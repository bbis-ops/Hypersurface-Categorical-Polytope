# Interaction search

```
Interaction search: 20 candidates at s=0.01

  17 break vertex localization, 3 safe, 0 rejected

BREAKS (largest measured gap first):
  angular_ridge    sigma  gamma= 500.2078 s*=0    pred=6.255e+00 meas=1.432e-02 law=n/a  SATURATING
  cbrt_sigma       sigma  gamma=1009.4537 s*=0    pred=0.000e+00 meas=2.318e-03 law=n/a  alpha~0.33
  sqrt_sigma       sigma  gamma= 182.8427 s*=0    pred=0.000e+00 meas=1.018e-03 law=n/a  alpha~0.50
  trig             lam    gamma=   6.2832 s*=0    pred=9.870e-04 meas=9.838e-04 law=yes
  sin_lam          lam    gamma=   3.1416 s*=0    pred=2.467e-04 meas=2.465e-04 law=yes
  sigma_times_b    sigma  gamma=   2.0000 s*=0    pred=1.000e-04 meas=1.000e-04 law=yes
  face_bowl        lam    gamma=   0.7500 s*=0    pred=2.812e-05 meas=2.805e-05 law=yes
  bilinear         sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.500e-05 law=yes
  cone_dist        sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.500e-05 law=yes  COUPLED
  diag_kink        sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.500e-05 law=yes  COUPLED
  linear_sigma     sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.500e-05 law=yes
  one_minus_lam    lam    gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.500e-05 law=yes
  tanh_sigma       sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.500e-05 law=yes
  log1p_sigma      sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.488e-05 law=yes
  rational_sigma   sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.475e-05 law=yes
  exp_neg_lam      lam    gamma=   0.3679 s*=0    pred=3.383e-06 meas=3.390e-06 law=yes
  c1_power         sigma  gamma=   0.0041 s*=0    pred=2.500e-11 meas=1.046e-09 law=n/a  alpha~1.50

SAFE (no inward push at the degenerate corner):
  cos_pi_sigma     no inward push
  sigma_sq         no inward push
  triple           no inward push

NON-SMOOTH candidates found: unbounded inward derivative at the
corner. These break localization but do NOT follow the quadratic
law - they need their own exponent. See fractional_exponent_law.

COUPLED candidates found: the perturbation couples flat axes, so the
additive law (V.7) over-predicts. 'pred' shows the directional law
(V.9), which matches. See directional_gap.

FRACTIONAL / HIGHER-ORDER candidates (homogeneity alpha != 1): gap
follows the unified exponent law Delta ~ s^(2/(2-alpha)) (V.10), not
the quadratic law. See fractional_exponent_law / gap_exponent.

SATURATING candidates: a near-singular bounded ridge (e.g. atan(y/x)).
The corner-derivative law predicts more than the amplitude ceiling
s*sup|P|, so leading-order theory is INVALID; the gap is amplitude-
limited. See amplitude_bound.
```
