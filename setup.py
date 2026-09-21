from setuptools import setup, find_packages

setup(
    name="ork2svg",
    version="0.1.0",
    description="Convert OpenRocket (.ork) files into dimensioned CAD SVG drawings and PNG images",
    author="Abhyuday Aerospace Team",
    packages=find_packages(),
    install_requires=[
        "resvg-py>=0.5.0",
    ],
    entry_points={
        "console_scripts": [
            "ork2svg=ork2svg.cli:main",
        ],
    },
    python_requires=">=3.8",
)
