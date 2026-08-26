# Research discoveries (automated)

Generated: 2026-05-23 02:22 UTC

**9 findings** from systematic search over obstruction, certification, localization, algorithms, and stability.

## Certification

### Enrichment weights shift epsilon and certification (`enriched_epsilon_cert_flip`)

V-enrichment: 5/18 pairs change epsilon; 3 flip strict certification vs unweighted.

*Fisher matrix in a V-category is a weighted enrichment; limits/colimits dual depends on weight asymmetry.*

```json
{
  "rows": [
    {
      "coupling": 0.0,
      "epsilon_unweighted": 0.0,
      "epsilon_enriched": 0.0,
      "block_w0": 1.0,
      "block_w1": 1.0,
      "cross_w": 1.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 1.0,
      "cert_flip": false
    },
    {
      "coupling": 0.0,
      "epsilon_unweighted": 0.0,
      "epsilon_enriched": 0.0,
      "block_w0": 1.0,
      "block_w1": 1.0,
      "cross_w": 12.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 1.0,
      "cert_flip": false
    },
    {
      "coupling": 0.0,
      "epsilon_unweighted": 0.0,
      "epsilon_enriched": 0.0,
      "block_w0": 0.15,
      "block_w1": 0.15,
      "cross_w": 1.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 1.0,
      "cert_flip": false
    },
    {
      "coupling": 0.05,
      "epsilon_unweighted": 0.07071067811865477,
      "epsilon_enriched": 0.07071067811865477,
      "block_w0": 1.0,
      "block_w1": 1.0,
      "cross_w": 1.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 1.0,
      "cert_flip": false
    },
    {
      "coupling": 0.05,
      "epsilon_unweighted": 0.07071067811865477,
      "epsilon_enriched": 0.8485281374238571,
      "block_w0": 1.0,
      "block_w1": 1.0,
      "cross_w": 12.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 0.0,
      "cert_flip": true
    },
    {
      "coupling": 0.05,
      "epsilon_unweighted": 0.07071067811865477,
      "epsilon_enriched": 0.07071067811865475,
      "block_w0": 0.15,
      "block_w1": 0.15,
      "cross_w": 1.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 1.0,
      "cert_flip": false
    },
    {
      "coupling": 0.1,
      "epsilon_unweighted": 0.14142135623730953,
      "epsilon_enriched": 0.14142135623730953,
      "block_w0": 1.0,
      "block_w1": 1.0,
      "cross_w": 1.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 1.0,
      "cert_flip": false
    },
    {
      "coupling": 0.1,
      "epsilon_unweighted": 0.14142135623730953,
      "epsilon_enriched": 1.6970562748477143,
      "block_w0": 1.0,
      "block_w1": 1.0,
      "cross_w": 12.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 0.0,
      "cert_flip": true
    },
    {
      "coupling": 0.1,
      "epsilon_unweighted": 0.14142135623730953,
      "epsilon_enriched": 0.1414213562373095,
      "block_w0": 0.15,
      "block_w1": 0.15,
      "cross_w": 1.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 1.0,
      "cert_flip": false
    },
    {
      "coupling": 0.15,
      "epsilon_unweighted": 0.21213203435596426,
      "epsilon_enriched": 0.21213203435596423,
      "block_w0": 1.0,
      "block_w1": 1.0,
      "cross_w": 1.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 1.0,
      "cert_flip": false
    },
    {
      "coupling": 0.15,
      "epsilon_unweighted": 0.21213203435596426,
      "epsilon_enriched": 2.5455844122715705,
      "block_w0": 1.0,
      "block_w1": 1.0,
      "cross_w": 12.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 0.0,
      "cert_flip": true
    },
    {
      "coupling": 0.15,
      "epsilon_unweighted": 0.21213203435596426,
      "epsilon_enriched": 0.21213203435596426,
      "block_w0": 0.15,
      "block_w1": 0.15,
      "cross_w": 1.0,
      "cert_unweighted": 1.0,
      "cert_enriched": 1.0,
      "cert_flip": false
    }
  ],
  "flip_count": 3,
  "epsilon_shift_count": 5,
  "total": 18
}
```

### Lawvere distance dampens cross-block epsilon (`lawvere_metric_epsilon`)

For 9/16 pairs, metric epsilon < plain as block distance grows; metric colimit-limit gap up to 1.00.

*V = Lawvere metric: hom cost exp(-d) weights Fisher off-diagonals.*

```json
{
  "rows": [
    {
      "coupling": 0.0,
      "block_distance": 0.0,
      "epsilon_plain": 0.0,
      "epsilon_lawvere": 0.0,
      "weight_cross": 1.0,
      "cert_plain": 1.0,
      "cert_lawvere": 1.0
    },
    {
      "coupling": 0.0,
      "block_distance": 0.3,
      "epsilon_plain": 0.0,
      "epsilon_lawvere": 0.0,
      "weight_cross": 0.7408182206817179,
      "cert_plain": 1.0,
      "cert_lawvere": 1.0
    },
    {
      "coupling": 0.0,
      "block_distance": 1.0,
      "epsilon_plain": 0.0,
      "epsilon_lawvere": 0.0,
      "weight_cross": 0.36787944117144233,
      "cert_plain": 1.0,
      "cert_lawvere": 1.0
    },
    {
      "coupling": 0.0,
      "block_distance": 2.0,
      "epsilon_plain": 0.0,
      "epsilon_lawvere": 0.0,
      "weight_cross": 0.1353352832366127,
      "cert_plain": 1.0,
      "cert_lawvere": 1.0
    },
    {
      "coupling": 0.1,
      "block_distance": 0.0,
      "epsilon_plain": 0.14142135623730953,
      "epsilon_lawvere": 0.14142135623730953,
      "weight_cross": 1.0,
      "cert_plain": 1.0,
      "cert_lawvere": 1.0
    },
    {
      "coupling": 0.1,
      "block_distance": 0.3,
      "epsilon_plain": 0.14142135623730953,
      "epsilon_lawvere": 0.104767517494119,
      "weight_cross": 0.7408182206817179,
      "cert_plain": 1.0,
      "cert_lawvere": 0.0
    },
    {
      "coupling": 0.1,
      "block_distance": 1.0,
      "epsilon_plain": 0.14142135623730953,
      "epsilon_lawvere": 0.052026009502288896,
      "weight_cross": 0.36787944117144233,
      "cert_plain": 1.0,
      "cert_lawvere": 0.0
    },
    {
      "coupling": 0.1,
      "block_distance": 2.0,
      "epsilon_plain": 0.14142135623730953,
      "epsilon_lawvere": 0.019139299302082188,
      "weight_cross": 0.1353352832366127,
      "cert_plain": 1.0,
      "cert_lawvere": 0.0
    }
  ],
  "metric_colimit_limit": [
    {
      "distance": 0.0,
      "colimit": 2.0,
      "limit": 1.0,
      "gap": 1.0
    },
    {
      "distance": 0.5,
      "colimit": 1.5,
      "limit": 1.5,
      "gap": 0.0
    },
    {
      "distance": 1.0,
      "colimit": 1.0,
      "limit": 2.0,
      "gap": -1.0
    },
    {
      "distance": 2.0,
      "colimit": 1.0,
      "limit": 2.0,
      "gap": -1.0
    }
  ]
}
```

## Learner

### Live epsilon triggers interior search (`learner_interior_switch`)

face_bowl learner switches from corner-hunting at strength 0.35; population interior rate 97%.

*Empirical Fisher on the diagram box H detects when a learner must abandon corner-hunting for interior search.*

```json
{
  "session": {
    "interaction": "face_bowl",
    "switch_strength": 0.35,
    "readings": [
      {
        "strength": 0.0,
        "mode": "CORNER_HUNTING",
        "epsilon": 0.0,
        "gap_vertex_grid": 0.0
      },
      {
        "strength": 0.1,
        "mode": "CORNER_HUNTING",
        "epsilon": 0.0,
        "gap_vertex_grid": 0.0
      },
      {
        "strength": 0.2,
        "mode": "CORNER_HUNTING",
        "epsilon": 0.0,
        "gap_vertex_grid": 0.003955078125000178
      },
      {
        "strength": 0.35,
        "mode": "INTERIOR_SEARCH",
        "epsilon": 0.0,
        "gap_vertex_grid": 0.030358886718749645
      },
      {
        "strength": 0.5,
        "mode": "INTERIOR_SEARCH",
        "epsilon": 0.0,
        "gap_vertex_grid": 0.0567626953125
      },
      {
        "strength": 0.8,
        "mode": "INTERIOR_SEARCH",
        "epsilon": 0.0,
        "gap_vertex_grid": 0.12812499999999982
      }
    ]
  },
  "population": {
    "n_learners": 30,
    "fraction_switching_to_interior": 0.9666666666666667,
    "interpretation": "When internal interaction (face_bowl) strengthens, live epsilon and grid gap trigger interior search."
  }
}
```

### Low-strength bilinear learners stay on corners (`learner_low_leakage_corners`)

Bilinear interaction at low strength keeps CORNER_HUNTING mode throughout schedule.

*Separable-like regimes: live epsilon supports cheap vertex probes.*

```json
{
  "readings": [
    {
      "strength": 0.0,
      "epsilon": 0.0,
      "gap_vertex_grid": 0.0,
      "certified": true,
      "mode": "CORNER_HUNTING",
      "reason": "low leakage and vertex localization \u2014 separable corner probe OK"
    },
    {
      "strength": 0.1,
      "epsilon": 0.0,
      "gap_vertex_grid": 0.0,
      "certified": true,
      "mode": "CORNER_HUNTING",
      "reason": "low leakage and vertex localization \u2014 separable corner probe OK"
    },
    {
      "strength": 0.2,
      "epsilon": 0.0,
      "gap_vertex_grid": 0.009375000000000355,
      "certified": true,
      "mode": "CORNER_HUNTING",
      "reason": "low leakage and vertex localization \u2014 separable corner probe OK"
    }
  ]
}
```

### Trajectory log detects interior need along path (`learner_trajectory_interior`)

Random-walk session: interior mode at step 3 (strength=0.24).

*Log theta_t live; epsilon and gap recorded each step for HITL learners.*

```json
{
  "n_steps": 14,
  "first_interior": {
    "step": 3,
    "lam": 0.9345072859986943,
    "sigma": 0.11996457949080369,
    "b": 1.8944444565250669,
    "k": 2.7968520924407847,
    "interaction_strength": 0.24,
    "epsilon": 0.0,
    "gap_vertex_grid": 0.010996093750000213,
    "mode": "INTERIOR_SEARCH",
    "reason": "grid beats vertex by 0.0110 \u2014 abandon corner-hunting"
  },
  "mode_counts": {
    "CORNER_HUNTING": 3,
    "INTERIOR_SEARCH": 11
  }
}
```

## Localization

### face_bowl onset is interaction-geometric, not setting-dependent (`localization_signature_geometric`)

Across categorical setting labels, face_bowl onset strength is uniform ([0.5, 0.5, 0.5, 0.5]); failure is from bowl term.

*Coexponential existence does not restore vertex localization if Theorem 1 hypotheses fail — interaction signature dominates.*

```json
{
  "setting_sweep": [
    {
      "setting": "FINITE_SET",
      "representable": false,
      "interaction_signature": "maximize_corners",
      "face_bowl_onset_strength": 0.5,
      "face_bowl_gap": 0.0567626953125
    },
    {
      "setting": "PRESHEAF_TOY",
      "representable": true,
      "interaction_signature": "maximize_corners",
      "face_bowl_onset_strength": 0.5,
      "face_bowl_gap": 0.0567626953125
    },
    {
      "setting": "ABELIAN_GROUP_TOY",
      "representable": true,
      "interaction_signature": "maximize_corners",
      "face_bowl_onset_strength": 0.5,
      "face_bowl_gap": 0.0567626953125
    },
    {
      "setting": "POINTED_SUSPENSION",
      "representable": true,
      "interaction_signature": "suspension_shift",
      "face_bowl_onset_strength": 0.5,
      "face_bowl_gap": 0.0567626953125
    }
  ],
  "face_bowl_curve": [
    {
      "interaction": "face_bowl",
      "strength": 0.0,
      "vertex_ok": true,
      "gap_vs_grid": 0.0,
      "theta_vertex": [
        1.0,
        0.0,
        2.0,
        3.0
      ],
      "theta_grid": [
        1.0,
        0.0,
        2.0,
        3.0
      ]
    },
    {
      "interaction": "face_bowl",
      "strength": 0.5,
      "vertex_ok": false,
      "gap_vs_grid": 0.0567626953125,
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
      ]
    },
    {
      "interaction": "face_bowl",
      "strength": 1.0,
      "vertex_ok": false,
      "gap_vs_grid": 0.19140625,
      "theta_vertex": [
        1.0,
        0.0,
        2.0,
        3.0
      ],
      "theta_grid": [
        0.75,
        0.25,
        2.0,
        3.0
      ]
    }
  ]
}
```

## Obstruction

### Coexponential-like functors outside Set (`coexponential_outside_set`)

3 / 4 toy settings admit representability proxies; only FINITE_SET is obstructed on the cardinality probe.

*Toposes / enriched homs / suspension shift the representing object; Set obstruction is not universal.*

```json
{
  "settings": [
    {
      "name": "FINITE_SET",
      "representable": false,
      "growth": "polynomial_in_Z_vs_exponential",
      "signature": "maximize_corners"
    },
    {
      "name": "PRESHEAF_TOY",
      "representable": true,
      "growth": "pointwise_exponential_in_site",
      "signature": "maximize_corners"
    },
    {
      "name": "ABELIAN_GROUP_TOY",
      "representable": true,
      "growth": "bilinear_enrichment",
      "signature": "maximize_corners"
    },
    {
      "name": "POINTED_SUSPENSION",
      "representable": true,
      "growth": "suspension_extra_base_point",
      "signature": "suspension_shift"
    }
  ]
}
```

### Finite site: objectwise exponentials exist (`presheaf_site_exponential`)

On 3 site objects, 1 have local exp >= Set hom proxy; covers multiply section counts — distinct from global Set coexp.

*Real presheaf site fragment: exp exists per object, not as Set cardinality.*

```json
{
  "site_objects": [
    {
      "object": "U",
      "stalk": 3,
      "exp_size": 27,
      "set_hom": 36,
      "local_exponential": false,
      "cover_product": 4
    },
    {
      "object": "V",
      "stalk": 2,
      "exp_size": 4,
      "set_hom": 25,
      "local_exponential": false,
      "cover_product": 4
    },
    {
      "object": "UV",
      "stalk": 4,
      "exp_size": 256,
      "set_hom": 49,
      "local_exponential": true,
      "cover_product": 6
    }
  ],
  "covers": {
    "U": [
      "UV"
    ],
    "V": [
      "UV"
    ],
    "UV": [
      "U",
      "V"
    ]
  }
}
```

## Stability

### Weighted colimit-limit gap (`colimit_limit_weight_gap`)

Enriched colimit-limit gap up to 3.50 at weights (0.5, 2.0).

*Dual story: colimit (max-plus) vs limit (min-plus) widens under asymmetric enrichment — analog of coproduct vs product tension.*

```json
{
  "sweep": [
    {
      "w0": 0.5,
      "w1": 0.5,
      "colimit": 1.0,
      "limit": 0.5,
      "gap": 0.5
    },
    {
      "w0": 0.5,
      "w1": 1.0,
      "colimit": 2.0,
      "limit": 0.5,
      "gap": 1.5
    },
    {
      "w0": 0.5,
      "w1": 2.0,
      "colimit": 4.0,
      "limit": 0.5,
      "gap": 3.5
    },
    {
      "w0": 1.0,
      "w1": 0.5,
      "colimit": 1.0,
      "limit": 1.0,
      "gap": 0.0
    },
    {
      "w0": 1.0,
      "w1": 1.0,
      "colimit": 2.0,
      "limit": 1.0,
      "gap": 1.0
    },
    {
      "w0": 1.0,
      "w1": 2.0,
      "colimit": 4.0,
      "limit": 1.0,
      "gap": 3.0
    },
    {
      "w0": 2.0,
      "w1": 0.5,
      "colimit": 2.0,
      "limit": 1.0,
      "gap": 1.0
    },
    {
      "w0": 2.0,
      "w1": 1.0,
      "colimit": 2.0,
      "limit": 2.0,
      "gap": 0.0
    },
    {
      "w0": 2.0,
      "w1": 2.0,
      "colimit": 4.0,
      "limit": 2.0,
      "gap": 2.0
    }
  ],
  "max_gap": 3.5
}
```
