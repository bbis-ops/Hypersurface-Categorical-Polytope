"""Canonical calculations: the repository's worked examples and counterexamples."""

from __future__ import annotations

from .counter import PYRAMID, SIMPLEX, SQUARE

CUBE = "([[-1,0,0],[0,-1,0],[0,0,-1],[1,0,0],[0,1,0],[0,0,1]], [0,0,0,1,1,1])"

PRESETS: dict[str, dict] = {
    "tilted-simplex": {
        "title": "Tilted simplex",
        "note": "The decisive example: ambient axes predict 2, the feasible chart gives 4/3.",
        "request": {"system": SIMPLEX, "base": "-((x0+x1-1)**2 + x0**4)", "perturbation": "x0"},
    },
    "sheared-simplex": {
        "title": "Sheared simplex",
        "note": "A different chart with the same transported Newton data (V.20).",
        "request": {"system": "([[-1,0],[0,-1],[1,2]], [0,0,2])", "base": "-((x0+2*x1-2)**2 + x0**4)",
                    "perturbation": "x0"},
    },
    "signed-channel": {
        "title": "Signed channel",
        "note": "No face qualifies, yet a curved channel gives s³/432 (mathematical audit §1).",
        "request": {"system": SQUARE, "base": "-(x0**6+x1**6)", "perturbation": "-x0**2+x0*x1**2"},
    },
    "signed-sharp": {
        "title": "Signed channel plus y⁵",
        "note": "A face qualifies with γ = 6, but the curved channel still gives order s³.",
        "request": {"system": SQUARE, "base": "-(x0**6+x1**6)", "perturbation": "-x0**2+x0*x1**2+x1**5"},
    },
    "curved-cancellation": {
        "title": "Reduced-layer cancellation",
        "note": "V.22 after cancelling the quartic layer: γ = 6 with coefficient 3125/46656.",
        "request": {"system": SQUARE, "base": "-(x0**6+x1**6)", "perturbation": "-x0**2+x0*x1**2-x1**4/4+x1**5"},
    },
    "interior-zero": {
        "title": "Interior zero set",
        "note": "Negative axis forms, yet x = y = 3s/8 gains 27s⁴/2048 (audit §2).",
        "request": {"system": SQUARE, "base": "-(x0**4+x1**4)", "perturbation": "-(x0-x1)**2+x0**3"},
    },
    "active-set": {
        "title": "Leading channel versus support",
        "note": "γ = 4/3 on the x axis, while the optimizer also moves in y (audit §6).",
        "request": {"system": SQUARE, "base": "-(x0**4+x1**4)", "perturbation": "x0+x1**2"},
    },
    "tied-faces": {
        "title": "Tied faces",
        "note": "Two axes tie at q* = 1/4: one exponent, a coefficient from both terms.",
        "request": {"system": SQUARE, "base": "-(x0**4+x1**4)", "perturbation": "x0+x1"},
    },
    "cross-term": {
        "title": "Cross term at the principal weight",
        "note": "The backend licenses γ = 2 from a homogeneity probe; Hypothesis 2 fails exactly.",
        "request": {"system": SQUARE, "base": "-(x0**2+x0*x1+x1**2)", "perturbation": "x0"},
    },
    "tied-maximizers": {
        "title": "Two base maximizers",
        "note": "Hypothesis 0 fails: F is maximal at (0,0) and (1,0).",
        "request": {"system": SQUARE, "base": "-((x0*(1-x0))**2 + x1**2)", "perturbation": "x0"},
    },
    "critical-layer": {
        "title": "Critical layer",
        "note": "q = 1: the calculator proves Δ(s) = 0 for small s (Lemma 2).",
        "request": {"system": SQUARE, "base": "-(x0**2 + x1**2)", "perturbation": "x0**2"},
    },
    "pyramid-apex": {
        "title": "Pyramid apex",
        "note": "Four active constraints in dimension three: not a simple vertex.",
        "request": {"system": PYRAMID, "base": "x2", "perturbation": "x0"},
    },
    "cube-3d": {
        "title": "Unit cube, three weights",
        "note": "Weights 1/2, 1/4, 1/6; the x2 edge wins with q* = 1/6 and γ = 6/5.",
        "request": {"system": CUBE, "base": "-(x0**2+x1**4+x2**6)", "perturbation": "x0*x1 + x2 - x1**2"},
    },
}


def preset_request(name: str) -> dict:
    if name not in PRESETS:
        raise KeyError(f"unknown preset {name!r}; choose from {', '.join(PRESETS)}")
    return dict(PRESETS[name]["request"], request_id=name)
