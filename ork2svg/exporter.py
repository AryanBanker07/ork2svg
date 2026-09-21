"""Export utilities for saving SVG files and rasterizing to high-resolution PNG."""

from pathlib import Path
from typing import Optional, Union
import resvg_py


def save_svg(svg_content: str, output_path: Union[str, Path]) -> Path:
    """Save SVG string to an output file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    return path


def save_png(
    svg_content: str,
    output_path: Union[str, Path],
    width: Optional[int] = None,
    height: Optional[int] = None,
    zoom: Optional[float] = None,
    dpi: float = 300.0,
) -> Path:
    """
    Rasterize SVG string to high-resolution PNG using resvg-py.
    
    :param svg_content: Raw SVG markup string.
    :param output_path: Path to save the PNG file.
    :param width: Target width in pixels (optional).
    :param height: Target height in pixels (optional).
    :param zoom: Zoom multiplier (e.g. 1.0, 2.0).
    :param dpi: Target DPI (default 300.0).
    :return: Resolved Path of the created PNG file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    png_bytes = resvg_py.svg_to_bytes(
        svg_string=svg_content,
        width=width,
        height=height,
        zoom=zoom,
        dpi=dpi,
        shape_rendering="geometric_precision",
        text_rendering="optimize_legibility",
    )

    with open(path, "wb") as f:
        f.write(png_bytes)
    return path
