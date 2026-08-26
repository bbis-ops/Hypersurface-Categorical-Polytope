# Unified law V.14: p = beta/(beta-alpha)  (stealth/ox-alpha@openrouter.ai)

9 breaking pairs screened, 2 base-self-fail, 0 law violations.

base x perturbation -> measured vs predicted gap exponent:
```
  sextic_cbrt_b x sextic_cbrt_p    beta= 6.00 alpha= 0.33 pred p= 1.059 meas p= 1.059 law=yes
  aniso_sqrt_b  x aniso_sqrt_p     beta= 6.00 alpha= 0.50 pred p= 1.091 meas p= 1.091 law=yes
  quartic_sqrt_bx quartic_sqrt_p   beta= 4.00 alpha= 0.50 pred p= 1.143 meas p= 1.143 law=yes
  odd_flat_vs_sqrt_cou_bx odd_flat_vs_sqrt_cou_p beta= 3.00 alpha= 0.50 pred p= 1.200 meas p= 1.223 law=yes
  odd_flat_vs_sqrt_cou_bx odd_flat_vs_sqrt_cou_p beta= 6.00 alpha= 1.00 pred p= 1.200 meas p= 1.225 law=yes
  quartic_linear_bx quartic_linear_p beta= 4.00 alpha= 1.00 pred p= 1.333 meas p= 1.333 law=yes
  quartic_cone_bx quartic_cone_p   beta= 4.00 alpha= 1.00 pred p= 1.333 meas p= 1.333 law=yes
  quad_sqrt_b   x quad_sqrt_p      beta= 2.00 alpha= 0.50 pred p= 1.333 meas p= 1.333 law=yes
  quad_linear_b x quad_linear_p    beta= 2.00 alpha= 1.00 pred p= 2.000 meas p= 2.000 law=yes

base self-fails (max off-corner even at s=0):
  anisotropic_offcorne_bx anisotropic_offcorne_p BASE SELF-FAILS
  offcorner_max_fight_bx offcorner_max_fight_p BASE SELF-FAILS

## Counterexamples: 0
  none - the unified law held across every combination.
```