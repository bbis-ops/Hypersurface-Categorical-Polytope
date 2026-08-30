"""
Hand-written seed cases for domain three.

Enough geometry to exercise every path without an API call, and deliberately
unflattering: unbounded systems, degenerate vertices, and unparseable payloads
are all here, because a seed bank of only well-posed cases would never exercise
the scope guard.

SIMPLEX is the reference geometry. Its vertex (0,1) is simple but tilted - the
edges are 45 degrees apart - so the edge and ambient measurements disagree there.
BOX is the control: domain one's own geometry, where they cannot disagree.

One seed is not like the others. `box_orders_2_4_product_push` was CONSTRUCTED
after screening showed the corpus held nothing that could separate the minimum
rule from the maximum - it was built to that specification rather than found by
search, and it is the same case the tests pin as `PRODUCT_SYS`. It is therefore
evidence that the adjudicator selects the minimum where the two rules differ,
and it is NOT independent adversarial evidence the way an API-proposed
counterexample is. A reader counting confirmations should know which it is.
Everything else here was written before the gap was measured.
"""

from __future__ import annotations

from dataclasses import dataclass

SIMPLEX = "([[-1,0],[0,-1],[1,1]], [0,0,1])"
BOX = "([[1,0],[-1,0],[0,1],[0,-1]], [1,0,1,0])"
SHEARED = "([[-1,0],[0,-1],[1,2]], [0,0,2])"
HALFPLANE = "([[-1,0],[0,-1]], [0,0])"
TRIANGLE_3D = "([[-1,0,0],[0,-1,0],[0,0,-1],[1,1,1]], [0,0,0,1])"


@dataclass(frozen=True)
class Seed:
    rule_id: str
    name: str
    system: str
    base: str
    pert: str
    note: str = ""


EDGE = "polyhedron/edge_exponent_law"
AMBIENT = "polyhedron/ambient_exponent_law"
LINEAR = "polyhedron/linear_max_at_vertex"

SEEDS: tuple[Seed, ...] = (
    # -- the experiment: same geometry, two coordinate systems ---------------
    Seed(EDGE, "simplex_quartic_edge", SIMPLEX, "-((x0+x1-1)**2 + x0**4)", "x0",
         "quartic along one edge, quadratic along the other"),
    Seed(AMBIENT, "simplex_quartic_ambient", SIMPLEX, "-((x0+x1-1)**2 + x0**4)", "x0",
         "same geometry measured on axes; expected to disagree"),
    Seed(EDGE, "sheared_quartic_edge", SHEARED, "-((x0+2*x1-2)**2 + x0**4)", "x0",
         "sheared simplex, tilted vertex"),
    Seed(AMBIENT, "sheared_quartic_ambient", SHEARED, "-((x0+2*x1-2)**2 + x0**4)", "x0",
         "sheared simplex on axes"),

    # -- control: on a box the two measurements cannot differ ----------------
    Seed(EDGE, "box_quadratic_edge", BOX, "-((1-x0)**2 + (1-x1)**2)", "(1-x0)",
         "domain one's own geometry; edges are axes"),
    Seed(AMBIENT, "box_quadratic_ambient", BOX, "-((1-x0)**2 + (1-x1)**2)", "(1-x0)",
         "same, on axes; must agree with the edge case"),

    # -- 3D ------------------------------------------------------------------
    Seed(EDGE, "simplex3d_edge", TRIANGLE_3D, "-((x0+x1+x2-1)**2 + x0**4)", "x0",
         "three-dimensional simplex"),

    # -- the selection clause, which nothing else here reaches ---------------
    # Every other seed has admissible faces that agree about q, so a maximum
    # rule would have returned the same exponent and the row cannot tell the
    # two apart. This one can: orders (2, 4) at the origin with a push that
    # survives on both edges gives q = 1/2 and q = 1/4, BOTH below 1, so the
    # minimum rule predicts 4/3 and the maximum rule predicts 2 and measurement
    # chooses between two finite numbers. Constructed after the gap was
    # measured, not found by search - see the note in the module docstring.
    Seed(EDGE, "box_orders_2_4_product_push", BOX, "-(x0**2 + x1**4)", "x0 + x1",
         "faces disagree with both degrees below 1: separates min from max"),

    # -- linear control: a theorem, present to catch false positives ---------
    Seed(LINEAR, "simplex_linear", SIMPLEX, "2*x0 - 3*x1", "0", "LP fundamental theorem"),
    Seed(LINEAR, "box_linear", BOX, "x0 + x1", "0", "maximum at a corner"),
    Seed(LINEAR, "sheared_linear", SHEARED, "-x0 + 4*x1", "0", "tilted geometry"),
    Seed(LINEAR, "simplex3d_linear", TRIANGLE_3D, "x0 + 2*x1 + 3*x2", "0", "3D vertex"),

    # -- out of scope: hypotheses genuinely unmet ----------------------------
    Seed(EDGE, "unbounded_quadrant", HALFPLANE, "-(x0**2 + x1**2)", "x0",
         "no upper constraint: unbounded, so no maximum to speak of"),
    Seed(EDGE, "base_rises_inward", SIMPLEX, "x0 + x1", "x0",
         "vertex is not a local max of the base"),
    Seed(EDGE, "degree_out_of_range", SIMPLEX, "-((x0+x1-1)**2 + x0**2)", "x0**3",
         "weighted degree falls outside (0,1)"),

    # -- refused at the parse boundary ---------------------------------------
    Seed(EDGE, "system_not_literal", "__import__('os').system('echo pwned')",
         "-(x0**2)", "x0", "hostile payload"),
    Seed(EDGE, "expression_not_whitelisted", SIMPLEX, "__import__('os').getcwd()", "x0",
         "expression outside the whitelist"),
    Seed(EDGE, "ragged_matrix", "([[1,0],[0,1,1]], [1,1])", "-(x0**2)", "x0",
         "malformed constraint matrix"),
)
