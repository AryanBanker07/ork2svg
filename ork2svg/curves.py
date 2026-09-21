"""Mathematical formulations for rocket aerodynamic profiles."""

import math
from typing import List, Tuple
from .models import Component


def haack_profile(length: float, base_radius: float, c: float = 0.0, num_points: int = 100) -> List[Tuple[float, float]]:
    """
    Calculate Haack series nose cone profile points.
    
    x in [0, length].
    theta = arccos(1 - 2*x / length)
    r(x) = (R / sqrt(pi)) * sqrt(theta - sin(2*theta)/2 + C * sin^3(theta))
    
    C = 0.0: Von Kármán
    C = 1/3 (~0.333): LV-Haack
    C = 2/3 (~0.667): Tangent Haack
    """
    points = []
    if length <= 0 or base_radius <= 0:
        return [(0.0, 0.0), (length, base_radius)]
    
    inv_sqrt_pi = 1.0 / math.sqrt(math.pi)
    for i in range(num_points + 1):
        x = (i / num_points) * length
        ratio = 1.0 - (2.0 * x / length)
        # Numerical clamping for acos
        ratio = max(-1.0, min(1.0, ratio))
        theta = math.acos(ratio)
        term = theta - (math.sin(2.0 * theta) / 2.0) + (c * (math.sin(theta) ** 3))
        r = base_radius * inv_sqrt_pi * math.sqrt(max(0.0, term))
        points.append((x, r))
    return points


def conical_profile(length: float, fore_radius: float, aft_radius: float, num_points: int = 50) -> List[Tuple[float, float]]:
    """Calculate linear/conical profile points between fore and aft radii."""
    points = []
    if length <= 0:
        return [(0.0, aft_radius)]
    for i in range(num_points + 1):
        x = (i / num_points) * length
        r = fore_radius + (aft_radius - fore_radius) * (x / length)
        points.append((x, r))
    return points


def ogive_profile(length: float, base_radius: float, num_points: int = 100) -> List[Tuple[float, float]]:
    """Calculate tangent ogive nose cone profile points."""
    points = []
    if length <= 0 or base_radius <= 0:
        return [(0.0, 0.0), (length, base_radius)]
    rho = (base_radius ** 2 + length ** 2) / (2.0 * base_radius)
    for i in range(num_points + 1):
        x = (i / num_points) * length
        val = rho ** 2 - (length - x) ** 2
        r = math.sqrt(max(0.0, val)) + base_radius - rho
        points.append((x, max(0.0, r)))
    return points


def ellipsoidal_profile(length: float, base_radius: float, num_points: int = 100) -> List[Tuple[float, float]]:
    """Calculate ellipsoidal profile points."""
    points = []
    if length <= 0 or base_radius <= 0:
        return [(0.0, 0.0), (length, base_radius)]
    for i in range(num_points + 1):
        x = (i / num_points) * length
        term = 1.0 - ((length - x) / length) ** 2
        r = base_radius * math.sqrt(max(0.0, term))
        points.append((x, r))
    return points


def parabolic_profile(length: float, base_radius: float, k: float = 0.5, num_points: int = 100) -> List[Tuple[float, float]]:
    """Calculate parabolic series profile points."""
    points = []
    if length <= 0 or base_radius <= 0:
        return [(0.0, 0.0), (length, base_radius)]
    denom = 2.0 - k if (2.0 - k) != 0 else 1.0
    for i in range(num_points + 1):
        x = (i / num_points) * length
        norm_x = x / length
        r = base_radius * ((2.0 * norm_x - k * (norm_x ** 2)) / denom)
        points.append((x, max(0.0, r)))
    return points


def power_profile(length: float, base_radius: float, power: float = 0.5, num_points: int = 100) -> List[Tuple[float, float]]:
    """Calculate power series profile points r = R * (x/L)^power."""
    points = []
    if length <= 0 or base_radius <= 0:
        return [(0.0, 0.0), (length, base_radius)]
    for i in range(num_points + 1):
        x = (i / num_points) * length
        r = base_radius * ((x / length) ** power)
        points.append((x, r))
    return points


def generate_component_profile(component: Component, num_points: int = 100, global_coords: bool = True) -> List[Tuple[float, float]]:
    """
    Generate the upper profile points (x, r) for a component.
    If global_coords is True, x coordinates are shifted by component.axial_start.
    """
    c_type = component.component_type.lower()
    shape = component.shape.lower() if component.shape else ""
    length = component.length
    
    if c_type == "nosecone":
        base_r = component.aft_radius
        if "haack" in shape:
            local_pts = haack_profile(length, base_r, c=component.shape_parameter, num_points=num_points)
        elif "ogive" in shape:
            local_pts = ogive_profile(length, base_r, num_points=num_points)
        elif "ellipsoid" in shape:
            local_pts = ellipsoidal_profile(length, base_r, num_points=num_points)
        elif "parabolic" in shape:
            local_pts = parabolic_profile(length, base_r, k=component.shape_parameter or 0.5, num_points=num_points)
        elif "power" in shape:
            local_pts = power_profile(length, base_r, power=component.shape_parameter or 0.5, num_points=num_points)
        else:  # fallback to conical
            local_pts = conical_profile(length, 0.0, base_r, num_points=num_points)
            
    elif c_type == "transition":
        fore_r = component.fore_radius
        aft_r = component.aft_radius
        if "ogive" in shape:
            # Ogive transition approximation
            local_pts = conical_profile(length, fore_r, aft_r, num_points=num_points)
        else:
            local_pts = conical_profile(length, fore_r, aft_r, num_points=num_points)
            
    elif c_type == "bodytube":
        r = component.aft_radius
        local_pts = [(0.0, r), (length, r)]
        
    else:
        local_pts = [(0.0, component.aft_radius), (length, component.aft_radius)]

    if global_coords:
        offset = component.axial_start
        return [(x + offset, r) for x, r in local_pts]
    return local_pts
