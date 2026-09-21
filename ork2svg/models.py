"""Data models for OpenRocket components and rocket hierarchy."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class FinSet:
    """Represents a set of fins attached to a body tube or transition."""
    name: str
    fin_type: str  # trapezoid, elliptical, freeform
    fin_count: int
    root_chord: float  # meters
    tip_chord: float  # meters
    span: float  # meters (height from body surface)
    sweep_length: float  # meters (axial distance from root LE to tip LE)
    thickness: float  # meters
    position_type: str  # "top", "bottom", "middle"
    position_offset: float  # meters
    # Computed coordinates relative to parent component start (x=0 is parent component front)
    root_le_x: float = 0.0
    root_te_x: float = 0.0
    tip_le_x: float = 0.0
    tip_te_x: float = 0.0


@dataclass
class Component:
    """Represents a rocket component (NoseCone, Transition, BodyTube)."""
    name: str
    component_type: str  # "nosecone", "transition", "bodytube"
    length: float  # meters
    fore_radius: float  # meters
    aft_radius: float  # meters
    shape: str = ""  # "haack", "conical", "ogive", "ellipsoid", "parabolic", "powerseries"
    shape_parameter: float = 0.0  # e.g., C for Haack (0=von Karman, 0.33=LV-Haack)
    material: str = ""
    thickness: float = 0.0
    fins: List[FinSet] = field(default_factory=list)
    # Global axial stations along the rocket (meters, nose tip = 0.0)
    axial_start: float = 0.0
    axial_end: float = 0.0

    @property
    def max_radius(self) -> float:
        return max(self.fore_radius, self.aft_radius)


@dataclass
class Stage:
    """Represents a rocket stage (e.g. Sustainer, Booster)."""
    name: str
    components: List[Component] = field(default_factory=list)
    axial_start: float = 0.0
    axial_end: float = 0.0

    @property
    def length(self) -> float:
        return self.axial_end - self.axial_start


@dataclass
class Rocket:
    """Represents an entire rocket assembly with multiple stages."""
    name: str
    stages: List[Stage] = field(default_factory=list)

    @property
    def total_length(self) -> float:
        if not self.stages:
            return 0.0
        return max(stage.axial_end for stage in self.stages)

    @property
    def max_diameter(self) -> float:
        max_r = 0.0
        for stage in self.stages:
            for comp in stage.components:
                max_r = max(max_r, comp.fore_radius, comp.aft_radius)
        return max_r * 2.0

    @property
    def reference_area(self) -> float:
        """Frontal reference area S_ref = pi * D_max^2 / 4."""
        import math
        d = self.max_diameter
        return math.pi * (d / 2.0) ** 2

    @property
    def max_fin_span_diameter(self) -> float:
        """Total tip-to-tip diameter including fins."""
        max_d = self.max_diameter
        for stage in self.stages:
            for comp in stage.components:
                for fin in comp.fins:
                    tip_dia = (comp.aft_radius + fin.span) * 2.0
                    max_d = max(max_d, tip_dia)
        return max_d

    def all_components(self) -> List[Component]:
        comps = []
        for stage in self.stages:
            comps.extend(stage.components)
        return comps


@dataclass
class DrawingTheme:
    """Color palette and styling theme for CAD/SVG rendering."""
    name: str
    background: str
    grid_major: str
    grid_minor: str
    rocket_fill: str
    rocket_stroke: str
    fin_fill: str
    fin_stroke: str
    centerline: str
    station_line: str
    dimension_line: str
    dimension_text: str
    title_box_bg: str
    title_box_border: str
    title_box_text: str
    title_box_accent: str


DARK_THEME = DrawingTheme(
    name="dark",
    background="#0d1117",
    grid_major="#21262d",
    grid_minor="#161b22",
    rocket_fill="#1f2937",
    rocket_stroke="#58a6ff",
    fin_fill="#26354a",
    fin_stroke="#79c0ff",
    centerline="#e3b341",
    station_line="#30363d",
    dimension_line="#f0883e",
    dimension_text="#f0883e",
    title_box_bg="#161b22",
    title_box_border="#30363d",
    title_box_text="#c9d1d9",
    title_box_accent="#58a6ff",
)

LIGHT_THEME = DrawingTheme(
    name="light",
    background="#ffffff",
    grid_major="#e1e4e8",
    grid_minor="#f6f8fa",
    rocket_fill="#f0f4f8",
    rocket_stroke="#0969da",
    fin_fill="#e1ecf8",
    fin_stroke="#0550ae",
    centerline="#9a6700",
    station_line="#d0d7de",
    dimension_line="#bc4c00",
    dimension_text="#bc4c00",
    title_box_bg="#f6f8fa",
    title_box_border="#d0d7de",
    title_box_text="#24292f",
    title_box_accent="#0969da",
)

BLUEPRINT_THEME = DrawingTheme(
    name="blueprint",
    background="#0b2545",
    grid_major="#133d6b",
    grid_minor="#0e2f54",
    rocket_fill="#134074",
    rocket_stroke="#8da9c4",
    fin_fill="#1d4e89",
    fin_stroke="#eef4f8",
    centerline="#f4d35e",
    station_line="#1f4e79",
    dimension_line="#ffffff",
    dimension_text="#ffffff",
    title_box_bg="#081d36",
    title_box_border="#8da9c4",
    title_box_text="#eef4f8",
    title_box_accent="#f4d35e",
)
