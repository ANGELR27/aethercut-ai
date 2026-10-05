import asyncio
import sys
from pathlib import Path

from config.settings import settings
from core.card_renderer import InfoCardRenderer
from core.fact_checker import FactChecker
from core.llm import LLMClient, safe_log
from core.models import InfoCard, VideoEditingPlan, TimelineSegment, ActionType

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


async def main():
    workdir = settings.TEMP_DIR / "cards_test"
    workdir.mkdir(parents=True, exist_ok=True)

    cards = [
        InfoCard(card_id="t_ok", start_sec=5, end_sec=10, kind="ley",
                 headline="Ley Bases y el RIGI",
                 claim="La Ley Bases de Argentina creó el RIGI, un régimen de incentivo para grandes inversiones",
                 search_query="Ley 27742 Ley Bases RIGI régimen de incentivo para grandes inversiones",
                 image_query="Ley de Bases y Puntos de Partida para la Libertad de los Argentinos"),
        InfoCard(card_id="t_false", start_sec=20, end_sec=25, kind="fecha",
                 headline="Capital de Argentina",
                 claim="La capital de Argentina es Montevideo",
                 search_query="capital de Argentina",
                 image_query="Buenos Aires"),
        InfoCard(card_id="t_person", start_sec=40, end_sec=45, kind="organizacion",
                 headline="Banco Central",
                 claim="El Banco Central de la República Argentina fue fundado en 1935",
                 search_query="Banco Central de la República Argentina año de fundación",
                 image_query="Banco Central de la República Argentina"),
    ]
    plan = VideoEditingPlan(video_summary="t", total_original_duration_sec=60,
                            timeline=[TimelineSegment(start_sec=0, end_sec=60, action=ActionType.KEEP)],
                            info_cards=cards)

    llm = LLMClient()
    checker = FactChecker(llm, workdir)
    await checker.verify_plan(plan, progress=lambda m: safe_log("  >> " + m))

    renderer = InfoCardRenderer(1920, 1080)
    renderer.render_all(plan.info_cards, workdir)

    print("\n=== RESULTADOS ===")
    for c in plan.info_cards:
        print(f"[{c.card_id}] veredicto={c.verdict} | nota={c.note}")
        if c.body:
            print(f"    texto: {c.body}")
        for s in c.sources:
            print(f"    fuente: {s.domain} -> {s.url[:80]}")
        print(f"    foto: {bool(c.image_path)} | tarjeta: {c.card_path}")
    print("Modelo usado:", llm.last_model_used)


asyncio.run(main())
