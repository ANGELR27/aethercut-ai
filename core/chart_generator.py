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
        Analiza el dato estadístico y renderiza el gráfico infográfico más apropiado.
        Devuelve una imagen PIL RGBA con fondo transparente.
        """
        stat_clean = (stat_value or "").strip()
        if not stat_clean:
            return None

        # 1. Comparativa A vs B
        comp = cls._parse_comparison(stat_clean) or cls._parse_comparison(headline)
        if comp:
            return cls._render_comparison_bars(comp, width_px, height_px, dpi)

        # 2. Porcentaje o ratio
        pct = cls._parse_percentage(stat_clean)
        if pct is not None:
            return cls._render_radial_gauge(pct, stat_clean, width_px, height_px, dpi)

        # 3. Crecimiento o aceleración
        growth = cls._parse_growth(stat_clean)
        if growth is not None and abs(growth) > 0:
            return cls._render_trend_sparkline(growth, stat_clean, width_px, height_px, dpi)

        # 4. Fallback a gráfico de métrica visual (Mini Bar HUD)
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
        """Renderiza un micro-indicador de 3 barras de ecualizador de datos para cifras generales."""
        fig_w = width_px / dpi
        fig_h = height_px / dpi

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi, facecolor="none")
        ax.set_facecolor("none")

        x_indices = [0.8, 1.8, 2.8]
        heights = [0.45, 0.90, 0.65]
        colors = ["#38bdf8", "#10b981", "#f59e0b"]

        # Barras de fondo
        ax.bar(x_indices, [1.0, 1.0, 1.0], width=0.45, color="#222224", alpha=0.6)
        # Barras de datos
        ax.bar(x_indices, heights, width=0.45, color=colors)

        ax.set_xlim(0.2, 3.4)
        ax.set_ylim(0, 1.1)
        ax.axis("off")

        buf = io.BytesIO()
        plt.tight_layout(pad=0.1)
        fig.savefig(buf, format="png", transparent=True, dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf).convert("RGBA")
