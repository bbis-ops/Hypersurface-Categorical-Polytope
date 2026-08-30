"""
`python -m categorical_polytope.adjudication.polyhedra` - the forward predictor.

A module of its own rather than a `__main__` guard inside `predict`, because
the package imports `predict` eagerly and running that module directly would
load it twice.
"""

from .predict import main

raise SystemExit(main())
