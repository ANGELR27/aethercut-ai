"""Módulo de generación de gráficos infográficos y estadísticos de alta fidelidad para video broadcast.

Utiliza Matplotlib (backend Agg) y PIL para renderizar gráficos profesionales:
- Gráficos de barras comparativas (ej. A vs B, '300M vs 6M', 'Perro vs Humano')
- Medidores radiales / Gauges de porcentaje (ej. '2.4% PIB', '99.8%')
- Gráficos de tendencia y aceleración (ej. '+450%', '3.5x crecimiento')
- Estética Obsidian Glass / Neon Accent compatible con el sistema UI/UX ProMax.
"""

from __future__ import annotations

import io
import re
from typing import Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


class BroadcastChartGenerator:
    """Generador de gráficos e infografías para tarjetas Bento HUD de video."""

    @staticmethod
    def _parse_comparison(stat_text: str) -> Optional[Tuple[str, float, str, float]]:
        """Intenta extraer valores para una comparativa (ej: '300M vs 6M', '2.4% vs 0.8%')."""
        pattern = r"([\d\.,]+)\s*([a-zA-Z%]*)\s*(?:vs\.?|contra|\/)\s*([\d\.,]+)\s*([a-zA-Z%]*)"
        m = re.search(pattern, stat_text, re.IGNORECASE)
        if m:
            v1_str, u1, v2_str, u2 = m.groups()
            try:
                v1 = float(v1_str.replace(",", "."))
                v2 = float(v2_str.replace(",", "."))
                unit1 = u1 or u2 or ""
                unit2 = u2 or u1 or ""
                return (f"{v1_str}{unit1}", v1, f"{v2_str}{unit2}", v2)
            except Exception:
                pass
        return None

    @staticmethod
    def _parse_percentage(stat_text: str) -> Optional[float]:
        """Extrae porcentaje flotante si existe (ej. '2.4% PIB' -> 2.4)."""
        m = re.search(r"([\d\.,]+)\s*%", stat_text)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except Exception:
                pass
        return None

    @staticmethod
    def _parse_growth(stat_text: str) -> Optional[float]:
        """Extrae multiplicador o crecimiento (ej. '+450%', '3.5x')."""
        m = re.search(r"([+-]?[\d\.,]+)\s*(?:%|x)", stat_text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", ".").replace("+", ""))
            except Exception:
                pass
        return None

    # Coordenadas geográficas clave de países y regiones para mapas geopolíticos
    GEO_COORDINATES: dict[str, tuple[float, float, str]] = {
        "argentina": (-64.0, -34.0, "ARG"),
        "estados unidos": (-98.0, 38.0, "EE.UU."),
        "eeuu": (-98.0, 38.0, "EE.UU."),
        "usa": (-98.0, 38.0, "EE.UU."),
        "china": (105.0, 35.0, "CHN"),
        "brasil": (-51.0, -14.0, "BRA"),
        "brazil": (-51.0, -14.0, "BRA"),
        "israel": (34.8, 31.5, "ISR"),
        "espana": (-3.7, 40.4, "ESP"),
        "españa": (-3.7, 40.4, "ESP"),
        "mexico": (-102.5, 23.6, "MEX"),
        "méxico": (-102.5, 23.6, "MEX"),
        "colombia": (-74.2, 4.5, "COL"),
        "chile": (-71.5, -35.6, "CHL"),
        "peru": (-75.0, -9.1, "PER"),
        "perú": (-75.0, -9.1, "PER"),
        "rusia": (60.0, 55.0, "RUS"),
        "ucrania": (31.1, 48.3, "UKR"),
        "alemania": (10.4, 51.1, "DEU"),
        "francia": (2.2, 46.2, "FRA"),
        "reino unido": (-3.4, 55.3, "GBR"),
        "italia": (12.5, 41.8, "ITA"),
        "japon": (138.2, 36.2, "JPN"),
        "japón": (138.2, 36.2, "JPN"),
        "india": (78.9, 20.5, "IND"),
        "canada": (-106.3, 56.1, "CAN"),
        "canadá": (-106.3, 56.1, "CAN"),
    }

    @classmethod
    def _detect_geo_locations(cls, text: str) -> list[tuple[float, float, str]]:
        """Detecta menciones de países o regiones clave en el texto para proyectar mapa."""
        low = text.lower()
        found: list[tuple[float, float, str]] = []
        seen = set()
        for name, (lon, lat, code) in cls.GEO_COORDINATES.items():
            if re.search(r"\b" + re.escape(name) + r"\b", low):
                if code not in seen:
                    found.append((lon, lat, code))
                    seen.add(code)
        return found

    @classmethod
    def render_chart_image(
        cls,
        stat_value: str,
        headline: str = "",
        width_px: int = 360,
        height_px: int = 240,
        dpi: int = 150,
    ) -> Optional[Image.Image]:
        """
        Analiza el dato estadístico, titular o contexto y renderiza el gráfico infográfico más apropiado:
        1. Mapa geopolítico si se detectan países o alianzas internacionales.
        2. Barras comparativas si hay 'A vs B' o comparativas de magnitudes.
        3. Medidor radial / Gauge si es un porcentaje o proporción.
        4. Curva de tendencia / Sparkline si hay aceleración o multiplicador.
        5. Mini ecualizador HUD de datos de alto impacto.
        """
        stat_clean = (stat_value or "").strip()
        combined_text = f"{stat_clean} {headline}".strip()
        if not combined_text:
            return None

        # 1. Mapa geopolítico interactivo si se mencionan países o relaciones internacionales
        geo_nodes = cls._detect_geo_locations(combined_text)
        if len(geo_nodes) >= 1:
            return cls._render_geointel_map(geo_nodes, width_px, height_px, dpi)

        # 2. Comparativa A vs B
        comp = cls._parse_comparison(stat_clean) or cls._parse_comparison(headline)
        if comp:
            return cls._render_comparison_bars(comp, width_px, height_px, dpi)

        # 3. Porcentaje o ratio
        pct = cls._parse_percentage(stat_clean) or cls._parse_percentage(headline)
        if pct is not None:
            return cls._render_radial_gauge(pct, stat_clean or headline, width_px, height_px, dpi)

        # 4. Crecimiento o aceleración
        growth = cls._parse_growth(stat_clean) or cls._parse_growth(headline)
        if growth is not None and abs(growth) > 0:
            return cls._render_trend_sparkline(growth, stat_clean or headline, width_px, height_px, dpi)

        # 5. Fallback a gráfico de métrica visual (Mini Bar HUD)
        return cls._render_metric_hud(stat_clean, width_px, height_px, dpi)

    @staticmethod
    def _render_comparison_bars(
        comp: Tuple[str, float, str, float],
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> Optional[Image.Image]:
        """Renderiza barras comparativas horizontales elegantes con acento neón."""
        label1, val1, label2, val2 = comp
        fig_w = width_px / dpi
        fig_h = height_px / dpi

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi, facecolor="none")
        ax.set_facecolor("none")

        y_pos = [1.2, 0.4]
        vals = [val1, val2]
        labels = [label1, label2]
        colors = ["#10b981", "#38bdf8"]  # Esmeralda vs Cyan

        max_v = max(vals) if max(vals) > 0 else 1.0
        norm_vals = [v / max_v for v in vals]

        # Barras de fondo (pistas oscuras)
        ax.barh(y_pos, [1.0, 1.0], height=0.36, color="#222222", alpha=0.6, edgecolor="#333333", linewidth=1)
        # Barras de valor real
        bars = ax.barh(y_pos, norm_vals, height=0.36, color=colors, edgecolor="none")

        # Texto sobre las barras
        for y, orig_val, col in zip(y_pos, labels, colors):
            ax.text(
                0.04, y, f" {orig_val}",
                va="center", ha="left",
                color="#ffffff", fontsize=11, fontweight="bold",
                fontfamily="sans-serif"
            )

        ax.set_xlim(0, 1.05)
        ax.set_ylim(-0.1, 1.7)
        ax.axis("off")

        buf = io.BytesIO()
        plt.tight_layout(pad=0.2)
        fig.savefig(buf, format="png", transparent=True, dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf).convert("RGBA")

    @staticmethod
    def _render_radial_gauge(
        pct: float,
        stat_label: str,
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> Optional[Image.Image]:
        """Renderiza un anillo / gauge radial futurista para porcentajes."""
        fig_w = width_px / dpi
        fig_h = height_px / dpi

        fig, ax = plt.subplots(
            figsize=(fig_w, fig_h),
            subplot_kw=dict(aspect="equal"),
            dpi=dpi,
            facecolor="none"
        )
        ax.set_facecolor("none")

        # Rango de porcentaje normalizado (0 a 100)
        clamped_pct = min(100.0, max(0.0, pct if pct <= 100 else 100.0))
        fraction = clamped_pct / 100.0

        # Fondo del anillo completo
        theta_full = np.linspace(0, 2 * np.pi, 120)
        ax.plot(np.cos(theta_full), np.sin(theta_full), color="#242426", lw=11, solid_capstyle="round")

        # Arco de progreso activo (desde arriba en sentido horario)
        start_angle = np.pi / 2
        end_angle = start_angle - (2 * np.pi * max(0.03, fraction))
        theta_prog = np.linspace(start_angle, end_angle, max(10, int(80 * fraction)))

        # Color: Ámbar si es moderado, verde esmeralda si es alto, cian si es neutro
        prog_color = "#f59e0b" if pct < 50 else "#10b981"
        ax.plot(np.cos(theta_prog), np.sin(theta_prog), color=prog_color, lw=11, solid_capstyle="round")

        # Cifra central destacada
        display_text = f"{pct:g}%" if len(f"{pct:g}%") <= 6 else f"{pct:.1f}%"
        ax.text(
            0, 0.08, display_text,
            va="center", ha="center",
            color="#ffffff", fontsize=17, fontweight="bold",
            fontfamily="sans-serif"
        )
        ax.text(
            0, -0.32, "MÉTRICA",
            va="center", ha="center",
            color="#94a3b8", fontsize=8, fontweight="bold",
            fontfamily="sans-serif"
        )

        ax.set_xlim(-1.20, 1.20)
        ax.set_ylim(-1.20, 1.20)
        ax.axis("off")

        buf = io.BytesIO()
        plt.tight_layout(pad=0.1)
        fig.savefig(buf, format="png", transparent=True, dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf).convert("RGBA")

    @staticmethod
    def _render_trend_sparkline(
        growth: float,
        stat_label: str,
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> Optional[Image.Image]:
        """Renderiza una curva de tendencia luminosa con gradiente/área sombreada."""
        fig_w = width_px / dpi
        fig_h = height_px / dpi

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi, facecolor="none")
        ax.set_facecolor("none")

        # Generar curva exponencial suave
        x = np.linspace(0, 10, 50)
        curve = 1.0 + (x / 10.0) ** 1.8 * (growth if growth > 0 else 1.0)
        
        line_color = "#38bdf8" if growth > 0 else "#f87171"
        ax.fill_between(x, curve, color=line_color, alpha=0.15)
        ax.plot(x, curve, color=line_color, lw=2.5, solid_capstyle="round")

        # Punto culminante final
        ax.scatter([x[-1]], [curve[-1]], color="#ffffff", s=40, zorder=5, edgecolors=line_color, linewidth=2)

        ax.axis("off")

        buf = io.BytesIO()
        plt.tight_layout(pad=0.2)
        fig.savefig(buf, format="png", transparent=True, dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf).convert("RGBA")

    @staticmethod
    def _render_metric_hud(
        stat_label: str,
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> Optional[Image.Image]:
        """Renderiza un indicador de datos visual futurista con anillo de cristal neón y métricas dinámicas."""
        fig_w = width_px / dpi
        fig_h = height_px / dpi

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi, facecolor="none")
        ax.set_facecolor("none")

        # 1. Indicador de 5 segmentos con gradiente luminoso y pistas de cristal
        segments = 5
        angles = np.linspace(0.85 * np.pi, 0.15 * np.pi, segments)
        radii = np.linspace(0.65, 0.95, segments)

        # Barra de progreso estilizada en arco
        t = np.linspace(np.pi, 0, 100)
        # Pista oscura de fondo
        ax.plot(np.cos(t), np.sin(t), color="#1e293b", lw=8, alpha=0.7, solid_capstyle="round")
        
        # Pista activa en gradiente neón
        t_active = np.linspace(np.pi, 0.25 * np.pi, 75)
        ax.plot(np.cos(t_active), np.sin(t_active), color="#38bdf8", lw=8, solid_capstyle="round")
        
        # Segmento culmen en esmeralda
        t_peak = np.linspace(0.40 * np.pi, 0.25 * np.pi, 20)
        ax.plot(np.cos(t_peak), np.sin(t_peak), color="#10b981", lw=8, solid_capstyle="round")

        # Icono / Tag numérico en el centro
        ax.text(
            0, 0.18, "HUD METRIC",
            va="center", ha="center",
            color="#38bdf8", fontsize=7.5, fontweight="bold",
            fontfamily="sans-serif"
        )
        ax.text(
            0, -0.05, "VERIFICADO",
            va="center", ha="center",
            color="#94a3b8", fontsize=6, fontweight="bold",
            fontfamily="sans-serif"
        )

        ax.set_xlim(-1.15, 1.15)
        ax.set_ylim(-0.25, 1.15)
        ax.axis("off")

        buf = io.BytesIO()
        plt.tight_layout(pad=0.1)
        fig.savefig(buf, format="png", transparent=True, dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf).convert("RGBA")

    @staticmethod
    def _render_geointel_map(
        geo_nodes: list[tuple[float, float, str]],
        width_px: int,
        height_px: int,
        dpi: int,
    ) -> Optional[Image.Image]:
        """
        Renderiza un mapa geopolítico vectorial de alta definición estilo HUD / Geospatial Intelligence:
        - Malla global de puntos sutiles
        - Contornos y polígonos estilizados de las masas continentales
        - Marcadores luminosos (pines) en los países involucrados
        - Arcos o líneas de enlace entre nodos si hay múltiples países
        """
        fig_w = width_px / dpi
        fig_h = height_px / dpi

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi, facecolor="none")
        ax.set_facecolor("none")

        # 1. Matriz de cuadrícula sutil (HUD grid)
        lons = np.linspace(-150, 150, 16)
        lats = np.linspace(-50, 70, 8)
        gx, gy = np.meshgrid(lons, lats)
        ax.scatter(gx, gy, s=1.2, color="#334155", alpha=0.35, zorder=1)

        # 2. Polígonos simplificados de continentes terrestres
        continents = [
            # América del Norte
            [(-130, 55), (-120, 65), (-80, 65), (-60, 45), (-80, 25), (-100, 20), (-120, 35)],
            # América del Sur
            [(-75, 10), (-40, -5), (-35, -20), (-60, -50), (-75, -40), (-80, -10)],
            # Europa
            [(-10, 40), (0, 60), (30, 65), (40, 45), (10, 38)],
            # África
            [(-15, 30), (35, 30), (45, 10), (30, -30), (15, -34), (0, 5)],
            # Asia
            [(40, 45), (70, 70), (140, 60), (120, 25), (100, 10), (60, 25)],
            # Oceanía / Australia
            [(115, -20), (150, -20), (145, -38), (120, -35)],
        ]

        for poly in continents:
            xs = [p[0] for p in poly] + [poly[0][0]]
            ys = [p[1] for p in poly] + [poly[0][1]]
            ax.fill(xs, ys, color="#1e293b", alpha=0.6, zorder=2)
            ax.plot(xs, ys, color="#475569", lw=0.8, alpha=0.7, zorder=3)

        # 3. Líneas de conexión diplomática o comercial si hay 2 o más nodos
        if len(geo_nodes) >= 2:
            node_xs = [n[0] for n in geo_nodes]
            node_ys = [n[1] for n in geo_nodes]
            for i in range(len(geo_nodes) - 1):
                x1, y1 = node_xs[i], node_ys[i]
                x2, y2 = node_xs[i + 1], node_ys[i + 1]
                ax.plot([x1, x2], [y1, y2], color="#38bdf8", lw=1.2, ls="--", alpha=0.85, zorder=4)

        # 4. Pines y etiquetas de los países localizados
        for lon, lat, code in geo_nodes:
            # Halo exterior difuso
            ax.scatter([lon], [lat], color="#38bdf8", s=65, alpha=0.35, zorder=5)
            # Centro blanco brillante
            ax.scatter([lon], [lat], color="#ffffff", edgecolors="#0284c7", lw=1.5, s=26, zorder=6)
            # Etiqueta con micro-caja
            y_offset = 6 if lat >= 0 else -10
            ax.text(
                lon, lat + y_offset, code,
                color="#ffffff", fontsize=7.5, fontweight="bold",
                ha="center", va="center",
                fontfamily="sans-serif",
                bbox=dict(boxstyle="round,pad=0.18", facecolor="#090d16", edgecolor="#38bdf8", alpha=0.85, lw=0.6),
                zorder=7,
            )

        ax.set_xlim(-170, 170)
        ax.set_ylim(-60, 80)
        ax.axis("off")

        buf = io.BytesIO()
        plt.tight_layout(pad=0.1)
        fig.savefig(buf, format="png", transparent=True, dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf).convert("RGBA")

    @classmethod
    def render_ai_custom_chart(
        cls,
        topic: str,
        stat_value: str,
        headline: str,
        width_px: int = 1280,
        height_px: int = 720,
    ) -> Optional[Image.Image]:
        """
        Utiliza NVIDIA (o LLM) para generar código de renderizado de infografía a medida
        estilo Studio Broadcast (Obsidian Glass, Dark Mode, acentos Neón) cuando se requiere
        un gráfico o diagrama cinemático avanzado que no encaja en las plantillas básicas.
        """
        from config.settings import settings
        if not getattr(settings, "NVIDIA_API_KEY", None):
            return None

        from openai import OpenAI
        prompt = (
            f"Escribe un script de Python usando matplotlib (backend Agg, plt.subplots, facecolor='#0b0f19') "
            f"para crear una infografía cinematográfica premium sobre:\n"
            f"Tema: {topic}\n"
            f"Dato clave: {stat_value}\n"
            f"Titular: {headline}\n\n"
            f"Requisitos estrictos:\n"
            f"- Dimensiones: {width_px}x{height_px} px (dpi=150, figsize=({width_px/150:.1f}, {height_px/150:.1f})).\n"
            f"- Fondo oscuro profesional '#0b0f19', texto blanco '#f8fafc', detalles en cian '#38bdf8' y esmeralda '#10b981'.\n"
            f"- Incluye barras, métricas o visualización de datos limpia y moderna.\n"
            f"- El script debe asignar la figura a la variable 'fig'.\n"
            f"- Responde ÚNICAMENTE con el código Python dentro de un bloque ```python ... ``` sin comentarios ni explicaciones adicionales."
        )

        try:
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=settings.NVIDIA_API_KEY,
                timeout=25.0,
            )
            resp = client.chat.completions.create(
                model=getattr(settings, "NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct"),
                messages=[
                    {"role": "system", "content": "Eres un programador experto en visualización de datos con Matplotlib."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500,
            )
            raw_code = resp.choices[0].message.content or ""
            # Extraer bloque de código
            m = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", raw_code)
            code = m.group(1) if m else raw_code

            # Ejecutar de forma segura para obtener 'fig'
            local_vars: dict = {"matplotlib": matplotlib, "plt": plt, "np": np}
            exec(code, local_vars, local_vars)

            fig = local_vars.get("fig")
            if fig is not None:
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
                plt.close(fig)
                buf.seek(0)
                img = Image.open(buf).convert("RGBA")
                return img
        except Exception as exc:
            from core.llm import safe_log
            safe_log(f"[ChartGenerator] Error generando gráfico con NVIDIA: {exc}")
        return None

