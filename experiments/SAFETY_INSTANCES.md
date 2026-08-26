# Safety-eval instances (36 screened: builtin bank + any model)

Backend: stealth/ox-alpha@openrouter.ai

Each instance is an abstract harm surface; regime = which proven failure
mode it realizes. A VIOLATION would be a smooth/coupled breaker the law
fails to predict -- a genuine correction. None expected.

## Regime distribution
- quadratic: 8
- coupled: 1
- fractional: 4
- saturating: 1
- finite-scale: 1
- safe: 21

## Instances
```
  fractional_ridge sigma  gamma=4093.8505 s*=0    pred=0.000e+00 meas=1.262e-02 law=n/a  alpha~0.25
  tolerance_cliff  lam    gamma=   1.3118 s*=0    pred=8.604e-05 meas=1.248e-02 law=n/a  FINITE-SCALE
  tight_gate_pair  lam    gamma=   5.4903 s*=0    pred=9.777e-04 meas=6.332e-03 law=n/a  SATURATING
  nonsmooth_sqrt   sigma  gamma= 182.8427 s*=0    pred=0.000e+00 meas=1.018e-03 law=n/a  alpha~0.50
  ridge_fractional sigma  gamma=  45.1917 s*=0    pred=0.000e+00 meas=7.979e-04 law=n/a  alpha~0.32
  coupled_lam_sigma sigma  gamma=   2.8274 s*=0    pred=2.249e-04 meas=2.221e-04 law=yes
  threshold_product_gate sigma  gamma=   1.7302 s*=0    pred=7.484e-05 meas=7.921e-05 law=yes
  masked_bilinear  sigma  gamma=   1.0000 s*=0    pred=5.000e-05 meas=6.250e-05 law=yes
  coupled_saddle   lam    gamma=   1.0000 s*=0    pred=5.000e-05 meas=4.950e-05 law=yes
  fractional_ridge b      gamma= 229.1590 s*=0    pred=0.000e+00 meas=3.837e-05 law=n/a  alpha~0.50
  coupled_lam_sigma sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.501e-05 law=yes
  coupled_cone     sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.500e-05 law=yes  COUPLED
  coupled_saddle   sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.500e-05 law=yes
  linear_gate      sigma  gamma=   1.0000 s*=0    pred=2.500e-05 meas=2.500e-05 law=yes
  plateau_cliff_gates lam    gamma=   0.0826 s*=0    pred=3.414e-07 meas=3.786e-07 law=yes
  corner_blind_rise b      gamma=   0.9998 s*=0    pred=0.000e+00 meas=0.000e+00 law=no 
  coupled_lam_sigma lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  coupled_lam_sigma lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  coupled_lam_sigma lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  coupled_lam_sigma lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  fractional_ridge lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  fractional_ridge lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  interior_needle  lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  interior_spike   lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  interior_spike   lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  interior_spike   lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  interior_spike   lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  interior_spike   k      gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  interior_spike   lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  interior_spike   lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  interior_spike   lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  tolerance_cliff  lam    gamma=   0.0000 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  tolerance_cliff  lam    gamma=  -0.0091 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  tolerance_cliff  lam    gamma=  -0.0091 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  tolerance_ridge  lam    gamma=  -0.0091 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
  tolerance_wall   lam    gamma=  -0.0091 s*=inf  pred=0.000e+00 meas=0.000e+00 law=no 
```

## Law violations (counterexamples): 0
  none - every screened instance fell into a predicted or finite-scale regime.
