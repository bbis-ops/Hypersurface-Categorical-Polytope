"""Concrete evaluation-design rules derived from metric coverage."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log, prod, sqrt
from typing import Sequence

from .eval_escape import samples_to_catch


@dataclass(frozen=True)
class GridDesign:
    """A sufficient axis-aligned grid design for an anisotropic box."""

    norm: str
    target_radii: tuple[float, ...]
    points_per_axis: tuple[int, ...]

    @property
    def total_points(self) -> int:
        return prod(self.points_per_axis)


@dataclass(frozen=True)
class LipschitzCertificate:
    """Extension of tested scores to the full domain via a Lipschitz bound."""

    sampled_max: float
    lipschitz_constant: float
    covering_radius: float
    threshold: float

    @property
    def global_upper_bound(self) -> float:
        return self.sampled_max + self.lipschitz_constant * self.covering_radius

    @property
    def certified(self) -> bool:
        return self.global_upper_bound <= self.threshold

    @property
    def required_sample_margin(self) -> float:
        return self.lipschitz_constant * self.covering_radius


def anisotropic_grid(target_radii: Sequence[float], *, norm: str = "linf") -> GridDesign:
    """
    Sufficient grid for failures containing a scaled metric ball.

    ``target_radii[i]`` is the physical radius on axis i. For scaled L-infinity,
    spacing <= 2*r_i is exact. For scaled L2, equal error allocation gives each
    scaled coordinate at most 1/sqrt(d), a transparent sufficient construction.
    """
    radii = tuple(float(r) for r in target_radii)
    if not radii or any(r <= 0.0 for r in radii):
        raise ValueError("target_radii must be nonempty and positive")
    if norm not in ("linf", "l2"):
        raise ValueError("norm must be 'linf' or 'l2'")
    factor = 1.0 if norm == "linf" else sqrt(len(radii))
    counts = tuple(ceil(1.0 + factor / (2.0 * r)) for r in radii)
    return GridDesign(norm, radii, counts)


def distributional_samples(
    failure_mass: float,
    miss_probability: float,
    *,
    detection_sensitivity: float = 1.0,
) -> int:
    """
    IID samples needed so a failure set of mass at least mu is missed with
    probability at most alpha. If the evaluator detects a sampled failure with
    sensitivity q, the per-draw detection probability is at least mu*q.
    """
    if not 0.0 < failure_mass < 1.0:
        raise ValueError("failure_mass must lie in (0,1)")
    if not 0.0 < miss_probability < 1.0:
        raise ValueError("miss_probability must lie in (0,1)")
    if not 0.0 < detection_sensitivity <= 1.0:
        raise ValueError("detection_sensitivity must lie in (0,1]")
    detection_mass = failure_mass * detection_sensitivity
    return ceil(log(miss_probability) / log(1.0 - detection_mass))


def distributional_miss_bound(
    samples: int,
    failure_mass: float,
    *,
    detection_sensitivity: float = 1.0,
) -> float:
    """Upper bound (1-mu*q)^n under IID or a conditional per-draw lower bound."""
    if samples < 0:
        raise ValueError("samples must be nonnegative")
    if not 0.0 < failure_mass < 1.0:
        raise ValueError("failure_mass must lie in (0,1)")
    if not 0.0 < detection_sensitivity <= 1.0:
        raise ValueError("detection_sensitivity must lie in (0,1]")
    return (1.0 - failure_mass * detection_sensitivity) ** samples


def shift_robust_distributional_samples(
    deployment_failure_mass: float,
    miss_probability: float,
    density_ratio_bound: float,
    *,
    detection_sensitivity: float = 1.0,
) -> int:
    """
    Distribution-shift bound. If dP_deploy/dP_eval <= W, a deployment failure
    region of mass mu has eval mass at least mu/W. This requires absolute
    continuity and a justified finite W; without them there is no transfer.
    """
    if density_ratio_bound < 1.0:
        raise ValueError("density_ratio_bound must be at least 1")
    return distributional_samples(
        deployment_failure_mass / density_ratio_bound,
        miss_probability,
        detection_sensitivity=detection_sensitivity,
    )


def lipschitz_certificate(
    sampled_max: float,
    lipschitz_constant: float,
    covering_radius: float,
    *,
    threshold: float = 0.0,
) -> LipschitzCertificate:
    """Certify H(x)<=threshold using max_i H(x_i)+L*rho <= threshold."""
    if lipschitz_constant < 0.0 or covering_radius < 0.0:
        raise ValueError("lipschitz_constant and covering_radius must be nonnegative")
    return LipschitzCertificate(
        float(sampled_max), float(lipschitz_constant), float(covering_radius), float(threshold)
    )


def mixed_space_grid_samples(
    categorical_strata: int, continuous_dimension: int, delta: float
) -> int:
    """Worst-case grid count when every discrete stratum needs a continuous cover."""
    if categorical_strata < 1:
        raise ValueError("categorical_strata must be positive")
    return categorical_strata * samples_to_catch(delta, continuous_dimension)
