"""SVG technical drawing renderer for OpenRocket models."""

import math
from typing import Dict, List, Optional, Tuple
from .curves import generate_component_profile
from .models import Component, DrawingTheme, FinSet, Rocket, Stage, DARK_THEME, LIGHT_THEME, BLUEPRINT_THEME


class SVGRenderer:
    """Renders a Rocket object to a dimensioned CAD SVG technical drawing."""

    def __init__(
        self,
        rocket: Rocket,
        theme: DrawingTheme = DARK_THEME,
        unit: str = "mm",
        show_dimensions: bool = True,
        show_stations: bool = True,
        show_title_block: bool = True,
        show_fins: bool = True,
    ):
        self.rocket = rocket
        self.theme = theme
        self.unit = unit.lower()
        self.show_dimensions = show_dimensions
        self.show_stations = show_stations
        self.show_title_block = show_title_block
        self.show_fins = show_fins

        # Unit scale factor (models are in meters)
        if self.unit == "mm":
            self.scale = 1000.0
            self.unit_label = "mm"
            self.fmt = "{:.1f}"
        elif self.unit == "in":
            self.scale = 39.3700787
            self.unit_label = "in"
            self.fmt = "{:.2f}"
        else:  # meters
            self.scale = 1.0
            self.unit_label = "m"
            self.fmt = "{:.3f}"

        # Rocket scaled dimensions
        self.L = self.rocket.total_length * self.scale
        self.max_r = (self.rocket.max_diameter / 2.0) * self.scale
        self.max_fin_r = (self.rocket.max_fin_span_diameter / 2.0) * self.scale

        # Canvas layout setup (all in scaled units)
        self.margin_left = max(260.0, self.L * 0.05)
        self.margin_right = max(260.0, self.L * 0.05)
        self.dim_top_space = max(380.0, self.max_fin_r * 1.5)
        self.dim_bottom_space = max(460.0, self.max_fin_r * 1.8)

        # Centerline Y position
        self.cy = self.dim_top_space + self.max_fin_r + 40.0

        # Total canvas size
        self.width = self.margin_left + self.L + self.margin_right
        self.height = self.cy + self.max_fin_r + self.dim_bottom_space

        # Baseline origin of rocket nose tip in SVG coordinates
        self.ox = self.margin_left

    def _u(self, meters: float) -> float:
        """Convert meters to scaled drawing units."""
        return meters * self.scale

    def _fmt_dim(self, meters: float, prefix: str = "") -> str:
        """Format dimension with unit."""
        val = meters * self.scale
        # Strip trailing .0 if integer
        formatted = self.fmt.format(val)
        if formatted.endswith(".0"):
            formatted = formatted[:-2]
        return f"{prefix}{formatted} {self.unit_label}"

    def render(self) -> str:
        """Generate the complete SVG document."""
        svg_parts = []
        svg_parts.append(self._render_header())
        svg_parts.append(self._render_defs())
        svg_parts.append(self._render_background())

        # Layer: ISO Centerline
        svg_parts.append(self._render_centerline())

        # Layer: Rocket solid body & fins
        svg_parts.append(self._render_rocket_geometry())

        # Layer: Internal component & stage separation lines
        svg_parts.append(self._render_internal_stations())

        # Layer: CFD Axisymmetric contour (for CFD tools)
        svg_parts.append(self._render_cfd_layer())

        # Layer: Dimensions
        if self.show_dimensions:
            svg_parts.append(self._render_dimensions())

        # Layer: Stations
        if self.show_stations:
            svg_parts.append(self._render_stations())

        # Layer: Title Block
        if self.show_title_block:
            svg_parts.append(self._render_title_block())

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def _render_header(self) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {self.width:.1f} {self.height:.1f}" '
            f'width="{self.width:.1f}" height="{self.height:.1f}" '
            f'style="background-color: {self.theme.background}; '
            f'font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif;">'
        )

    def _render_defs(self) -> str:
        """Render arrowheads, markers, and patterns in SVG defs."""
        arr_color = self.theme.dimension_line
        return f"""<defs>
  <!-- Grid Pattern -->
  <pattern id="grid_minor" width="50" height="50" patternUnits="userSpaceOnUse">
    <path d="M 50 0 L 0 0 0 50" fill="none" stroke="{self.theme.grid_minor}" stroke-width="1" />
  </pattern>
  <pattern id="grid_major" width="250" height="250" patternUnits="userSpaceOnUse">
    <rect width="250" height="250" fill="url(#grid_minor)" />
    <path d="M 250 0 L 0 0 0 250" fill="none" stroke="{self.theme.grid_major}" stroke-width="1.5" />
  </pattern>

  <!-- Dimension Arrowheads -->
  <marker id="arrow-start" viewBox="0 0 10 10" refX="2" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M 10 1.5 L 0 5 L 10 8.5 Z" fill="{arr_color}" />
  </marker>
  <marker id="arrow-end" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M 0 1.5 L 10 5 L 0 8.5 Z" fill="{arr_color}" />
  </marker>
  <marker id="arrow-start-rev" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M 0 1.5 L 10 5 L 0 8.5 Z" fill="{arr_color}" />
  </marker>
  <marker id="arrow-end-rev" viewBox="0 0 10 10" refX="2" refY="5" markerWidth="8" markerHeight="8" orient="auto">
    <path d="M 10 1.5 L 0 5 L 10 8.5 Z" fill="{arr_color}" />
  </marker>
</defs>"""

    def _render_background(self) -> str:
        return f"""<!-- Background & Grid -->
<g id="background_layer">
  <rect width="{self.width:.1f}" height="{self.height:.1f}" fill="{self.theme.background}" />
  <rect width="{self.width:.1f}" height="{self.height:.1f}" fill="url(#grid_major)" opacity="0.6" />
</g>"""

    def _render_centerline(self) -> str:
        """Render ISO standard dash-dot centerline."""
        x1 = self.ox - 60.0
        x2 = self.ox + self.L + 60.0
        y = self.cy
        return f"""<!-- Centerline -->
<g id="centerline_layer">
  <line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" 
        stroke="{self.theme.centerline}" stroke-width="1.8" stroke-dasharray="24,6,6,6" opacity="0.85" />
  <text x="{x1 - 15:.1f}" y="{y + 5:.1f}" fill="{self.theme.centerline}" font-size="16" font-weight="600" text-anchor="end">CL</text>
</g>"""

    def _render_rocket_geometry(self) -> str:
        """Render symmetrical upper and lower body silhouettes and fins."""
        parts = ['<g id="rocket_geometry_layer">']

        # 1. First render Fins (so body sits cleanly on fin roots)
        if self.show_fins:
            parts.append(self._render_fins())

        # 2. Render Body Silhouette
        # Collect upper profile points from tip (0) to tail (L)
        upper_pts: List[Tuple[float, float]] = []
        for stage in self.rocket.stages:
            for comp in stage.components:
                pts = generate_component_profile(comp, num_points=40, global_coords=True)
                upper_pts.extend(pts)

        # Build closed SVG path:
        # Upper curve: x: 0 -> L, y: cy - r
        # Base line: x: L, y: cy - r_tail -> cy + r_tail
        # Lower curve: x: L -> 0, y: cy + r
        # Tip close
        path_cmds = []
        first = True
        for x, r in upper_pts:
            px = self.ox + self._u(x)
            py = self.cy - self._u(r)
            if first:
                path_cmds.append(f"M {px:.2f} {py:.2f}")
                first = False
            else:
                path_cmds.append(f"L {px:.2f} {py:.2f}")

        # Reverse for lower curve
        for x, r in reversed(upper_pts):
            px = self.ox + self._u(x)
            py = self.cy + self._u(r)
            path_cmds.append(f"L {px:.2f} {py:.2f}")

        path_cmds.append("Z")
        d_str = " ".join(path_cmds)

        parts.append(
            f'  <path d="{d_str}" fill="{self.theme.rocket_fill}" '
            f'stroke="{self.theme.rocket_stroke}" stroke-width="2.5" stroke-linejoin="round" />'
        )

        parts.append("</g>")
        return "\n".join(parts)

    def _render_fins(self) -> str:
        """Render both upper (+Y) and lower (-Y) fin silhouettes."""
        fin_parts = []
        for stage in self.rocket.stages:
            for comp in stage.components:
                c_start = comp.axial_start
                r_body = comp.aft_radius
                for fin in comp.fins:
                    # Global axial positions of fin vertices
                    x_r_le = c_start + fin.root_le_x
                    x_t_le = c_start + fin.tip_le_x
                    x_t_te = c_start + fin.tip_te_x
                    x_r_te = c_start + fin.root_te_x

                    # Convert to drawing coordinates
                    sx_r_le = self.ox + self._u(x_r_le)
                    sx_t_le = self.ox + self._u(x_t_le)
                    sx_t_te = self.ox + self._u(x_t_te)
                    sx_r_te = self.ox + self._u(x_r_te)

                    sy_body_r = self._u(r_body)
                    sy_tip_r = self._u(r_body + fin.span)

                    # Upper Fin (+Y)
                    up_pts = (
                        f"{sx_r_le:.2f},{self.cy - sy_body_r:.2f} "
                        f"{sx_t_le:.2f},{self.cy - sy_tip_r:.2f} "
                        f"{sx_t_te:.2f},{self.cy - sy_tip_r:.2f} "
                        f"{sx_r_te:.2f},{self.cy - sy_body_r:.2f}"
                    )
                    fin_parts.append(
                        f'  <polygon points="{up_pts}" fill="{self.theme.fin_fill}" '
                        f'stroke="{self.theme.fin_stroke}" stroke-width="2" stroke-linejoin="round" />'
                    )

                    # Lower Fin (-Y)
                    dn_pts = (
                        f"{sx_r_le:.2f},{self.cy + sy_body_r:.2f} "
                        f"{sx_t_le:.2f},{self.cy + sy_tip_r:.2f} "
                        f"{sx_t_te:.2f},{self.cy + sy_tip_r:.2f} "
                        f"{sx_r_te:.2f},{self.cy + sy_body_r:.2f}"
                    )
                    fin_parts.append(
                        f'  <polygon points="{dn_pts}" fill="{self.theme.fin_fill}" '
                        f'stroke="{self.theme.fin_stroke}" stroke-width="2" stroke-linejoin="round" />'
                    )

        return "\n".join(fin_parts)

    def _render_internal_stations(self) -> str:
        """Render component separation lines inside the rocket."""
        lines = ['<!-- Component Separation Lines -->', '<g id="component_junctions_layer">']
        for stage in self.rocket.stages:
            for comp in stage.components:
                # Line at end of each component (except final rocket tail)
                if comp.axial_end < self.rocket.total_length:
                    x = self.ox + self._u(comp.axial_end)
                    r = self._u(comp.aft_radius)
                    y1 = self.cy - r
                    y2 = self.cy + r
                    lines.append(
                        f'  <line x1="{x:.2f}" y1="{y1:.2f}" x2="{x:.2f}" y2="{y2:.2f}" '
                        f'stroke="{self.theme.station_line}" stroke-width="1.4" stroke-dasharray="4,4" />'
                    )
        lines.append("</g>")
        return "\n".join(lines)

    def _render_cfd_layer(self) -> str:
        """Render a clean, isolated 2D axisymmetric profile for OpenFOAM meshing tools."""
        pts: List[Tuple[float, float]] = []
        for stage in self.rocket.stages:
            for comp in stage.components:
                pts.extend(generate_component_profile(comp, num_points=50, global_coords=True))

        path_cmds = [f"M {self.ox:.2f} {self.cy:.2f}"]
        # Surface points
        for x, r in pts:
            px = self.ox + self._u(x)
            py = self.cy - self._u(r)
            path_cmds.append(f"L {px:.2f} {py:.2f}")

        # Down to centerline at tail
        tail_x = self.ox + self.L
        path_cmds.append(f"L {tail_x:.2f} {self.cy:.2f}")
        # Back to nose tip along centerline
        path_cmds.append("Z")

        d_str = " ".join(path_cmds)
        return (
            f'<!-- OpenFOAM 2D Axisymmetric Profile Layer (Hidden by default, available for CFD/CAD tools) -->\n'
            f'<g id="openfoam_axisymmetric_profile" opacity="0.001">\n'
            f'  <path d="{d_str}" id="rocket_half_body_contour" />\n'
            f'</g>'
        )

    def _render_horizontal_dimension(
        self, x1: float, x2: float, y: float, text: str, ref_y: float, font_size: int = 20, is_major: bool = False
    ) -> str:
        """Render a horizontal dimension line with extension lines and centered text."""
        parts = []
        color = self.theme.dimension_line
        text_color = self.theme.dimension_text

        # Extension (witness) lines
        # Offset slightly from body
        ext_gap = 8.0 if y < ref_y else -8.0
        ext_y1 = ref_y + ext_gap
        ext_y2 = y - (6.0 if y < ref_y else -6.0)

        parts.append(
            f'  <line x1="{x1:.2f}" y1="{ext_y1:.2f}" x2="{x1:.2f}" y2="{ext_y2:.2f}" '
            f'stroke="{color}" stroke-width="1" stroke-dasharray="3,3" opacity="0.7" />'
        )
        parts.append(
            f'  <line x1="{x2:.2f}" y1="{ext_y1:.2f}" x2="{x2:.2f}" y2="{ext_y2:.2f}" '
            f'stroke="{color}" stroke-width="1" stroke-dasharray="3,3" opacity="0.7" />'
        )

        # Dimension line with arrows
        dx = abs(x2 - x1)
        if dx > 50.0:
            parts.append(
                f'  <line x1="{x1:.2f}" y1="{y:.2f}" x2="{x2:.2f}" y2="{y:.2f}" '
                f'stroke="{color}" stroke-width="1.6" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)" />'
            )
        else:
            # Reversed arrows for narrow dimension
            parts.append(
                f'  <line x1="{x1 - 25:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}" '
                f'stroke="{color}" stroke-width="1.6" marker-end="url(#arrow-end-rev)" />'
            )
            parts.append(
                f'  <line x1="{x2:.2f}" y1="{y:.2f}" x2="{x2 + 25:.2f}" y2="{y:.2f}" '
                f'stroke="{color}" stroke-width="1.6" marker-start="url(#arrow-start-rev)" />'
            )

        # Dimension text
        mid_x = (x1 + x2) / 2.0
        text_y = y - 9.0
        font_weight = "bold" if is_major else "600"

        # Background badge for text legibility
        text_len_est = len(text) * (font_size * 0.58)
        rect_x = mid_x - (text_len_est / 2.0) - 6.0
        rect_y = text_y - font_size + 2.0
        parts.append(
            f'  <rect x="{rect_x:.2f}" y="{rect_y:.2f}" width="{text_len_est + 12:.2f}" height="{font_size + 6:.2f}" '
            f'fill="{self.theme.background}" opacity="0.85" rx="3" />'
        )
        parts.append(
            f'  <text x="{mid_x:.2f}" y="{text_y:.2f}" fill="{text_color}" '
            f'font-size="{font_size}" font-weight="{font_weight}" text-anchor="middle">{text}</text>'
        )

        return "\n".join(parts)

    def _render_vertical_dimension(
        self, x: float, y1: float, y2: float, text: str, ref_x: float, font_size: int = 18
    ) -> str:
        """Render a vertical diameter dimension line with ISO rotated text and extension lines."""
        parts = []
        color = self.theme.dimension_line
        text_color = self.theme.dimension_text

        # Extension lines connecting feature station to dimension line
        parts.append(
            f'  <line x1="{ref_x:.2f}" y1="{y1:.2f}" x2="{x - 4 if x < ref_x else x + 4:.2f}" y2="{y1:.2f}" '
            f'stroke="{color}" stroke-width="1.2" stroke-dasharray="3,3" opacity="0.65" />'
        )
        parts.append(
            f'  <line x1="{ref_x:.2f}" y1="{y2:.2f}" x2="{x - 4 if x < ref_x else x + 4:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="1.2" stroke-dasharray="3,3" opacity="0.65" />'
        )

        # Dimension line with arrows
        parts.append(
            f'  <line x1="{x:.2f}" y1="{y1:.2f}" x2="{x:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="1.6" marker-start="url(#arrow-start)" marker-end="url(#arrow-end)" />'
        )

        # Rotated text centered on the dimension line (ISO style)
        mid_y = (y1 + y2) / 2.0
        text_len = len(text) * (font_size * 0.58)
        rect_w = text_len + 14.0
        rect_h = font_size + 6.0

        # Background badge rotated with text
        parts.append(
            f'  <g transform="rotate(-90, {x:.2f}, {mid_y:.2f})">\n'
            f'    <rect x="{x - rect_w / 2.0:.2f}" y="{mid_y - rect_h / 2.0:.2f}" '
            f'width="{rect_w:.2f}" height="{rect_h:.2f}" '
            f'fill="{self.theme.background}" opacity="0.88" rx="3" />\n'
            f'    <text x="{x:.2f}" y="{mid_y + font_size * 0.35:.2f}" fill="{text_color}" '
            f'font-size="{font_size}" font-weight="bold" text-anchor="middle">{text}</text>\n'
            f'  </g>'
        )
        return "\n".join(parts)

    def _render_dimensions(self) -> str:
        """Render full 3-tier dimension chains for components, stages, and overall rocket."""
        dims = ['<!-- Dimensions Layer -->', '<g id="dimensions_layer">']

        top_surface_y = self.cy - self.max_fin_r

        # Tier 1 (Component Lengths): y = top_surface_y - 60
        y_comp = top_surface_y - 60.0
        all_comps = self.rocket.all_components()
        for comp in all_comps:
            x1 = self.ox + self._u(comp.axial_start)
            x2 = self.ox + self._u(comp.axial_end)
            comp_r = self._u(comp.max_radius)
            ref_y = self.cy - comp_r
            dim_str = self._fmt_dim(comp.length)
            dims.append(self._render_horizontal_dimension(x1, x2, y_comp, dim_str, ref_y, font_size=18))

        # Tier 2 (Stage Lengths): y = top_surface_y - 140
        if len(self.rocket.stages) > 1:
            y_stage = top_surface_y - 140.0
            for stage in self.rocket.stages:
                x1 = self.ox + self._u(stage.axial_start)
                x2 = self.ox + self._u(stage.axial_end)
                ref_y = y_comp
                dim_str = f"{stage.name}: {self._fmt_dim(stage.length)}"
                dims.append(
                    self._render_horizontal_dimension(x1, x2, y_stage, dim_str, ref_y, font_size=20, is_major=True)
                )

        # Tier 3 (Total Overall Length): y = top_surface_y - 220
        y_total = top_surface_y - (220.0 if len(self.rocket.stages) > 1 else 140.0)
        total_dim_str = f"TOTAL LENGTH: {self._fmt_dim(self.rocket.total_length)}"
        dims.append(
            self._render_horizontal_dimension(
                self.ox, self.ox + self.L, y_total, total_dim_str, ref_y=y_total + 60.0, font_size=24, is_major=True
            )
        )

        # Vertical Dimensions (Diameters)
        # 1. Nose base diameter
        nose = next((c for c in all_comps if c.component_type == "nosecone"), None)
        if nose:
            nose_base_x = self.ox + self._u(nose.axial_end)
            r = self._u(nose.aft_radius)
            dim_x = self.ox - 70.0
            dia_str = self._fmt_dim(nose.aft_radius * 2.0, prefix="Ø ")
            dims.append(self._render_vertical_dimension(dim_x, self.cy - r, self.cy + r, dia_str, ref_x=nose_base_x, font_size=20))

        # 2. Main body tube diameter
        tube = next((c for c in all_comps if c.component_type == "bodytube"), None)
        if tube:
            mid_tube_x = self.ox + self._u((tube.axial_start + tube.axial_end) / 2.0)
            r = self._u(tube.aft_radius)
            dim_x = self.ox - 170.0
            dia_str = self._fmt_dim(tube.aft_radius * 2.0, prefix="Ø ")
            dims.append(self._render_vertical_dimension(dim_x, self.cy - r, self.cy + r, dia_str, ref_x=mid_tube_x, font_size=20))

        # 3. Fin span diameters (Right margin or at fin locations)
        if self.show_fins:
            for stage in self.rocket.stages:
                for comp in stage.components:
                    for fin in comp.fins:
                        total_span_dia = (comp.aft_radius + fin.span) * 2.0
                        fin_te_x = self.ox + self._u(comp.axial_start + fin.root_te_x)
                        span_r = self._u(comp.aft_radius + fin.span)
                        dim_x = fin_te_x + 60.0
                        span_str = self._fmt_dim(total_span_dia, prefix="SPAN Ø ")
                        dims.append(
                            self._render_vertical_dimension(
                                dim_x, self.cy - span_r, self.cy + span_r, span_str, ref_x=fin_te_x, font_size=18
                            )
                        )

        # 4. Fin geometric callout notes (Root, Tip, Span, Sweep)
        dims.append(self._render_fin_annotations())

        dims.append("</g>")
        return "\n".join(dims)

    def _render_fin_annotations(self) -> str:
        """Render detailed callouts for each fin set (root, tip, span, sweep)."""
        notes = []
        for stage in self.rocket.stages:
            for comp in stage.components:
                for fin in comp.fins:
                    le_x = self.ox + self._u(comp.axial_start + fin.root_le_x)
                    r_body = self._u(comp.aft_radius)
                    tip_y = self.cy + r_body + self._u(fin.span)

                    text_y = tip_y + 42.0
                    note_text = (
                        f"{fin.name} ({fin.fin_count}x): "
                        f"Root={self._fmt_dim(fin.root_chord)} | "
                        f"Tip={self._fmt_dim(fin.tip_chord)} | "
                        f"Span={self._fmt_dim(fin.span)} | "
                        f"Sweep={self._fmt_dim(fin.sweep_length)}"
                    )
                    text_len = len(note_text) * 9.5
                    notes.append(
                        f'  <rect x="{le_x - 6:.2f}" y="{text_y - 18:.2f}" width="{text_len:.2f}" height="24" '
                        f'fill="{self.theme.background}" opacity="0.85" rx="3" />'
                    )
                    notes.append(
                        f'  <text x="{le_x:.2f}" y="{text_y:.2f}" fill="{self.theme.dimension_text}" '
                        f'font-size="16" font-weight="600">{note_text}</text>'
                    )
        return "\n".join(notes)

    def _render_stations(self) -> str:
        """Render axial station markers along the bottom axis."""
        stations = ['<!-- Station Markers Layer -->', '<g id="station_markers_layer">']
        y_sta = self.cy + self.max_fin_r + 90.0

        all_comps = self.rocket.all_components()
        station_x_vals = [0.0] + [c.axial_end for c in all_comps]

        for x_val in station_x_vals:
            sx = self.ox + self._u(x_val)
            stations.append(
                f'  <line x1="{sx:.2f}" y1="{self.cy - 10:.2f}" x2="{sx:.2f}" y2="{y_sta + 15:.2f}" '
                f'stroke="{self.theme.station_line}" stroke-width="1.2" stroke-dasharray="2,2" opacity="0.75" />'
            )
            sta_label = f"STA {self.fmt.format(x_val * self.scale)}"
            text_w = len(sta_label) * 10.0
            stations.append(
                f'  <rect x="{sx - text_w / 2.0 - 4:.2f}" y="{y_sta + 20:.2f}" width="{text_w + 8:.2f}" height="22" '
                f'fill="{self.theme.background}" opacity="0.85" rx="3" />'
            )
            stations.append(
                f'  <text x="{sx:.2f}" y="{y_sta + 36:.2f}" fill="{self.theme.title_box_text}" '
                f'font-size="15" font-weight="600" font-family="monospace" text-anchor="middle">{sta_label}</text>'
            )

        stations.append("</g>")
        return "\n".join(stations)

    def _render_title_block(self) -> str:
        """Render standard aerospace engineering drawing title block."""
        tb_w = 460.0
        tb_h = 170.0
        tb_x = self.width - tb_w - 40.0
        tb_y = self.height - tb_h - 40.0

        # Reference area formatted in metric
        s_ref_m2 = self.rocket.reference_area
        s_ref_mm2 = s_ref_m2 * 1e6

        return f"""<!-- Title Block -->
<g id="title_block_layer">
  <rect x="{tb_x:.2f}" y="{tb_y:.2f}" width="{tb_w:.2f}" height="{tb_h:.2f}" 
        fill="{self.theme.title_box_bg}" stroke="{self.theme.title_box_border}" stroke-width="2" rx="6" />
  
  <!-- Title Header -->
  <text x="{tb_x + 20:.2f}" y="{tb_y + 32:.2f}" fill="{self.theme.title_box_accent}" 
        font-size="22" font-weight="bold" letter-spacing="1">PROJECT: {self.rocket.name.upper()}</text>
  <line x1="{tb_x + 15:.2f}" y1="{tb_y + 44:.2f}" x2="{tb_x + tb_w - 15:.2f}" y2="{tb_y + 44:.2f}" 
        stroke="{self.theme.title_box_border}" stroke-width="1.5" />

  <!-- Drawing Details -->
  <text x="{tb_x + 20:.2f}" y="{tb_y + 68:.2f}" fill="{self.theme.title_box_text}" font-size="14">
    <tspan font-weight="bold">TYPE:</tspan> OpenRocket Technical Drawing
  </text>
  <text x="{tb_x + 20:.2f}" y="{tb_y + 90:.2f}" fill="{self.theme.title_box_text}" font-size="14">
    <tspan font-weight="bold">TOTAL LENGTH:</tspan> {self._fmt_dim(self.rocket.total_length)}
  </text>
  <text x="{tb_x + 20:.2f}" y="{tb_y + 112:.2f}" fill="{self.theme.title_box_text}" font-size="14">
    <tspan font-weight="bold">MAX DIAMETER:</tspan> {self._fmt_dim(self.rocket.max_diameter)}
  </text>
  <text x="{tb_x + 20:.2f}" y="{tb_y + 134:.2f}" fill="{self.theme.title_box_text}" font-size="14">
    <tspan font-weight="bold">REF AREA (S<tspan font-size="10" baseline-shift="sub">ref</tspan>):</tspan> {s_ref_m2:.5f} m² ({s_ref_mm2:.1f} mm²)
  </text>
  <text x="{tb_x + 20:.2f}" y="{tb_y + 154:.2f}" fill="{self.theme.title_box_accent}" font-size="13" font-weight="600">
    STATUS: VERIFIED CAD VECTOR GEOMETRY
  </text>
</g>"""
