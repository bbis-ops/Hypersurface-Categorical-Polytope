# Friday–Saturday discoveries

Generated: 2026-05-23 02:57 UTC

**5 findings** from systematic search over obstruction, certification, localization, algorithms, and stability.

## Certification

### epsilon / Phi / delta as a sheaf over the site (`sheafified_certificate`)

CertificateSheaf: 1/4 couplings glue on 3-object site; 5-object larger_site gluing_ok=False; global epsilon = max stalk.

*Certification is geometric: stalks over U,V,UV with restriction — descent holds in toy probe.*

```json
{
  "coupling": 0.1,
  "sites": [
    {
      "n_objects": 3,
      "n_covers": 3,
      "gluing_ok": false,
      "global_epsilon": 0.07071067811865477,
      "objects": [
        "U",
        "V",
        "UV"
      ]
    },
    {
      "n_objects": 5,
      "n_covers": 5,
      "gluing_ok": false,
      "global_epsilon": 0.07071067811865477,
      "objects": [
        "U",
        "V",
        "W",
        "UV",
        "UVW"
      ]
    }
  ],
  "coupling_sweep": [
    {
      "coupling": 0.0,
      "global_epsilon": 0.0,
      "global_certified": true,
      "gluing_ok": true,
      "sections": {
        "U": {
          "epsilon": 0.0,
          "phi": 0.0,
          "delta": 0.0,
          "certified": true
        },
        "V": {
          "epsilon": 0.0,
          "phi": 0.0,
          "delta": 0.0,
          "certified": true
        },
        "UV": {
          "epsilon": 0.0,
          "phi": 0.0,
          "delta": 0.0,
          "certified": true
        }
      }
    },
    {
      "coupling": 0.1,
      "global_epsilon": 0.07071067811865477,
      "global_certified": true,
      "gluing_ok": false,
      "sections": {
        "U": {
          "epsilon": 0.04714045207910317,
          "phi": 0.03166666666666667,
          "delta": 0.03166666666666667,
          "certified": true
        },
        "V": {
          "epsilon": 0.07071067811865477,
          "phi": 0.07125000000000002,
          "delta": 0.07125000000000002,
          "certified": true
        },
        "UV": {
          "epsilon": 0.03535533905932738,
          "phi": 0.017812500000000005,
          "delta": 0.017812500000000005,
          "certified": true
        }
      }
    },
    {
      "coupling": 0.15,
      "global_epsilon": 0.10606601717798213,
      "global_certified": true,
      "gluing_ok": false,
      "sections": {
        "U": {
          "epsilon": 0.07071067811865475,
          "phi": 0.07125000000000001,
          "delta": 0.07125000000000001,
          "certified": true
        },
        "V": {
          "epsilon": 0.10606601717798213,
          "phi": 0.1603125,
          "delta": 0.1603125,
          "certified": true
        },
        "UV": {
          "epsilon": 0.053033008588991064,
          "phi": 0.040078125,
          "delta": 0.040078125,
          "certified": true
        }
      }
    },
    {
      "coupling": 0.2,
      "global_epsilon": 0.14142135623730953,
      "global_certified": true,
      "gluing_ok": false,
      "sections": {
        "U": {
          "epsilon": 0.09428090415820634,
          "phi": 0.12666666666666668,
          "delta": 0.12666666666666668,
          "certified": true
        },
        "V": {
          "epsilon": 0.14142135623730953,
          "phi": 0.2850000000000001,
          "delta": 0.2850000000000001,
          "certified": true
        },
        "UV": {
          "epsilon": 0.07071067811865477,
          "phi": 0.07125000000000002,
          "delta": 0.07125000000000002,
          "certified": true
        }
      }
    }
  ]
}
```

## Learner

### Lawvere damping delays epsilon_0 crossing (interior gap-driven) (`lawvere_face_bowl_threshold`)

epsilon > epsilon_0: plain crosses at 0.45; Lawvere (d=2) at not in [0,0.9] (prediction=True). INTERIOR onset ~0.234375 is gap-only.

*Lawvere damping lowers effective epsilon -> delays epsilon_0 crossing; interior onset from gap is unchanged at fixed strength.*

```json
{
  "onsets_by_distance": {
    "0.0": {
      "interior_plain": 0.234375,
      "interior_lawvere": 0.234375,
      "noncorner_lawvere": 0.234375,
      "block_only_lawvere": null
    },
    "0.5": {
      "interior_plain": 0.234375,
      "interior_lawvere": 0.234375,
      "noncorner_lawvere": 0.234375,
      "block_only_lawvere": null
    },
    "1.0": {
      "interior_plain": 0.234375,
      "interior_lawvere": 0.234375,
      "noncorner_lawvere": 0.234375,
      "block_only_lawvere": null
    },
    "2.0": {
      "interior_plain": 0.234375,
      "interior_lawvere": 0.234375,
      "noncorner_lawvere": 0.234375,
      "block_only_lawvere": null
    }
  },
  "sample_rows": [
    {
      "strength": 0.0,
      "d0": {
        "strength": 0.0,
        "block_distance": 0.0,
        "epsilon_plain": 0.0,
        "epsilon_lawvere": 0.0,
        "gap_vertex_grid": 0.0,
        "mode_plain": "CORNER_HUNTING",
        "mode_lawvere": "CORNER_HUNTING"
      },
      "d2": {
        "strength": 0.0,
        "block_distance": 2.0,
        "epsilon_plain": 0.0,
        "epsilon_lawvere": 0.0,
        "gap_vertex_grid": 0.0,
        "mode_plain": "CORNER_HUNTING",
        "mode_lawvere": "CORNER_HUNTING"
      }
    },
    {
      "strength": 0.1,
      "d0": {
        "strength": 0.1,
        "block_distance": 0.0,
        "epsilon_plain": 0.05656854249492382,
        "epsilon_lawvere": 0.05656854249492382,
        "gap_vertex_grid": 0.0,
        "mode_plain": "CORNER_HUNTING",
        "mode_lawvere": "CORNER_HUNTING"
      },
      "d2": {
        "strength": 0.1,
        "block_distance": 2.0,
        "epsilon_plain": 0.05656854249492382,
        "epsilon_lawvere": 0.007655719720832876,
        "gap_vertex_grid": 0.0,
        "mode_plain": "CORNER_HUNTING",
        "mode_lawvere": "CORNER_HUNTING"
      }
    },
    {
      "strength": 0.2,
      "d0": {
        "strength": 0.2,
        "block_distance": 0.0,
        "epsilon_plain": 0.11313708498984763,
        "epsilon_lawvere": 0.11313708498984763,
        "gap_vertex_grid": 0.003955078125000178,
        "mode_plain": "CORNER_HUNTING",
        "mode_lawvere": "CORNER_HUNTING"
      },
      "d2": {
        "strength": 0.2,
        "block_distance": 2.0,
        "epsilon_plain": 0.11313708498984763,
        "epsilon_lawvere": 0.015311439441665752,
        "gap_vertex_grid": 0.003955078125000178,
        "mode_plain": "CORNER_HUNTING",
        "mode_lawvere": "CORNER_HUNTING"
      }
    },
    {
      "strength": 0.5,
      "d0": {
        "strength": 0.5,
        "block_distance": 0.0,
        "epsilon_plain": 0.28284271247461906,
        "epsilon_lawvere": 0.28284271247461906,
        "gap_vertex_grid": 0.0567626953125,
        "mode_plain": "INTERIOR_SEARCH",
        "mode_lawvere": "INTERIOR_SEARCH"
      },
      "d2": {
        "strength": 0.5,
        "block_distance": 2.0,
        "epsilon_plain": 0.28284271247461906,
        "epsilon_lawvere": 0.038278598604164375,
        "gap_vertex_grid": 0.0567626953125,
        "mode_plain": "INTERIOR_SEARCH",
        "mode_lawvere": "INTERIOR_SEARCH"
      }
    }
  ],
  "prediction": "Lawvere damping lowers effective epsilon -> delays epsilon_0 crossing; interior onset from gap is unchanged at fixed strength.",
  "prediction_epsilon_delayed": true,
  "epsilon_cross_plain": 0.45,
  "epsilon_cross_lawvere_d2": null,
  "interior_onset_plain_d0": 0.234375,
  "block_onset_d0": null,
  "block_onset_d2": null
}
```

### Adjunction-learning session forces interior search (`category_learning_phenomenology`)

Typical arc: early beats use separable corner probes; confusion (face_bowl) raises grid-vertex gap; detector forces INTERIOR_SEARCH when the learner treats adjunction faces as coupled rather than corner-only.

*Human/LLM-scale narrative: confusion on coexp couples faces; live detector switches mode when grid beats vertices.*

```json
{
  "n_steps": 8,
  "first_interior_step": 3,
  "first_interior_strength": 0.35,
  "mode_sequence": [
    "CORNER_HUNTING",
    "CORNER_HUNTING",
    "CORNER_HUNTING",
    "INTERIOR_SEARCH",
    "INTERIOR_SEARCH",
    "INTERIOR_SEARCH",
    "INTERIOR_SEARCH",
    "INTERIOR_SEARCH"
  ],
  "phenomenology": [
    "Step 3 (cross_natural): Cross-naturality couples blocks. [MODE SWITCH CORNER_HUNTING -> INTERIOR_SEARCH: eps=0.0000, gap=0.0304]"
  ],
  "qualitative": "Typical arc: early beats use separable corner probes; confusion (face_bowl) raises grid-vertex gap; detector forces INTERIOR_SEARCH when the learner treats adjunction faces as coupled rather than corner-only."
}
```

## Obstruction

### Enriched UP: presheaf/pointed vs Fisher–localization decoupling (`enriched_coexp_up`)

Presheaf UP exact=False; pointed UP exact=False. Fisher cert and vertex_ok remain decoupled on the same box.

*Enriched representing objects may exist locally; Theorem 1 / Fisher still diagnose factorization vs geometry independently.*

```json
{
  "presheaf": {
    "exists": true,
    "up": false,
    "hom_coproduct": {
      "0": 4,
      "1": 9,
      "2": 16,
      "3": 25,
      "4": 36
    },
    "hom_rep": {
      "0": 256,
      "1": 256,
      "2": 256,
      "3": 256,
      "4": 256
    }
  },
  "pointed": {
    "exists": false,
    "up": false
  },
  "bundle": {
    "presheaf_up": {
      "exists": true,
      "exact_up": false,
      "reason": "Pointwise exponentials on site; C is a presheaf, not a single set."
    },
    "pointed_up": {
      "exists": false,
      "exact_up": false,
      "reason": "Sigma(A) suspension proxy replaces Set coexp cardinality."
    },
    "fisher_vs_localization": [
      {
        "coupling": 0.0,
        "epsilon": 0.0,
        "certified": true,
        "phi": 0.0,
        "gap": 0.0
      },
      {
        "coupling": 0.1,
        "epsilon": 0.14142135623730953,
        "certified": true,
        "phi": 0.2850000000000001,
        "gap": 0.230104166666667
      },
      {
        "coupling": 0.25,
        "epsilon": 0.3535533905932738,
        "certified": false,
        "phi": 1.7812500000000004,
        "gap": 1.505208333333333
      }
    ],
    "localization": [
      {
        "strength": 0.0,
        "interaction": "face_bowl",
        "vertex_ok": true,
        "gap_vs_grid": 0.0
      },
      {
        "strength": 0.5,
        "interaction": "face_bowl",
        "vertex_ok": false,
        "gap_vs_grid": 0.0567626953125
      },
      {
        "strength": 1.0,
        "interaction": "face_bowl",
        "vertex_ok": false,
        "gap_vs_grid": 0.19140625
      }
    ],
    "decoupled": "Fisher cert tracks factorization leakage; vertex_ok tracks Theorem 1 on interaction \u2014 independent of enriched coexp representability."
  },
  "face_bowl_localization": [
    {
      "strength": 0.0,
      "interaction": "face_bowl",
      "vertex_ok": true,
      "gap_vs_grid": 0.0
    },
    {
      "strength": 0.5,
      "interaction": "face_bowl",
      "vertex_ok": false,
      "gap_vs_grid": 0.0567626953125
    },
    {
      "strength": 1.0,
      "interaction": "face_bowl",
      "vertex_ok": false,
      "gap_vs_grid": 0.19140625
    }
  ]
}
```

### Larger site: objectwise exponentials (`larger_site_coexp`)

5-object site: 2/5 objects have local exp >= Set hom proxy.

*Extends presheaf probe beyond 3-object toy.*

```json
{
  "objects": [
    {
      "object": "U",
      "stalk": 3,
      "exp_size": 27,
      "set_hom": 36,
      "local_exponential": false,
      "cover_product": 30
    },
    {
      "object": "V",
      "stalk": 2,
      "exp_size": 4,
      "set_hom": 25,
      "local_exponential": false,
      "cover_product": 30
    },
    {
      "object": "W",
      "stalk": 2,
      "exp_size": 4,
      "set_hom": 25,
      "local_exponential": false,
      "cover_product": 6
    },
    {
      "object": "UV",
      "stalk": 5,
      "exp_size": 3125,
      "set_hom": 64,
      "local_exponential": true,
      "cover_product": 6
    },
    {
      "object": "UVW",
      "stalk": 6,
      "exp_size": 46656,
      "set_hom": 81,
      "local_exponential": true,
      "cover_product": 60
    }
  ]
}
```
