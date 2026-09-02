"""Dependency-free SVG rendering for extracted page-space strokes."""
from __future__ import annotations
from pathlib import Path
from handwriting.goodnotes.extraction import Page


def render_page_svg(page: Page, destination: str | Path) -> Path:
    """Render a page to SVG while preserving native coordinates and widths."""
    output = Path(destination)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{page.width}" height="{page.height}" viewBox="0 0 {page.width} {page.height}">', '<rect width="100%" height="100%" fill="white"/>']
    for stroke in page.strokes:
        r, g, b, alpha = stroke.color_rgba; color = f"rgb({round(r * 255)},{round(g * 255)},{round(b * 255)})"
        for start, end in zip(stroke.points, stroke.points[1:]):
            parts.append(f'<path d="M {start.x:.3f} {start.y:.3f} L {end.x:.3f} {end.y:.3f}" stroke="{color}" stroke-opacity="{alpha:.3f}" stroke-width="{max(.1, (start.width + end.width) / 2):.3f}" stroke-linecap="round" fill="none"/>')
    parts.append("</svg>"); output.write_text("\n".join(parts), encoding="utf-8")
    return output
