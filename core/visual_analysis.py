"""Análisis visual local para que los overlays respeten el encuadre.

No envía fotogramas a servicios externos: detecta cortes de plano con
PySceneDetect y usa el clasificador facial incluido en OpenCV para ubicar al
hablante. Ambos resultados son sugerencias; cuando no hay detección válida se
mantiene el comportamiento editorial existente (``auto``).
"""

from __future__ import annotations

from pathlib import Path
from statistics import median
from threading import Event
from typing import Iterable, List, Optional

from cancellation import CancellationRequested
from core.models import InfoCard


class VisualAnalyzer:
    def __init__(self, cancel_event: Optional[Event] = None):
        self.cancel_event = cancel_event

    def detect_scene_cuts(self, video_path: Path, min_scene_len_sec: float = 1.2) -> List[float]:
        """Devuelve cambios de plano para diagnóstico y decisiones editoriales.

        AdaptiveDetector usa un promedio móvil, por lo que evita confundir
        movimiento rápido de cámara con un corte. Una ausencia de PySceneDetect
        o un archivo peculiar nunca detiene el render.
        """
        if self.cancel_event and self.cancel_event.is_set():
            raise CancellationRequested()
        try:
            from scenedetect import AdaptiveDetector, detect
            scenes = detect(str(video_path), AdaptiveDetector(min_scene_len=min_scene_len_sec))
            if self.cancel_event and self.cancel_event.is_set():
                raise CancellationRequested()
            return [round(end.get_seconds(), 3) for _start, end in scenes[:-1]]
        except CancellationRequested:
            raise
        except Exception as exc:
            print(f"[VisualAnalyzer] No se detectaron cambios de plano: {exc}")
            return []

    def place_cards_away_from_speaker(self, video_path: Path, cards: Iterable[InfoCard]) -> int:
        """Sugiere un lado para cada tarjeta automática según la cara dominante.

        Se inspecciona un solo cuadro por tarjeta, cerca de la frase detectada,
        para no transformar este paso en un segundo render. Solo se modifican
        tarjetas con posición ``auto`` para respetar ajustes manuales o del LLM.
        """
        try:
            import cv2
        except Exception as exc:
            print(f"[VisualAnalyzer] OpenCV no está disponible: {exc}")
            return 0

        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(str(cascade_path))
        if face_cascade.empty():
            return 0
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return 0

        placed = 0
        try:
            for card in cards:
                if self.cancel_event and self.cancel_event.is_set():
                    raise CancellationRequested()
                if not card.enabled or card.screen_position != "auto":
                    continue
                # Un instante posterior evita elegir un fotograma de transición.
                capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, card.start_sec + 0.25) * 1000)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.12, minNeighbors=5, minSize=(36, 36))
                if len(faces) == 0:
                    continue
                x, _y, w, h = max(faces, key=lambda face: int(face[2]) * int(face[3]))
                center = (float(x) + float(w) / 2) / max(1, frame.shape[1])
                if center < 0.44:
                    card.screen_position = "lower_right"
                elif center > 0.56:
                    card.screen_position = "lower_left"
                else:
                    # Con el hablante centrado, se conserva una esquina inferior
                    # consistente, lejos de subtítulos situados en el centro.
                    card.screen_position = "upper_right"
                placed += 1
        finally:
            capture.release()
        return placed

    def dominant_face_focus(self, video_path: Path, start_sec: float, end_sec: float,
                            samples: int = 5) -> float:
        """Devuelve el centro horizontal del rostro dominante de un clip.

        Muestrea varios puntos y usa la mediana para ignorar transiciones o
        detecciones puntuales equivocadas. El valor 0.5 conserva el encuadre
        centrado cuando el video no contiene una cara reconocible.
        """
        try:
            import cv2
        except Exception:
            return 0.5
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        detector = cv2.CascadeClassifier(str(cascade_path))
        if detector.empty():
            return 0.5
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return 0.5
        centers: List[float] = []
        try:
            span = max(0.15, float(end_sec) - float(start_sec))
            for index in range(max(1, samples)):
                if self.cancel_event and self.cancel_event.is_set():
                    raise CancellationRequested()
                at = float(start_sec) + span * (index + 0.5) / max(1, samples)
                capture.set(cv2.CAP_PROP_POS_MSEC, at * 1000)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = detector.detectMultiScale(gray, scaleFactor=1.12, minNeighbors=5, minSize=(36, 36))
                if len(faces):
                    x, _y, w, h = max(faces, key=lambda face: int(face[2]) * int(face[3]))
                    centers.append((float(x) + float(w) / 2) / max(1, frame.shape[1]))
        finally:
            capture.release()
        return max(0.0, min(1.0, float(median(centers)))) if centers else 0.5
