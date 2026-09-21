"""Parser for OpenRocket (.ork) files, handling XML, ZIP, and GZIP formats."""

import gzip
import io
from pathlib import Path
from typing import List, Optional, Tuple, Union
import xml.etree.ElementTree as ET
import zipfile

from .models import Component, FinSet, Rocket, Stage


def _clean_float(val_str: Optional[str], default: float = 0.0) -> float:
    """Safely parse a float string, removing 'auto' prefix if present."""
    if val_str is None:
        return default
    s = val_str.replace("auto", "").strip()
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _clean_int(val_str: Optional[str], default: int = 1) -> int:
    """Safely parse an integer string."""
    if val_str is None:
        return default
    s = val_str.strip()
    try:
        return int(s)
    except ValueError:
        return default


def _load_xml_root(file_path: Union[str, Path]) -> ET.Element:
    """Load XML root element from a file, supporting plain XML, ZIP, or GZIP."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"OpenRocket file not found: {p}")

    with open(p, "rb") as f:
        header = f.read(16)
        f.seek(0)
        raw_bytes = f.read()

    # Check for ZIP header (PK\x03\x04)
    if raw_bytes.startswith(b"PK\x03\x04"):
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
            names = z.namelist()
            target_name = None
            if "rocket.ork" in names:
                target_name = "rocket.ork"
            else:
                for n in names:
                    if n.endswith(".ork") or n.endswith(".xml"):
                        target_name = n
                        break
            if target_name is None and names:
                target_name = names[0]
            if target_name is None:
                raise ValueError(f"ZIP archive {p.name} contains no entries.")
            xml_data = z.read(target_name)
            return ET.fromstring(xml_data)

    # Check for GZIP header (\x1f\x8b)
    if raw_bytes.startswith(b"\x1f\x8b"):
        xml_data = gzip.decompress(raw_bytes)
        return ET.fromstring(xml_data)

    # Plain text / XML
    try:
        return ET.fromstring(raw_bytes)
    except ET.ParseError as e:
        # Retry with string decoding
        text = raw_bytes.decode("utf-8", errors="replace")
        return ET.fromstring(text)


def _parse_fin_set(elem: ET.Element, parent_length: float) -> FinSet:
    """Parse a fin set XML element into a FinSet dataclass."""
    name = elem.findtext("name", "Fin Set")
    fin_type = elem.tag.replace("finset", "")
    fin_count = _clean_int(elem.findtext("fincount"), default=_clean_int(elem.findtext("instancecount"), 4))
    
    root_chord = _clean_float(elem.findtext("rootchord"), 0.0)
    tip_chord = _clean_float(elem.findtext("tipchord"), 0.0)
    span = _clean_float(elem.findtext("height"), 0.0)
    sweep_length = _clean_float(elem.findtext("sweeplength"), 0.0)
    thickness = _clean_float(elem.findtext("thickness"), 0.003)
    
    pos_elem = elem.find("position")
    pos_type = pos_elem.attrib.get("type", "bottom") if pos_elem is not None else "bottom"
    pos_val = _clean_float(pos_elem.text, 0.0) if (pos_elem is not None and pos_elem.text) else 0.0
    
    # Calculate root/tip LE and TE relative to parent component front (x=0)
    if pos_type == "bottom":
        # Root trailing edge is at (parent_length - pos_val)
        root_te_x = parent_length - pos_val
        root_le_x = root_te_x - root_chord
    elif pos_type == "middle":
        mid = parent_length / 2.0 + pos_val
        root_le_x = mid - (root_chord / 2.0)
        root_te_x = root_le_x + root_chord
    else:  # "top"
        root_le_x = pos_val
        root_te_x = root_le_x + root_chord

    tip_le_x = root_le_x + sweep_length
    tip_te_x = tip_le_x + tip_chord

    return FinSet(
        name=name,
        fin_type=fin_type,
        fin_count=fin_count,
        root_chord=root_chord,
        tip_chord=tip_chord,
        span=span,
        sweep_length=sweep_length,
        thickness=thickness,
        position_type=pos_type,
        position_offset=pos_val,
        root_le_x=root_le_x,
        root_te_x=root_te_x,
        tip_le_x=tip_le_x,
        tip_te_x=tip_te_x,
    )


def _parse_component(elem: ET.Element) -> Optional[Component]:
    """Parse a single aerodynamic component element."""
    c_type = elem.tag.lower()
    if c_type not in ["nosecone", "transition", "bodytube"]:
        return None

    name = elem.findtext("name", c_type.capitalize())
    length = _clean_float(elem.findtext("length"), 0.0)
    thickness = _clean_float(elem.findtext("thickness"), 0.0)
    material = elem.findtext("material", "")
    shape = elem.findtext("shape", "")
    shape_param = _clean_float(elem.findtext("shapeparameter"), 0.0)

    # Radii
    if c_type == "nosecone":
        aft_r = _clean_float(elem.findtext("aftradius") or elem.findtext("radius"), 0.0)
        fore_r = 0.0
    elif c_type == "transition":
        fore_r = _clean_float(elem.findtext("foreradius"), 0.0)
        aft_r = _clean_float(elem.findtext("aftradius"), 0.0)
    else:  # bodytube
        r = _clean_float(elem.findtext("radius"), 0.0)
        fore_r = r
        aft_r = r

    # Extract subcomponent fins
    fins = []
    sub = elem.find("subcomponents")
    if sub is not None:
        for sub_elem in sub:
            if "fin" in sub_elem.tag.lower():
                fin_set = _parse_fin_set(sub_elem, parent_length=length)
                fins.append(fin_set)

    return Component(
        name=name,
        component_type=c_type,
        length=length,
        fore_radius=fore_r,
        aft_radius=aft_r,
        shape=shape,
        shape_parameter=shape_param,
        material=material,
        thickness=thickness,
        fins=fins,
    )


def parse_ork_file(file_path: Union[str, Path]) -> Rocket:
    """
    Parse an OpenRocket (.ork) file into a fully qualified Rocket model.
    Computes all cumulative axial coordinate positions from nose to tail.
    """
    root = _load_xml_root(file_path)
    rocket_elem = root.find("rocket")
    if rocket_elem is None:
        rocket_elem = root  # root might be rocket directly

    rocket_name = rocket_elem.findtext("name", Path(file_path).stem)
    
    stages: List[Stage] = []
    current_axial_x = 0.0

    # Search for stage elements
    stage_elems = rocket_elem.findall(".//stage")
    if not stage_elems:
        # Single implicit stage
        stage_elems = [rocket_elem]

    for s_idx, s_elem in enumerate(stage_elems):
        s_name = s_elem.findtext("name", f"Stage {s_idx + 1}")
        subcomponents = s_elem.find("subcomponents")
        if subcomponents is None and s_elem.tag == "rocket":
            subcomponents = s_elem
            
        if subcomponents is None:
            continue

        stage_start_x = current_axial_x
        components: List[Component] = []

        for comp_elem in subcomponents:
            comp = _parse_component(comp_elem)
            if comp is not None and comp.length > 0:
                comp.axial_start = current_axial_x
                comp.axial_end = current_axial_x + comp.length
                current_axial_x = comp.axial_end
                components.append(comp)

        if components:
            stage = Stage(
                name=s_name,
                components=components,
                axial_start=stage_start_x,
                axial_end=current_axial_x,
            )
            stages.append(stage)

    # Resolve any 'auto' radius inheritance:
    # If transition fore/aft radius is 0, infer from neighbor components
    all_comps = [c for s in stages for c in s.components]
    for idx, c in enumerate(all_comps):
        if c.component_type == "transition":
            if c.fore_radius == 0.0 and idx > 0:
                c.fore_radius = all_comps[idx - 1].aft_radius
            if c.aft_radius == 0.0 and idx < len(all_comps) - 1:
                c.aft_radius = all_comps[idx + 1].fore_radius

    return Rocket(name=rocket_name, stages=stages)
