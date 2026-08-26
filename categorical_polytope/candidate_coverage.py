"""Registered metric candidate spaces for V.7--V.14 coverage claims.

The open-ended API campaign ranges over arbitrary expressions and therefore has
no finite-dimensional covering radius.  This module defines a separate,
versioned collection of normal-form families.  Within each family the
parameter vector is the candidate: there are no unobserved expression-level
degrees of freedom.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import log10, sqrt
from typing import Callable, Iterable

from .base_search import Candidate
from .verification_campaign import VerificationRecord, verify_base, verify_combined, verify_interaction


@dataclass(frozen=True)
class ParameterAxis:
    name: str
    lower: float
    upper: float
    scale: str = "linear"

    def value(self, unit: float) -> float:
        if not 0.0 <= unit <= 1.0:
            raise ValueError(f"unit coordinate must lie in [0,1], got {unit}")
        if self.scale == "linear":
            return self.lower + unit * (self.upper - self.lower)
        if self.scale == "log10":
            return 10.0 ** (log10(self.lower) + unit * (log10(self.upper) - log10(self.lower)))
        raise ValueError(f"unsupported scale: {self.scale}")


@dataclass(frozen=True)
class RegisteredFamily:
    law: str
    family: str
    axes: tuple[ParameterAxis, ...]
    formula: str
    scope: str
    build: Callable[[dict[str, float]], VerificationRecord]

    @property
    def dimension(self) -> int:
        return len(self.axes)

    def parameters(self, unit_point: Iterable[float]) -> dict[str, float]:
        values = tuple(unit_point)
        if len(values) != self.dimension:
            raise ValueError(f"{self.family} expects {self.dimension} coordinates")
        return {axis.name: axis.value(unit) for axis, unit in zip(self.axes, values)}

    def evaluate(self, unit_point: Iterable[float]) -> VerificationRecord:
        return self.build(self.parameters(unit_point))


def cartesian_unit_grid(dimension: int, points_per_axis: int) -> list[tuple[float, ...]]:
    if dimension < 1:
        raise ValueError("dimension must be positive")
    if points_per_axis < 2:
        raise ValueError("an endpoint-including grid needs at least two points per axis")
    axis = tuple(i / (points_per_axis - 1) for i in range(points_per_axis))
    return [tuple(point) for point in product(axis, repeat=dimension)]


def cartesian_covering_radius(dimension: int, points_per_axis: int) -> float:
    """Exact radius in normalized Euclidean coordinates on ``[0,1]^d``."""
    if dimension < 1:
        raise ValueError("dimension must be positive")
    if points_per_axis < 2:
        raise ValueError("an endpoint-including grid needs at least two points per axis")
    return sqrt(dimension) / (2.0 * (points_per_axis - 1))


def coverage_certificate_status(status_counts: dict[str, int]) -> tuple[str, int]:
    """Fail-closed decision for a completely evaluated registered grid."""
    unresolved = sum(int(status_counts.get(key, 0)) for key in ("rejected", "outside_scope", "inconclusive"))
    if int(status_counts.get("counterexample", 0)):
        return "NUMERICAL SURVIVOR — adjudication required", unresolved
    if unresolved:
        return "WITHHELD — unresolved grid points", unresolved
    return "CONDITIONAL PASS under R(rho)", 0


def _num(value: float) -> str:
    return format(value, ".12g")


def _interaction(law: str, family: str, expr: str, params: dict[str, float]) -> VerificationRecord:
    note = "registered parameters: " + ", ".join(f"{key}={value:.12g}" for key, value in params.items())
    return verify_interaction(law, Candidate(family, expr, "registered-grid", note))


def _v7(p: dict[str, float]) -> VerificationRecord:
    expr = f"{_num(p['a'])}*(1-lam)+{_num(p['b'])}*sigma"
    return _interaction("V.7", "v7_linear_separable", expr, p)


def _fractional(law: str, family: str, p: dict[str, float]) -> VerificationRecord:
    expr = (f"{_num(p['a'])}*(1-lam)**{_num(p['alpha'])}"
            f"+{_num(p['b'])}*sigma**{_num(p['alpha'])}")
    return _interaction(law, family, expr, p)


def _v8(p: dict[str, float]) -> VerificationRecord:
    return _fractional("V.8", "v8_fractional_separable", p)


def _v9(p: dict[str, float]) -> VerificationRecord:
    expr = f"sqrt(({_num(p['a'])}*(1-lam))**2+({_num(p['b'])}*sigma)**2)"
    return _interaction("V.9", "v9_coupled_cone", expr, p)


def _v10(p: dict[str, float]) -> VerificationRecord:
    return _fractional("V.10", "v10_c1_fractional", p)


def _v11(p: dict[str, float]) -> VerificationRecord:
    expr = (f"tanh(({_num(p['a'])}*(1-lam)+{_num(p['b'])}*sigma)"
            f"/{_num(p['epsilon'])})")
    return _interaction("V.11", "v11_saturating_ridge", expr, p)


def _v12(p: dict[str, float]) -> VerificationRecord:
    expr = f"-(1-lam)**{_num(p['beta_lam'])}-sigma**{_num(p['beta_sigma'])}"
    note = "registered parameters: " + ", ".join(f"{key}={value:.12g}" for key, value in p.items())
    return verify_base("V.12", Candidate("v12_anisotropic_base", expr, "registered-grid", note))


def _v13(p: dict[str, float]) -> VerificationRecord:
    # x=1-lam and y=sigma; u and v are the interior maximizer coordinates.
    expr = (f"exp(-{_num(p['sharpness'])}*((1-lam-{_num(p['u'])})**2"
            f"+(sigma-{_num(p['v'])})**2))")
    note = "registered parameters: " + ", ".join(f"{key}={value:.12g}" for key, value in p.items())
    return verify_base("V.13", Candidate("v13_interior_peak", expr, "registered-grid", note))


def _v14(p: dict[str, float]) -> VerificationRecord:
    beta_lam, beta_sigma = p["beta_lam"], p["beta_sigma"]
    # q is weighted degree.  mix allocates q across the two active axes, so
    # alpha_lam/beta_lam + alpha_sigma/beta_sigma = q by construction.
    alpha_lam = p["q"] * p["mix"] * beta_lam
    alpha_sigma = p["q"] * (1.0 - p["mix"]) * beta_sigma
    seed_q = (1.0 + p["q"]) / 2.0
    seed_lam = seed_q * beta_lam
    seed_sigma = seed_q * beta_sigma
    base_expr = f"-(1-lam)**{_num(beta_lam)}-sigma**{_num(beta_sigma)}"
    # The higher-weight separable seed is asymptotically dominated by the
    # joint monomial.  It lets the campaign's corner-seeded coordinate search
    # enter the interior instead of being trapped where the product vanishes.
    pert_expr = (f"(1-lam)**{_num(alpha_lam)}*sigma**{_num(alpha_sigma)}"
                 f"+0.2*(1-lam)**{_num(seed_lam)}+0.2*sigma**{_num(seed_sigma)}")
    note = ("registered parameters: " + ", ".join(f"{key}={value:.12g}" for key, value in p.items())
            + f", alpha_lam={alpha_lam:.12g}, alpha_sigma={alpha_sigma:.12g}")
    return verify_combined(
        Candidate("v14_weighted_monomial_b", base_expr, "registered-grid", note),
        Candidate("v14_weighted_monomial_p", pert_expr, "registered-grid", note),
    )


REGISTERED_FAMILIES: tuple[RegisteredFamily, ...] = (
    RegisteredFamily(
        "V.7", "linear-separable",
        (ParameterAxis("a", 0.25, 1.0), ParameterAxis("b", 0.25, 1.0)),
        "P=a(1-lambda)+b sigma",
        "Positive finite slopes on both flat axes of the fixed quadratic base.", _v7,
    ),
    RegisteredFamily(
        "V.8", "fractional-separable",
        (ParameterAxis("alpha", 0.20, 0.80), ParameterAxis("a", 0.25, 1.0),
         ParameterAxis("b", 0.25, 1.0)),
        "P=a(1-lambda)^alpha+b sigma^alpha",
        "Separable 0<alpha<1 slice, bounded away from singular endpoints.", _v8,
    ),
    RegisteredFamily(
        "V.9", "coupled-cone",
        (ParameterAxis("a", 0.25, 1.0), ParameterAxis("b", 0.25, 1.0)),
        "P=sqrt((a(1-lambda))^2+(b sigma)^2)",
        "Degree-one anisotropic cone with both axes active.", _v9,
    ),
    RegisteredFamily(
        "V.10", "c1-fractional-separable",
        (ParameterAxis("alpha", 1.10, 1.50), ParameterAxis("a", 0.25, 1.0),
         ParameterAxis("b", 0.25, 1.0)),
        "P=a(1-lambda)^alpha+b sigma^alpha",
        "Separable 1<alpha<2 slice restricted to numerically resolved exponents.", _v10,
    ),
    RegisteredFamily(
        "V.11", "saturating-ridge",
        (ParameterAxis("a", 0.25, 1.0), ParameterAxis("b", 0.25, 1.0),
         ParameterAxis("epsilon", 0.002, 0.05, "log10")),
        "P=tanh((a(1-lambda)+b sigma)/epsilon)",
        "Bounded smooth ridges ranging from steep to moderately saturated.", _v11,
    ),
    RegisteredFamily(
        "V.12", "anisotropic-power-base",
        (ParameterAxis("beta_lam", 2.0, 8.0), ParameterAxis("beta_sigma", 2.0, 8.0)),
        "r=-(1-lambda)^beta_lam-sigma^beta_sigma; fixed linear push",
        "Coercive anisotropic power bases with beta_i>1.", _v12,
    ),
    RegisteredFamily(
        "V.13", "interior-gaussian-peak",
        (ParameterAxis("u", 0.10, 0.90), ParameterAxis("v", 0.10, 0.90),
         ParameterAxis("sharpness", 10.0, 10000.0, "log10")),
        "r=exp(-w[((1-lambda)-u)^2+(sigma-v)^2])",
        "Interior peaks separated from the boundary; log-scaled sharpness.", _v13,
    ),
    RegisteredFamily(
        "V.14", "weighted-monomial",
        (ParameterAxis("beta_lam", 2.0, 6.0), ParameterAxis("beta_sigma", 2.0, 6.0),
         ParameterAxis("q", 0.20, 0.55), ParameterAxis("mix", 0.20, 0.80)),
        "r=-x^beta_lam-y^beta_sigma; P=x^(q*mix*beta_lam)y^(q*(1-mix)*beta_sigma) plus a higher-weight search seed",
        "Two-axis weighted-homogeneous leaders with 0<q<1 and an asymptotically dominated separable seed.", _v14,
    ),
)


def family_by_law(law: str) -> RegisteredFamily:
    for family in REGISTERED_FAMILIES:
        if family.law == law:
            return family
    raise KeyError(law)
