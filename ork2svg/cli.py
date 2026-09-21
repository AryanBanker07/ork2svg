"""Command-line interface for ork2svg."""

import argparse
from pathlib import Path
import sys
from typing import Optional

from .exporter import save_png, save_svg
from .models import BLUEPRINT_THEME, DARK_THEME, LIGHT_THEME
from .parser import parse_ork_file
from .renderer import SVGRenderer


def get_theme(name: str):
    name = name.lower()
    if name == "light":
        return LIGHT_THEME
    elif name == "blueprint":
        return BLUEPRINT_THEME
    return DARK_THEME


def main(args: Optional[list] = None):
    parser = argparse.ArgumentParser(
        prog="ork2svg",
        description="Convert OpenRocket (.ork) files into dimensioned CAD SVG drawings and high-resolution PNG images.",
    )
    parser.add_argument("input", help="Path to input OpenRocket (.ork) file (XML, ZIP, or GZIP).")
    parser.add_argument("-o", "--output", help="Path to output SVG file. Defaults to <stem>_dimensioned.svg.")
    parser.add_argument(
        "--png",
        action="store_true",
        help="Also export a high-resolution PNG file.",
    )
    parser.add_argument(
        "--png-output",
        help="Explicit path for PNG output (if different from default <stem>_dimensioned.png).",
    )
    parser.add_argument(
        "--theme",
        choices=["dark", "light", "blueprint"],
        default="dark",
        help="Visual drawing theme (default: dark).",
    )
    parser.add_argument(
        "--units",
        choices=["mm", "m", "in"],
        default="mm",
        help="Drawing measurement units (default: mm).",
    )
    parser.add_argument(
        "--png-width",
        type=int,
        default=None,
        help="Target PNG width in pixels (e.g. 3840 for 4K).",
    )
    parser.add_argument(
        "--png-dpi",
        type=float,
        default=300.0,
        help="Target DPI for PNG rasterization (default: 300.0).",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        default=1.0,
        help="Zoom multiplier for PNG export (default: 1.0).",
    )
    parser.add_argument(
        "--no-dimensions",
        action="store_true",
        help="Hide dimension lines and text.",
    )
    parser.add_argument(
        "--no-stations",
        action="store_true",
        help="Hide station marker lines.",
    )
    parser.add_argument(
        "--no-title-block",
        action="store_true",
        help="Hide engineering title block.",
    )
    parser.add_argument(
        "--no-fins",
        action="store_true",
        help="Hide fin geometries.",
    )

    parsed_args = parser.parse_args(args)

    input_path = Path(parsed_args.input)
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Resolve output paths
    svg_output = Path(parsed_args.output) if parsed_args.output else input_path.parent / f"{input_path.stem}_dimensioned.svg"
    png_output = (
        Path(parsed_args.png_output)
        if parsed_args.png_output
        else (svg_output.parent / f"{svg_output.stem}.png")
    )

    print(f"Parsing OpenRocket file: {input_path}")
    try:
        rocket = parse_ork_file(input_path)
    except Exception as e:
        print(f"Error parsing {input_path}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded rocket: '{rocket.name}'")
    print(f"  Stages: {len(rocket.stages)}")
    print(f"  Total Length: {rocket.total_length * 1000.0:.1f} mm ({rocket.total_length:.3f} m)")
    print(f"  Max Diameter: {rocket.max_diameter * 1000.0:.1f} mm")
    print(f"  Max Fin Span: {rocket.max_fin_span_diameter * 1000.0:.1f} mm")

    theme = get_theme(parsed_args.theme)
    renderer = SVGRenderer(
        rocket=rocket,
        theme=theme,
        unit=parsed_args.units,
        show_dimensions=not parsed_args.no_dimensions,
        show_stations=not parsed_args.no_stations,
        show_title_block=not parsed_args.no_title_block,
        show_fins=not parsed_args.no_fins,
    )

    svg_content = renderer.render()
    saved_svg = save_svg(svg_content, svg_output)
    print(f"[OK] Generated SVG drawing: {saved_svg}")

    if parsed_args.png:
        print(f"Rasterizing high-resolution PNG ({parsed_args.png_dpi} DPI)...")
        saved_png = save_png(
            svg_content=svg_content,
            output_path=png_output,
            width=parsed_args.png_width,
            zoom=parsed_args.zoom,
            dpi=parsed_args.png_dpi,
        )
        print(f"[OK] Generated PNG image: {saved_png}")


if __name__ == "__main__":
    main()
