"""
Domain three: the exponent laws on a general polyhedron.

Domain one's box is a hypercube, where a corner's edges are the coordinate axes.
This domain removes that coincidence and asks the same law in both coordinate
systems, so the harness records which one it actually lives in.

`PolyhedronDomain` runs it backwards - claim in, verdict out - and `predict`
runs it forwards, geometry in, exponent out. Note that the name `predict`
re-exported here is the FUNCTION; reach the module it lives in as
`categorical_polytope.adjudication.polyhedra.predict` in a `from ... import`,
which resolves the submodule regardless.
"""

from .domain import RULE_IDS, PolyhedronDomain
from .geometry import GeometryError, Polyhedron, Vertex, box, simplex
from .predict import (
    Face,
    Hypotheses,
    Prediction,
    calibrate,
    consistent_faces,
    predict,
)
__all__ = ["RULE_IDS", "Face", "GeometryError", "Hypotheses", "Polyhedron",
           "PolyhedronDomain", "Prediction", "Vertex", "box", "calibrate",
           "consistent_faces", "predict", "simplex"]
