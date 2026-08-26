# Registered candidate-space coverage certificate

This is the missing metric bridge for the V.7–V.14 campaign. It is a
**restricted normal-form coverage claim**, not a claim that arbitrary model-generated
expressions or prompts form a finite-dimensional Cartesian space.

## Two-layer design

- **Open adversarial layer:** currently 80 logged API request batches and 1410 unique
  generated candidates. This measures demonstrated adversarial-search behavior but has no
  exhaustive covering-radius claim.
- **Registered coverage layer (registry v1):** the bounded families below. Within a family, the normalized
  parameter vector is the candidate and the metric is Euclidean distance on `[0,1]^d`.

Registry v1 was designed after the open campaign and calibrated with boundary probes, so this
run is an **exploratory calibration certificate**, not a retrospectively claimed preregistration.
The code and ranges now provide a frozen target for an unchanged confirmatory rerun.

## Certificate theorem and regularity assumption

For an endpoint-including Cartesian grid with `m` points per normalized parameter axis,
the exact covering radius is

`rho = sqrt(d)/(2(m-1))`.

**Minimum-width assumption R(rho):** within each registered family, every relevant
counterexample set contains a closed relative metric ball of radius at least `rho`.
If every grid point is conclusively verified and R(rho) holds, every relevant
counterexample in that registered family would be detected. This is conditional on R(rho);
the experiment does not estimate or silently assume it.

Equivalently, a margin formulation may replace R: if a violation functional `H` is
`L`-Lipschitz and every relevant failure has margin at least `eta`, it is enough that
`rho < eta/L`. No numerical `L` or `eta` is claimed here.

## Results

| Law | Registered family | d | Grid | Exact rho | verified | counterexamples | unresolved | Outcome |
|---|---|---:|---:|---:|---:|---:|---:|---|
| V.7 | linear-separable | 2 | 3^2=9 | 0.353553 | 9 | 0 | 0 | CONDITIONAL PASS under R(rho) |
| V.8 | fractional-separable | 3 | 3^3=27 | 0.433013 | 27 | 0 | 0 | CONDITIONAL PASS under R(rho) |
| V.9 | coupled-cone | 2 | 3^2=9 | 0.353553 | 9 | 0 | 0 | CONDITIONAL PASS under R(rho) |
| V.10 | c1-fractional-separable | 3 | 3^3=27 | 0.433013 | 25 | 1 | 1 | NUMERICAL SURVIVOR — adjudication required |
| V.11 | saturating-ridge | 3 | 3^3=27 | 0.433013 | 27 | 0 | 0 | CONDITIONAL PASS under R(rho) |
| V.12 | anisotropic-power-base | 2 | 3^2=9 | 0.353553 | 9 | 0 | 0 | CONDITIONAL PASS under R(rho) |
| V.13 | interior-gaussian-peak | 3 | 3^3=27 | 0.433013 | 27 | 0 | 0 | CONDITIONAL PASS under R(rho) |
| V.14 | weighted-monomial | 4 | 3^4=81 | 0.500000 | 69 | 9 | 3 | NUMERICAL SURVIVOR — adjudication required |

## Registered domains

### V.7 — linear-separable

- Formula: `P=a(1-lambda)+b sigma`
- Scope: Positive finite slopes on both flat axes of the fixed quadratic base.
- Normalization: `a` in [0.25, 1.0] (linear) -> [0,1]; `b` in [0.25, 1.0] (linear) -> [0,1]
- Exact normalized Euclidean covering radius: `0.353553390593`.
- Status: **CONDITIONAL PASS under R(rho)**.

### V.8 — fractional-separable

- Formula: `P=a(1-lambda)^alpha+b sigma^alpha`
- Scope: Separable 0<alpha<1 slice, bounded away from singular endpoints.
- Normalization: `alpha` in [0.2, 0.8] (linear) -> [0,1]; `a` in [0.25, 1.0] (linear) -> [0,1]; `b` in [0.25, 1.0] (linear) -> [0,1]
- Exact normalized Euclidean covering radius: `0.433012701892`.
- Status: **CONDITIONAL PASS under R(rho)**.

### V.9 — coupled-cone

- Formula: `P=sqrt((a(1-lambda))^2+(b sigma)^2)`
- Scope: Degree-one anisotropic cone with both axes active.
- Normalization: `a` in [0.25, 1.0] (linear) -> [0,1]; `b` in [0.25, 1.0] (linear) -> [0,1]
- Exact normalized Euclidean covering radius: `0.353553390593`.
- Status: **CONDITIONAL PASS under R(rho)**.

### V.10 — c1-fractional-separable

- Formula: `P=a(1-lambda)^alpha+b sigma^alpha`
- Scope: Separable 1<alpha<2 slice restricted to numerically resolved exponents.
- Normalization: `alpha` in [1.1, 1.5] (linear) -> [0,1]; `a` in [0.25, 1.0] (linear) -> [0,1]; `b` in [0.25, 1.0] (linear) -> [0,1]
- Exact normalized Euclidean covering radius: `0.433012701892`.
- Status: **NUMERICAL SURVIVOR — adjudication required**.

Non-verified grid points:

- `counterexample` at `{"a": 0.25, "alpha": 1.3, "b": 0.25}`: in-scope exponent mismatch
- `outside_scope` at `{"a": 0.25, "alpha": 1.5, "b": 0.25}`: measured homogeneity is outside this theorem slice

### V.11 — saturating-ridge

- Formula: `P=tanh((a(1-lambda)+b sigma)/epsilon)`
- Scope: Bounded smooth ridges ranging from steep to moderately saturated.
- Normalization: `a` in [0.25, 1.0] (linear) -> [0,1]; `b` in [0.25, 1.0] (linear) -> [0,1]; `epsilon` in [0.002, 0.05] (log10) -> [0,1]
- Exact normalized Euclidean covering radius: `0.433012701892`.
- Status: **CONDITIONAL PASS under R(rho)**.

### V.12 — anisotropic-power-base

- Formula: `r=-(1-lambda)^beta_lam-sigma^beta_sigma; fixed linear push`
- Scope: Coercive anisotropic power bases with beta_i>1.
- Normalization: `beta_lam` in [2.0, 8.0] (linear) -> [0,1]; `beta_sigma` in [2.0, 8.0] (linear) -> [0,1]
- Exact normalized Euclidean covering radius: `0.353553390593`.
- Status: **CONDITIONAL PASS under R(rho)**.

### V.13 — interior-gaussian-peak

- Formula: `r=exp(-w[((1-lambda)-u)^2+(sigma-v)^2])`
- Scope: Interior peaks separated from the boundary; log-scaled sharpness.
- Normalization: `u` in [0.1, 0.9] (linear) -> [0,1]; `v` in [0.1, 0.9] (linear) -> [0,1]; `sharpness` in [10.0, 10000.0] (log10) -> [0,1]
- Exact normalized Euclidean covering radius: `0.433012701892`.
- Status: **CONDITIONAL PASS under R(rho)**.

### V.14 — weighted-monomial

- Formula: `r=-x^beta_lam-y^beta_sigma; P=x^(q*mix*beta_lam)y^(q*(1-mix)*beta_sigma) plus a higher-weight search seed`
- Scope: Two-axis weighted-homogeneous leaders with 0<q<1 and an asymptotically dominated separable seed.
- Normalization: `beta_lam` in [2.0, 6.0] (linear) -> [0,1]; `beta_sigma` in [2.0, 6.0] (linear) -> [0,1]; `q` in [0.2, 0.55] (linear) -> [0,1]; `mix` in [0.2, 0.8] (linear) -> [0,1]
- Exact normalized Euclidean covering radius: `0.5`.
- Status: **NUMERICAL SURVIVOR — adjudication required**.

Non-verified grid points:

- `counterexample` at `{"beta_lam": 2.0, "beta_sigma": 2.0, "mix": 0.5, "q": 0.375}`: in-scope weighted exponent mismatch
- `counterexample` at `{"beta_lam": 2.0, "beta_sigma": 2.0, "mix": 0.8, "q": 0.375}`: in-scope weighted exponent mismatch
- `outside_scope` at `{"beta_lam": 2.0, "beta_sigma": 2.0, "mix": 0.2, "q": 0.55}`: pair does not satisfy weighted coercive-corner hypotheses
- `outside_scope` at `{"beta_lam": 2.0, "beta_sigma": 2.0, "mix": 0.5, "q": 0.55}`: pair does not satisfy weighted coercive-corner hypotheses
- `outside_scope` at `{"beta_lam": 2.0, "beta_sigma": 2.0, "mix": 0.8, "q": 0.55}`: pair does not satisfy weighted coercive-corner hypotheses
- `counterexample` at `{"beta_lam": 2.0, "beta_sigma": 4.0, "mix": 0.2, "q": 0.55}`: in-scope weighted exponent mismatch
- `counterexample` at `{"beta_lam": 2.0, "beta_sigma": 6.0, "mix": 0.2, "q": 0.55}`: in-scope weighted exponent mismatch
- `counterexample` at `{"beta_lam": 2.0, "beta_sigma": 6.0, "mix": 0.5, "q": 0.55}`: in-scope weighted exponent mismatch
- `counterexample` at `{"beta_lam": 4.0, "beta_sigma": 2.0, "mix": 0.5, "q": 0.55}`: in-scope weighted exponent mismatch
- `counterexample` at `{"beta_lam": 4.0, "beta_sigma": 2.0, "mix": 0.8, "q": 0.55}`: in-scope weighted exponent mismatch
- `counterexample` at `{"beta_lam": 6.0, "beta_sigma": 2.0, "mix": 0.5, "q": 0.55}`: in-scope weighted exponent mismatch
- `counterexample` at `{"beta_lam": 6.0, "beta_sigma": 2.0, "mix": 0.8, "q": 0.55}`: in-scope weighted exponent mismatch

## Claim boundary

The certificate covers only the explicitly registered normal-form families and parameter
ranges above. The open API corpus remains valuable adversarial evidence and can discover
failures outside these families, but its candidate count must not be substituted for `m^d`.
A theorem proved analytically retains the scope of its proof; this grid tests the executable
implementation and supplies conditional finite-family detection evidence.

## Reproduce

`python experiments/run_candidate_coverage.py --points-per-axis 3`
