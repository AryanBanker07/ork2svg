"""Unit and integration tests for ork2svg package."""

import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from ork2svg.curves import conical_profile, haack_profile, ogive_profile
from ork2svg.exporter import save_png, save_svg
from ork2svg.models import BLUEPRINT_THEME, DARK_THEME, LIGHT_THEME
from ork2svg.parser import parse_ork_file
from ork2svg.renderer import SVGRenderer


class TestCurves(unittest.TestCase):
    def test_haack_profile(self):
        pts = haack_profile(length=1.0, base_radius=0.1, c=0.3, num_points=50)
        self.assertEqual(len(pts), 51)
        self.assertAlmostEqual(pts[0][0], 0.0)
        self.assertAlmostEqual(pts[0][1], 0.0)
        self.assertAlmostEqual(pts[-1][0], 1.0)
        self.assertAlmostEqual(pts[-1][1], 0.1, places=3)

    def test_conical_profile(self):
        pts = conical_profile(length=2.0, fore_radius=0.05, aft_radius=0.1, num_points=20)
        self.assertEqual(len(pts), 21)
        self.assertAlmostEqual(pts[0][1], 0.05)
        self.assertAlmostEqual(pts[-1][1], 0.1)
        # Midpoint linearity
        self.assertAlmostEqual(pts[10][1], 0.075)


class TestParser(unittest.TestCase):
    def setUp(self):
        self.banana3_path = Path(r"c:\Users\banke\OneDrive\Desktop\abhyuday\year 2\Openrocket Mods\banana3.ork")

    def test_parse_banana3(self):
        if not self.banana3_path.exists():
            self.skipTest("banana3.ork not found")
        rocket = parse_ork_file(self.banana3_path)
        self.assertEqual(rocket.name, "Banana3")
        self.assertAlmostEqual(rocket.total_length, 4.885, places=3)
        self.assertAlmostEqual(rocket.max_diameter, 0.146, places=3)
        self.assertEqual(len(rocket.stages), 2)

        # Check Sustainer components
        sustainer = rocket.stages[0]
        self.assertEqual(sustainer.name, "Sustainer")
        self.assertAlmostEqual(sustainer.length, 3.005, places=3)
        self.assertEqual(len(sustainer.components), 5)

        # Check Booster components
        booster = rocket.stages[1]
        self.assertAlmostEqual(booster.length, 1.880, places=3)
        self.assertEqual(len(booster.components), 2)


class TestRenderer(unittest.TestCase):
    def setUp(self):
        self.banana3_path = Path(r"c:\Users\banke\OneDrive\Desktop\abhyuday\year 2\Openrocket Mods\banana3.ork")

    def test_render_svg_structure(self):
        if not self.banana3_path.exists():
            self.skipTest("banana3.ork not found")
        rocket = parse_ork_file(self.banana3_path)
        renderer = SVGRenderer(rocket, theme=DARK_THEME, unit="mm")
        svg = renderer.render()

        # Check well-formed XML
        root = ET.fromstring(svg)
        self.assertTrue(root.tag.endswith("svg"))

        # Verify critical elements
        self.assertIn("TOTAL LENGTH: 4885 mm", svg)
        self.assertIn("Ø 146 mm", svg)
        self.assertIn("Ø 108 mm", svg)
        self.assertIn("SPAN Ø 388 mm", svg)
        self.assertIn("PROJECT: BANANA3", svg)
        self.assertIn("openfoam_axisymmetric_profile", svg)

    def test_render_themes(self):
        if not self.banana3_path.exists():
            self.skipTest("banana3.ork not found")
        rocket = parse_ork_file(self.banana3_path)
        for theme in [DARK_THEME, LIGHT_THEME, BLUEPRINT_THEME]:
            renderer = SVGRenderer(rocket, theme=theme)
            svg = renderer.render()
            self.assertIn(theme.background, svg)


class TestExporter(unittest.TestCase):
    def setUp(self):
        self.banana3_path = Path(r"c:\Users\banke\OneDrive\Desktop\abhyuday\year 2\Openrocket Mods\banana3.ork")
        self.test_dir = Path(r"c:\Users\banke\OneDrive\Desktop\abhyuday\year 2\Openrocket Mods\ork2svg\tests\temp")
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_svg_and_png_export(self):
        if not self.banana3_path.exists():
            self.skipTest("banana3.ork not found")
        rocket = parse_ork_file(self.banana3_path)
        renderer = SVGRenderer(rocket)
        svg = renderer.render()

        svg_file = self.test_dir / "test_rocket.svg"
        png_file = self.test_dir / "test_rocket.png"

        save_svg(svg, svg_file)
        self.assertTrue(svg_file.exists())
        self.assertGreater(svg_file.stat().st_size, 1000)

        save_png(svg, png_file, dpi=150.0)
        self.assertTrue(png_file.exists())
        self.assertGreater(png_file.stat().st_size, 10000)


if __name__ == "__main__":
    unittest.main()
