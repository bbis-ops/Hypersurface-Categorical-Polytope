# Discoveries (automated)

Generated: 2026-08-26 12:32 UTC

**10 findings** from systematic search over obstruction, certification, localization, algorithms, and stability.

## Algorithm

### Fisher top-k pruning sensitivity (`prune_topk_gap`) — **Lemma E.1**

top_k=1 loses 0.0000 vs full probe; top_k=4 loses 0.0000 (CCC corner value 7.0000).

*Theorem 3 pruning is safe only when marginals rank the true pair in top-k.*

```json
{
  "full_value": 7.0,
  "top1_value": 7.0,
  "top4_value": 7.0,
  "miss_top1": 0.0,
  "miss_top4": 0.0,
  "pairs_top1": 1,
  "pairs_top4": 16,
  "theorem_ref": "Lemma E.1"
}
```

## Certification

### Strict certification boundary (2-block Fisher toy) (`cert_boundary_fisher`) — **Proposition B.1**

Separable factorization is strictly certified for f <~ 0.181; fails above (epsilon or gap vs Phi).

*Operational epsilon_0 band aligns with coupling ~0.10–0.15 in this toy.*

```json
{
  "boundary_f": 0.1812,
  "certified_at": 0.16124999999999998,
  "certified_at_result": true,
  "fails_at": 0.20124999999999996,
  "fails_at_result": false,
  "theorem_ref": "Proposition B.1"
}
```

### Tightest certified gap vs Phi(epsilon) (`phi_slack_sweet_spot`) — **Lemma B.2**

Among certified couplings, max gap/Phi ~ 0.908 at f=0.07 (bound is conservative elsewhere).

*Phi is rarely tight; certification fails mainly via epsilon_0, not gap alone.*

```json
{
  "best_f": 0.07,
  "best_ratio": 0.9076,
  "certified_sample": [
    {
      "f": 0.13,
      "epsilon": 0.18384776310850237,
      "gap": 0.38520001072500953,
      "phi": 0.43502999941014764,
      "ratio": 0.8854562012902512
    },
    {
      "f": 0.14,
      "epsilon": 0.19798989873223333,
      "gap": 0.4461126736111103,
      "phi": 0.5087939965518904,
      "ratio": 0.8768041223647036
    },
    {
      "f": 0.15,
      "epsilon": 0.21213203435596426,
      "gap": 0.511874999999999,
      "phi": 0.5906249999999998,
      "ratio": 0.8666666666666651
    },
    {
      "f": 0.16,
      "epsilon": 0.2262741699796952,
      "gap": 0.5826852049910869,
      "phi": 0.6814768382154351,
      "ratio": 0.8550330287335205
    },
    {
      "f": 0.17,
      "epsilon": 0.2404163056034262,
      "gap": 0.6587821008593426,
      "phi": 0.7824945179994118,
      "ratio": 0.8418999567481159
    }
  ],
  "theorem_ref": "Lemma B.2"
}
```

## Localization

### face_bowl breaks vertex localization (`face_bowl_onset`) — **Theorem C.1 (Counterexample)**

Interior (lambda,sigma) face wins over corners from strength ~0.188 (grid gain 0.0018).

*Theorem 1 hypotheses fail; extremal search alone is unsound.*

```json
{
  "onset_strength": 0.1875,
  "theta_vertex": [
    1.0,
    0.0,
    2.0,
    3.0
  ],
  "theta_grid": [
    0.875,
    0.125,
    2.0,
    3.0
  ],
  "value_vertex": 7.10546875,
  "value_grid": 7.1072235107421875,
  "gap_vs_grid": 0.0017547607421875,
  "theorem_ref": "Theorem C.1 (Counterexample)"
}
```

### Nonlinear interaction localization map (`interaction_landscape`) — **Proposition C.2**

Grid reference beats vertex-only search in 9 cases: structural (6): trig@0.5, trig@1.0, trig@1.5, face_bowl@0.5; cross-block coupling (3): bilinear@0.5, bilinear@1.0, bilinear@1.5.

*face_bowl/trig/softplus break axis quasiconvexity; strong bilinear/triple violate separate monotonicity — Theorem 1 does not apply.*

```json
{
  "grid": [
    {
      "mode": "bilinear",
      "strength": 0.0,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "bilinear",
      "strength": 0.5,
      "vertex_ok": false,
      "gap_vs_grid": 0.055556,
      "theta_grid_interior": true
    },
    {
      "mode": "bilinear",
      "strength": 1.0,
      "vertex_ok": false,
      "gap_vs_grid": 0.25,
      "theta_grid_interior": true
    },
    {
      "mode": "bilinear",
      "strength": 1.5,
      "vertex_ok": false,
      "gap_vs_grid": 0.055556,
      "theta_grid_interior": true
    },
    {
      "mode": "triple",
      "strength": 0.0,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "triple",
      "strength": 0.5,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "triple",
      "strength": 1.0,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "triple",
      "strength": 1.5,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "softplus",
      "strength": 0.0,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "softplus",
      "strength": 0.5,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "softplus",
      "strength": 1.0,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "softplus",
      "strength": 1.5,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "trig",
      "strength": 0.0,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "trig",
      "strength": 0.5,
      "vertex_ok": false,
      "gap_vs_grid": 0.754913,
      "theta_grid_interior": true
    },
    {
      "mode": "trig",
      "strength": 1.0,
      "vertex_ok": false,
      "gap_vs_grid": 1.749995,
      "theta_grid_interior": true
    },
    {
      "mode": "trig",
      "strength": 1.5,
      "vertex_ok": false,
      "gap_vs_grid": 2.749992,
      "theta_grid_interior": true
    },
    {
      "mode": "face_bowl",
      "strength": 0.0,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_grid_interior": false
    },
    {
      "mode": "face_bowl",
      "strength": 0.5,
      "vertex_ok": false,
      "gap_vs_grid": 0.058256,
      "theta_grid_interior": true
    },
    {
      "mode": "face_bowl",
      "strength": 1.0,
      "vertex_ok": false,
      "gap_vs_grid": 0.172068,
      "theta_grid_interior": true
    },
    {
      "mode": "face_bowl",
      "strength": 1.5,
      "vertex_ok": false,
      "gap_vs_grid": 0.351852,
      "theta_grid_interior": true
    }
  ],
  "failures": [
    "bilinear@0.5",
    "bilinear@1.0",
    "bilinear@1.5",
    "trig@0.5",
    "trig@1.0",
    "trig@1.5",
    "face_bowl@0.5",
    "face_bowl@1.0",
    "face_bowl@1.5"
  ],
  "structural_breaks": [
    "trig@0.5",
    "trig@1.0",
    "trig@1.5",
    "face_bowl@0.5",
    "face_bowl@1.0",
    "face_bowl@1.5"
  ],
  "cross_block_breaks": [
    "bilinear@0.5",
    "bilinear@1.0",
    "bilinear@1.5"
  ],
  "theorem_ref": "Proposition C.2"
}
```

### Hypersurface vertex invariant under Fisher coupling (`hypersurface_corner_invariant`) — **Lemma D.1**

Vertex probe stays at (1,0,2,3) for all tested f (confirmed).

*Coupling affects separable gap, not corner argmax on this box.*

```json
{
  "thetas_by_f": {
    "0.0": [
      1.0,
      0.0,
      2.0,
      3.0
    ],
    "0.05": [
      1.0,
      0.0,
      2.0,
      3.0
    ],
    "0.1": [
      1.0,
      0.0,
      2.0,
      3.0
    ],
    "0.25": [
      1.0,
      0.0,
      2.0,
      3.0
    ],
    "0.35": [
      1.0,
      0.0,
      2.0,
      3.0
    ]
  },
  "theorem_ref": "Lemma D.1"
}
```

## Obstruction

### Minimal coexponential obstruction in Set (`obstruction_minimal`) — **Proposition A.1**

No representable coexponential for |Y|=2, |A|=2 (smallest found in scan).

*Formal dual to coproduct is empty already for 2-element probes.*

```json
{
  "y": 2,
  "a": 2,
  "reason": "cardinality mismatch: |Hom(C,Z)| = |Z|^|C| cannot match |Hom(Y,A+Z)| = (|A|+|Z|)^|Y| for all Z unless trivial constants.",
  "hom_Y_AplusZ_at_Z2": 16,
  "theorem_ref": "Proposition A.1"
}
```

### Exponential vs polynomial growth in |Z| (`growth_rate_mismatch`) — **Lemma A.2**

cardinality mismatch: |Hom(C,Z)| = |Z|^|C| cannot match |Hom(Y,A+Z)| = (|A|+|Z|)^|Y| for all Z unless trivial constants.

*No fixed finite C can represent the coproduct functor for all Z.*

```json
{
  "y": 2,
  "a": 2,
  "ratio_hom_coproduct_over_hom_C": [
    9.0,
    4.0,
    2.7777777777777777,
    2.25,
    1.96
  ],
  "z_values": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "theorem_ref": "Lemma A.2"
}
```

### CCC corner beats coexponential shadow (`conceptual_ccc_corner`) — **Proposition G.1**

Global diagram max at PRODUCT_EXPONENTIAL (U=3.000); coproduct blocks still peak at inhabited corners.

*Operational substitute aligns with product/exp, not empty coexp.*

```json
{
  "global_vertex": "PRODUCT_EXPONENTIAL",
  "global_point": {
    "product_exp": 1,
    "coproduct_coexp": 0,
    "composition": 1,
    "naturality": 1,
    "cross_naturality": 0
  },
  "per_block": [
    {
      "block": "A",
      "vertex": "PRODUCT_EXPONENTIAL",
      "U": 3.0
    },
    {
      "block": "B",
      "vertex": "GENERIC_INTERIOR",
      "U": 2.9
    }
  ],
  "theorem_ref": "Proposition G.1"
}
```

## Stability

### Decomposition strategy phase transitions (`strategy_transitions`) — **Proposition F.1**

2 strategy changes along coupling sweep; first JOINT_SOLVE near epsilon=0.3535533905932738.

*Design rules R1–R5 are discrete phases, not a smooth continuum.*

```json
{
  "transitions": [
    {
      "epsilon": 0.07071067811865477,
      "from": "SEPARABLE_PROBE",
      "to": "BLOCK_COORDINATE_ASCENT",
      "coproduct_robust": false
    },
    {
      "epsilon": 0.3535533905932738,
      "from": "BLOCK_COORDINATE_ASCENT",
      "to": "JOINT_SOLVE",
      "coproduct_robust": false
    }
  ],
  "theorem_ref": "Proposition F.1"
}
```
