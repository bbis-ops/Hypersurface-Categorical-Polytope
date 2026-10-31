/* gitcalculator browser engine, part two: counter-arguments, receipts, and
 * the Design, Sweep and Attack modes. Requires engine.js. */
(function (global) {
  "use strict";
  const G = global.GitCalc;
  const { Q, localize, analyze, curvedReduction, ambientAxes, measure, polyText, monomialText, exps, key, wdeg, combinations } = G;
  const ENGINE_VERSION = "gitcalculator-js.v1";
  const normalize = (r) => {
    const out = {};
    for (const k of ["system", "base", "perturbation", "observed_exponent", "observation_tolerance"]) if (r[k] != null && r[k] !== "") out[k] = r[k];
    if (out.perturbation == null && r.pert != null) out.perturbation = r.pert;
    return out;
  };

  // ===== counter-arguments ===================================================
  const SQUARE = "([[-1,0],[0,-1],[1,0],[0,1]], [0,0,1,1])", SIMPLEX = "([[-1,0],[0,-1],[1,1]], [0,0,1])";
  const PYRAMID = "([[-1,0,0],[0,-1,0],[1,0,0],[0,1,0],[0,0,-1],[1,0,1],[-1,0,1],[0,1,1],[0,-1,1]], [0,0,1,1,0,1,0,1,0])";
  const linkOf = (ctx, id) => (ctx.certificate.links || []).find((l) => l.id === id) || {};
  const faces = (ctx) => ((linkOf(ctx, "faces").values || {}).faces) || [];
  const verdictOf = (ctx, id) => (ctx.measurement.verdicts || []).find((v) => v.id === id) || {};
  const ASSESS = {
    "ambient-axes": (ctx) => {
      const naive = ctx.alternatives.ambient_axes, feasible = ctx.certificate.gamma;
      if (!naive || !naive.gamma || !feasible) return ["clear", "No ambient-axis counterfactual applies to this input."];
      if (naive.gamma === feasible) return ["clear", `The ambient axes give the same exponent γ = ${feasible} here.`];
      const v = verdictOf(ctx, "ambient-axes").verdict;
      const moves = naive.infeasible_directions || [];
      return ["averted", `Ambient axes would give γ = ${naive.gamma}` + (moves.length ? ` (direction ${moves.join(", ")} leaves P)` : "") + `; the feasible chart gives γ = ${feasible}.`
        + (v === "contradicted" ? " Certified lower bounds contradict the ambient answer." : v === "consistent" ? " The measurement does not separate the two exponents." : "")];
    },
    "signed-channel": (ctx) => {
      const h5 = linkOf(ctx, "H5"), vals = h5.values || {};
      if (h5.status === "unresolved") {
        const gain = ctx.measurement.measured_exponent;
        return ["blocks", `Uncontrolled positive terms ${(vals.uncontrolled || []).join(", ")} sit below the selection cutoff, so the license is withheld` + (gain ? `; certified lower bounds grow like s^${gain}.` : ".")];
      }
      if ((vals.absorbed || []).length) return ["averted", `Higher positive terms are absorbed by negative monomials (${vals.absorbed.join("; ")}).`];
      return ["clear", "Every positive monomial is dominated by the base at the selected order."];
    },
    "signed-sharp": (ctx) => {
      if (ctx.certificate.q_star && linkOf(ctx, "H5").status === "unresolved") {
        const v = verdictOf(ctx, "exact-faces").verdict;
        return ["blocks", `A face qualifies with γ = ${ctx.certificate.gamma}, but a signed term below it is uncontrolled; the qualified minimum is not a theorem here.` + (v === "contradicted" ? " Certified lower bounds contradict it." : "")];
      }
      return ["clear", "No qualified minimum rests on an uncontrolled signed layer."];
    },
    "interior-zero": (ctx) => {
      const stuck = faces(ctx).filter((f) => f.status === "unresolved");
      return stuck.length ? ["blocks", `Mixed-sign initial forms without a positive witness: ${stuck.map((f) => `{${f.face.join(", ")}}: ${f.initial_form}`).join("; ")}.`] : ["clear", "Every initial form is decided by its signs or an exact witness."];
    },
    "empty-not-zero": (ctx) => {
      if (ctx.certificate.status === "zero_response") return ["averted", "Lemma 2 certifies Δ(s) = 0 for small s, so here the refusal does mean no response."];
      if (ctx.certificate.q_star) return ["clear", "A response exponent was produced."];
      if (ctx.measurement.positive_gain_found) { const g = ctx.measurement.measured_exponent; return ["caveat", "No face qualifies, yet certified lower bounds are positive" + (g ? ` and scale like s^${g}.` : ".")]; }
      return ["caveat", "No qualified face. That alone proves neither zero response nor a competing law."];
    },
    "active-set": (ctx) => {
      const winners = faces(ctx).filter((f) => f.winning).map((f) => new Set(f.face));
      const minimal = winners.filter((w) => !winners.some((o) => o.size < w.size && [...o].every((a) => w.has(a))));
      if (ctx.certificate.status !== "theorem" || !minimal.length) return ["clear", "No proved leading channel to compare with the optimizer."];
      const leading = new Set(minimal.flatMap((w) => [...w])), support = ctx.measurement.support_at_smallest_s || [];
      const extra = support.filter((a) => !leading.has(a)).sort();
      const channel = minimal.map((w) => `{${[...w].sort().join(", ")}}`).join(" or ");
      return extra.length ? ["caveat", `The leading channel is ${channel}, but the measured optimizer also moves along ${extra.join(", ")}: released constraints describe the leading channel only.`] : ["clear", `The measured optimizer stays on the leading channel ${channel}.`];
    },
    "homogeneity-probe": (ctx) => {
      const h2 = linkOf(ctx, "H2").status;
      if (h2 === "exact") return ["averted", "H2 is verified exactly; no numerical homogeneity probe is relied on."];
      if (h2 === "failed") return ["blocks", "H2 fails exactly, so the theorem as stated does not deliver an exponent here; a numerical homogeneity probe could still admit it. " + (linkOf(ctx, "H2").detail || "")];
      return ["clear", "The principal part was not reached."];
    },
    "isolation-probe": (ctx) => {
      const l = linkOf(ctx, "H0");
      if (l.status === "exact") return ["averted", `H0 is proved: ${l.method}.`];
      if (l.status === "failed") return ["blocks", (l.detail || "") + (ctx.measurement.boundary_dominated ? " The certified lower bounds are attained far from v, at the rival." : "")];
      if (l.status === "unresolved") return ["caveat", "Uniqueness of the base maximizer has no exact certificate here."];
      return ["clear", "H0 was not reached."];
    },
    "critical-layer": (ctx) => {
      const crit = faces(ctx).filter((f) => f.status === "critical");
      return crit.length ? ["caveat", `A degree-one layer competes with the base at equal order on ${crit.map((f) => `{${f.face.join(", ")}}`).join(", ")}; it adds nothing for small s when dominated (Lemma 2).`] : ["clear", "No face sits at the critical degree q = 1."];
    },
    "tied-coefficient": (ctx) => {
      const winners = faces(ctx).filter((f) => f.winning);
      const minimal = winners.filter((f) => !winners.some((g) => g.face.length < f.face.length && g.face.every((a) => f.face.includes(a))));
      const terms = Math.max(0, ...minimal.map((f) => (f.initial_form.match(/ [+-] /g) || []).length + 1));
      return minimal.length > 1 || terms > 1 ? ["caveat", `${minimal.length} minimal winning face(s) tie at q*; every tied term enters the coefficient, while the exponent depends only on q*.`] : ["clear", "One minimal winning face with a one-term initial form."];
    },
    "finite-scale": (ctx) => {
      const rows = (ctx.measurement.verdicts || []).filter((v) => v.coefficient_ratio);
      if (rows.length) return ["caveat", `At the smallest certified scale the lower bound is ${rows[0].coefficient_ratio}× the leading term of '${rows[0].id}'. Asymptotic validity is not an accuracy statement at fixed s.`];
      return ctx.certificate.gamma ? ["caveat", "The law is a limit s → 0; accuracy at a given s needs its own bound."] : ["clear", "No exponent to scale."];
    },
    "inverse-tolerance": (ctx) => {
      const obs = ctx.request.observed_exponent;
      if (obs == null) return ["clear", "No observed exponent was supplied."];
      const tol = ctx.request.observation_tolerance ?? 0.05, qObs = 1 - 1 / Number(obs);
      const match = faces(ctx).filter((f) => f.status === "qualified" && Math.abs(Number(Q.parse(f.degree).toNumber()) - qObs) <= tol);
      const status = match.length ? (new Set(match.map((f) => f.degree)).size === 1 ? "matched" : "ambiguous") : "no_face_match";
      return ["caveat", `Inverse status ${status}: q_obs = 1 − 1/γ_obs = ${qObs.toFixed(4)} is compared with the qualified face degrees within tolerance ${tol}; it does not reconstruct the objective.`];
    },
    "non-simple": (ctx) => (linkOf(ctx, "vertex").status === "failed" ? ["blocks", linkOf(ctx, "vertex").detail] : ["clear", "The selected vertex is simple."]),
  };
  const REGISTRY = [
    ["ambient-axes", "Ambient axes decide the exponent", "Probing F and G along the ambient coordinate axes at v gives the Newton data.", "At the simplex vertex (0,1), the ambient direction (1,0) leaves P and sees quadratic decay, predicting γ = 2. The feasible chart u₀ = (1,−1), u₁ = (0,−1) gives D = c₀⁴ + c₁², R = c₀, and Δ(s) = 3·4^(−4/3)·s^(4/3).", ["README.md#the-decisive-example-feasibility-comes-before-degree", "docs/FORMAL_AMBIENT_FACE_TRANSPORT.md#why-ambient-axes-fail"], { system: SIMPLEX, base: "-((x0+x1-1)**2 + x0**4)", perturbation: "x0" }],
    ["signed-channel", "A non-positive initial form excludes gain", "Former Lemma 2: a face whose first weighted layer is non-positive contributes nothing.", "D₀ = x⁶ + y⁶, R = −x² + xy²: no coordinate face qualifies, yet −x² + xy² = y⁴/4 − (x − y²/2)² opens a curved channel and Δ(s) ~ s³/432.", ["docs/MATHEMATICAL_AUDIT.md#1-an-exact-counterexample-with-a-sharp-constant", "docs/FORMAL_FACE_SELECTION.md#6-upper-control-on-unqualified-faces"], { system: SQUARE, base: "-(x0**6+x1**6)", perturbation: "-x0**2+x0*x1**2" }],
    ["signed-sharp", "A qualified face fixes the exponent despite signed terms below it", "Once some face qualifies, its least degree gives the exponent.", "Adding y⁵ to the signed example qualifies the y face (q = 5/6, γ = 6), but the curved witness gives Δ(s) ≥ c·s³, which no Θ(s⁶) law allows.", ["docs/MATHEMATICAL_AUDIT.md#1-an-exact-counterexample-with-a-sharp-constant"], { system: SQUARE, base: "-(x0**6+x1**6)", perturbation: "-x0**2+x0*x1**2+x1**5" }],
    ["interior-zero", "Negative axis forms rule out gain", "If every coordinate-axis initial form is negative, the perturbation cannot help.", "D₀ = x⁴ + y⁴, R = −(x − y)² + x³: both axis forms are negative and the full form is non-positive, but x = y = 3s/8 gives 27s⁴/2048 > 0.", ["docs/MATHEMATICAL_AUDIT.md#2-why-uniform-remainders-did-not-repair-the-proof"], { system: SQUARE, base: "-(x0**4+x1**4)", perturbation: "-(x0-x1)**2+x0**3" }],
    ["empty-not-zero", "No qualified face means no response", "A refusal for lack of a qualified face shows that the perturbation does not help.", "The signed example is refused by the selector, yet Δ(s) ~ s³/432 > 0. An empty qualified set establishes neither zero response nor a competing law.", ["docs/FORMAL_FACE_SELECTION.md#10-scope", "docs/FACE_SELECTION_BACKEND.md#refused"], { system: SQUARE, base: "-(x0**6+x1**6)", perturbation: "-x0**2+x0*x1**2" }],
    ["active-set", "The winning face is the optimizer's support", "The released constraints of the winning face are exactly the perturbed optimizer's support.", "J = −x⁴ − y⁴ + s(x + y²): the minimal degree 1/4 lies on the x axis, yet x_s = (s/4)^(1/3) and y_s = (s/2)^(1/2) are both positive for every small s.", ["docs/MATHEMATICAL_AUDIT.md#6-exponent-selection-does-not-fix-the-active-set"], { system: SQUARE, base: "-(x0**4+x1**4)", perturbation: "x0+x1**2" }],
    ["homogeneity-probe", "A measured homogeneity near one proves the principal part", "base_homogeneity ≈ 1 establishes Hypothesis 2.", "F = −(x0² + x0·x1 + x1²) on the square: the probe measures homogeneity 1.0, but the cross term x0·x1 has the principal weight, so in_w(D) is not the diagonal D₀ that Hypothesis 2 requires.", ["docs/FORMAL_FACE_SELECTION.md#4-hypotheses-with-uniform-remainders", "docs/PRINCIPLE_DOCUMENTATION_REVIEW.md#substantive-corrections-and-clarifications"], { system: SQUARE, base: "-(x0**2+x0*x1+x1**2)", perturbation: "x0" }],
    ["isolation-probe", "Finding no rival maximizer proves uniqueness", "A finite rival search establishes Hypothesis 0.", "F = −((x0(1 − x0))² + x1²) has two global maximizers, (0,0) and (1,0). The tie breaks the local law: moving to the other maximizer already gains s·(G(w) − G(v)).", ["docs/FORMAL_FACE_SELECTION.md#2-global-isolation"], { system: SQUARE, base: "-((x0*(1-x0))**2 + x1**2)", perturbation: "x0" }],
    ["critical-layer", "Degree-one terms obey the same law", "Every face degree q gives γ = 1/(1 − q).", "D = x0² + x1², R = x0²: q = 1, so γ is undefined; −x0² + s·x0² ≤ 0 for s < 1 and Δ(s) = 0 for small s.", ["docs/FACE_SELECTION_BACKEND.md#term-level-perturbation-classification", "docs/FORMAL_FACE_SELECTION.md#6-upper-control-on-unqualified-faces"], { system: SQUARE, base: "-(x0**2 + x1**2)", perturbation: "x0**2" }],
    ["tied-coefficient", "One tied monomial determines the coefficient", "The winning monomial alone fixes the leading coefficient.", "D = x0⁴ + x1⁴, R = x0 + x1: both axes tie at q = 1/4, and Δ(s) = 2·3·4^(−4/3)·s^(4/3). The exponent depends on q* only; every tied lowest-layer term enters the coefficient.", ["docs/PRINCIPLE_DOCUMENTATION_REVIEW.md#substantive-corrections-and-clarifications"], { system: SQUARE, base: "-(x0**4+x1**4)", perturbation: "x0+x1" }],
    ["finite-scale", "The asymptotic law gives the response at a given s", "Δ(s) ≈ C·s^γ is accurate whenever the exponent is licensed.", "The runbook's finite-scale pair shares the licensed exponent 3, yet one request lies outside a 10% tolerance at its scale: asymptotic validity and finite-scale accuracy are separate decisions.", ["docs/CURVED_FINITE_SCALE.md", "docs/RUNBOOK.md#finite-scale-accuracy-is-a-separate-question"], null],
    ["inverse-tolerance", "Inverse matching identifies the mechanism exactly", "An observed exponent recovers the winning mechanism.", "The inverse block compares q_obs = 1 − 1/γ_obs with the admitted face degrees within an absolute tolerance; it can be ambiguous or unmatched and never reconstructs the objective.", ["docs/FACE_SELECTION_BACKEND.md#forward-and-inverse-power"], null],
    ["non-simple", "The law applies at any vertex", "Face selection works at every maximizing vertex.", "At the apex of a square pyramid four constraints are active in dimension three. The tangent cone is not simplicial, there is no edge chart, and the theorem does not apply.", ["docs/FORMAL_FACE_SELECTION.md#10-scope"], { system: PYRAMID, base: "x2", perturbation: "x0" }],
  ];
  const EFFECT_ORDER = { blocks: 0, caveat: 1, averted: 2, clear: 3 };
  function assess(ctx) {
    return REGISTRY.map(([id, title, claim, refutation, sources]) => {
      let effect, detail;
      try { [effect, detail] = ASSESS[id](ctx); } catch (error) { effect = "caveat"; detail = `assessment failed: ${error.message}`; }
      return { id, title, effect, detail, claim, refutation, sources };
    }).sort((a, b) => EFFECT_ORDER[a.effect] - EFFECT_ORDER[b.effect]);
  }

  // ===== receipts ==============================================================
  const STEP_CHALLENGES = { standing: [], vertex: ["non-simple"], transport: ["ambient-axes"], H0: ["isolation-probe"], H1: [], H2: ["homogeneity-probe"], H3: [], faces: ["interior-zero", "critical-layer", "tied-coefficient"], H5: ["signed-channel", "signed-sharp"], selection: ["empty-not-zero", "active-set", "finite-scale", "inverse-tolerance"] };
  const VERDICTS = {
    proved: "Every hypothesis of the theorem is discharged in exact arithmetic.",
    "proved-v22": "The curved-reduction theorem V.22 applies, with exact checks.",
    unlicensed: "An exponent was computed, but a hypothesis fails or is unresolved.",
    refused: "The input lies outside the law as stated.",
    contradicted: "Certified lower bounds contradict the proved exponent: an internal inconsistency to report.",
  };
  function fnv(text) { let h = 0xcbf29ce484222325n; for (const ch of new TextEncoder().encode(text)) { h ^= BigInt(ch); h = (h * 0x100000001b3n) & 0xffffffffffffffffn; } return h.toString(16).padStart(16, "0"); }
  function minimalFaces(table) {
    const winners = table.filter((e) => e.winning).map((e) => e.edges);
    return winners.filter((f) => !winners.some((g) => g.length < f.length && g.every((i) => f.includes(i)))).sort();
  }
  function newtonData(model, cert) {
    if (!model || !model.gain) return null;
    const w = model.weights;
    return {
      axes: model.axes, weights: w ? w.map(String) : null,
      gain: [...model.gain].map(([k, c]) => ({ exps: exps(k), coefficient: String(c), sign: c.sign(), degree: w ? String(wdeg(exps(k), w)) : null })),
      loss: [...model.loss].map(([k, c]) => ({ exps: exps(k), coefficient: String(c), degree: w ? String(wdeg(exps(k), w)) : null })),
      principal: model.principal ? model.principal.map(([b, a]) => [b, String(a)]) : null,
      q_star: cert.q_star || null, winners: cert._table ? minimalFaces(cert._table) : [],
    };
  }
  function geometryData(local, measurement) {
    const base = local.result.geometry;
    if (!base) return null;
    const model = local.model;
    return Object.assign({}, base, {
      generators: model ? model.generators.map((u) => u.map((x) => x.toNumber())) : [], rho: model ? model.rho.toNumber() : null,
      simple: !!model, path: (measurement.rows || []).filter((r) => r.lower_bound !== "0").map((r) => ({ s: r.s, x: r.witness_x })),
    });
  }
  function solve(request, options = {}) {
    const started = Date.now();
    const inputs = normalize(request);
    const local = localize(inputs);
    const { result: cert } = analyze(local, inputs, null);
    const model = local.model && local.model.gain ? local.model : null;
    const alternatives = {};
    if (model) {
      const cr = curvedReduction(model); if (cr) alternatives.curved_reduction = cr;
      const naive = ambientAxes(model); if (naive) alternatives.ambient_axes = naive;
    }
    const predictions = [];
    if (cert.gamma) predictions.push({ id: "exact-faces", label: cert.status === "theorem" ? "face selection (proved)" : `exact face data (${cert.status})`, gamma: Q.parse(cert.gamma) });
    const curved = alternatives.curved_reduction;
    if (curved && curved.status === "licensed") predictions.push({ id: "curved", label: "V.22 curved reduction", gamma: Q.parse(curved.gamma), coefficient: curved.coefficient_value });
    const naive = alternatives.ambient_axes;
    if (naive && naive.gamma && naive.gamma !== cert.gamma) predictions.push({ id: "ambient-axes", label: "ambient-axis counterfactual", gamma: Q.parse(naive.gamma) });
    const measurement = options.measure === false ? { status: "not_requested", verdicts: [] } : measure(model, predictions, options.budget || "standard");
    measurement.predictions = predictions.map((p) => ({ id: p.id, label: p.label, gamma: String(p.gamma) }));
    const ctx = { request: inputs, certificate: cert, model, measurement, alternatives };
    const counter = assess(ctx);
    const effects = Object.fromEntries(counter.map((c) => [c.id, c]));
    const contradicted = new Set((measurement.verdicts || []).filter((v) => v.verdict === "contradicted").map((v) => v.id));
    let verdict, headline;
    if (cert.status === "theorem" && contradicted.has("exact-faces")) [verdict, headline] = ["contradicted", "Certified lower bounds outgrow the proved exponent; please report this input."];
    else if (cert.status === "theorem" || cert.status === "zero_response") [verdict, headline] = ["proved", cert.conclusion];
    else if (curved && curved.status === "licensed" && !contradicted.has("curved")) [verdict, headline] = ["proved-v22", `Δ(s) ~ ${curved.coefficient}·s^${curved.gamma}`];
    else if (cert.gamma) [verdict, headline] = ["unlicensed", `candidate Δ(s) = Θ(s^${cert.gamma}), not proved`];
    else if (measurement.positive_gain_found && measurement.measured_exponent) [verdict, headline] = ["refused", `no proved exponent; certified bounds grow like s^${measurement.measured_exponent}`];
    else [verdict, headline] = ["refused", cert.reason || "no exponent"];
    const gamma = verdict === "proved-v22" ? curved.gamma : cert.gamma || null;
    const qStar = verdict === "proved-v22" ? null : cert.q_star || null;
    const coefficient = verdict === "proved-v22" ? { exact: curved.coefficient, source: "V.22 exact" } : null;
    const steps = (cert.links || []).slice().sort((a, b) => G.ORDER.indexOf(a.id) - G.ORDER.indexOf(b.id)).map((l) => ({
      id: l.id, clause: l.clause, statement: l.statement, doc: l.doc, backend: null,
      certificate: { status: l.status, method: l.method, detail: l.detail },
      challenges: (STEP_CHALLENGES[l.id] || []).map((id) => ({ id, effect: effects[id].effect })),
    }));
    const certificate = Object.assign({}, cert); delete certificate._table; delete certificate._qStar;
    const signature = { verdict, gamma, q_star: qStar, certificate: { status: cert.status, links: Object.fromEntries((cert.links || []).map((l) => [l.id, l.status])) },
      curved: curved || null, ambient_gamma: naive ? naive.gamma : null,
      measurement: Object.fromEntries((measurement.verdicts || []).map((v) => [v.id, v.verdict])), counter: Object.fromEntries(counter.map((c) => [c.id, c.effect])) };
    const receipt = {
      schema: "gitcalculator.receipt.v1", engine: ENGINE_VERSION, input: inputs,
      answer: { verdict, meaning: VERDICTS[verdict], headline, gamma, q_star: qStar, coefficient, backend_status: "not run (browser engine)", certificate_status: cert.status },
      steps, certificate, alternatives, measurement, counterarguments: counter,
      newton: newtonData(model || local.model, cert), geometry: geometryData(local, measurement),
      provenance: { git: options.git || {}, code_id: "browser engine", calculator_id: options.engineBlob || ENGINE_VERSION, sources: {}, documents: {}, runtime: { engine: "javascript", python: "—" } },
      timings: { total: (Date.now() - started) / 1000 }, signature,
    };
    receipt.id = "gcjs-" + fnv(JSON.stringify({ input: inputs, engine: ENGINE_VERSION, signature }));
    return receipt;
  }
  /* Certificate-only outcome, used by Design, Sweep and Attack. */
  function outcome(local, request, t) {
    const { result } = analyze(local, request, t);
    let verdict = result.status === "theorem" || result.status === "zero_response" ? "proved" : result.gamma ? "unlicensed" : "refused";
    let gamma = result.gamma || null;
    if (verdict !== "proved" && local.model && local.model.gain) {
      const cr = curvedReduction(local.model);
      if (cr && cr.status === "licensed") { verdict = "proved-v22"; gamma = cr.gamma; }
    }
    const winners = result._table ? minimalFaces(result._table).map((f) => `{${f.map((i) => local.model.axes[i]).join(",")}}`).join(" ") : "";
    return { verdict, gamma, q_star: result.q_star || null, status: result.status, winners, open: result.open_links || [], conclusion: result.conclusion };
  }

  // ===== Design: the exponent spectrum of a vertex ============================
  function affineText(row, b, n) {
    // slack = b - a·x, written in x0..x{n-1}
    const terms = [];
    if (!b.isZero()) terms.push([b, null]);
    row.forEach((a, k) => { if (!a.isZero()) terms.push([a.neg(), `x${k}`]); });
    if (!terms.length) return "0";
    return terms.map(([c, v], i) => {
      const mag = c.abs(), sign = c.sign() < 0 ? "-" : "+";
      const body = v ? (mag.eq(Q.ONE) ? v : `${mag}*${v}`) : String(mag);
      return i === 0 ? (sign === "-" ? "-" : "") + body : ` ${sign} ${body}`;
    }).join("");
  }
  function slackPower(slack, power) {
    const simple = /^-?\w+$/.test(slack) && !slack.startsWith("-");
    const base = simple ? slack : `(${slack})`;
    return power === 1 ? base : `${base}**${power}`;
  }
  function slackMonomial(slacks, alpha) {
    const parts = alpha.map((p, i) => (p ? slackPower(slacks[i], p) : null)).filter(Boolean);
    return parts.join("*") || "1";
  }
  function spectrumOf(model, limit = 50000) {
    const betas = model.principal.map(([b]) => b), n = model.n;
    const total = betas.reduce((a, b) => a * b, 1);
    const groups = new Map();
    const alpha = new Array(n).fill(0);
    let count = 0;
    const visit = (i) => {
      if (count > limit) return;
      if (i === n) {
        count++;
        if (alpha.every((a) => a === 0)) return;
        const q = wdeg(alpha, model.weights);
        if (q.ge(Q.ONE)) return;
        const k = String(q);
        if (!groups.has(k)) groups.set(k, { q, alphas: [] });
        groups.get(k).alphas.push(alpha.slice());
        return;
      }
      for (let a = 0; a < betas[i]; a++) { alpha[i] = a; visit(i + 1); }
      alpha[i] = 0;
    };
    visit(0);
    return { groups: [...groups.values()].sort((a, b) => a.q.cmp(b.q)), truncated: total > limit };
  }
  function design(request) {
    const inputs = { system: request.system, base: request.base };
    const local = localize(inputs);
    const links = local.result.links;
    if (!local.model) return { status: "not_applicable", reason: local.result.reason || "no simple base maximizer", links };
    const model = local.model;
    if (!model.weights) return { status: "not_applicable", reason: "the exponent spectrum needs the exact diagonal principal part (Hypothesis 2)", links };
    const slacks = model.active.map((j) => affineText(model.rows[j], model.rhs[j], model.n));
    const { groups, truncated } = spectrumOf(model);
    const baseProved = ["H0", "H1", "H2"].every((id) => (links.find((l) => l.id === id) || {}).status === "exact");
    const spectrum = groups.map((g) => {
      const gamma = Q.ONE.div(Q.ONE.sub(g.q));
      const mechanisms = g.alphas.slice(0, 8).map((alpha) => ({ alpha, monomial: monomialText(alpha, model.axes), perturbation: slackMonomial(slacks, alpha) }));
      return { q: String(g.q), gamma: String(gamma), gamma_value: gamma.toNumber(), mechanism_count: g.alphas.length, mechanisms };
    });
    const out = { status: "complete", base_proved: baseProved, links, vertex: model.vertex.map(String), weights: model.weights.map(String), orders: model.principal.map(([b]) => b),
      slacks: model.axes.map((a, i) => ({ axis: a, constraint: model.active[i], expression: slacks[i] })), spectrum, truncated };
    if (request.target != null && String(request.target).trim() !== "") {
      let gammaT;
      try { gammaT = Q.parse(String(request.target)); } catch { return Object.assign(out, { target: { error: "write the target exponent as a number such as 4/3 or 1.5" } }); }
      if (gammaT.le(Q.ONE)) return Object.assign(out, { target: { gamma: String(gammaT), error: "a fractional response needs γ > 1" } });
      const qT = Q.ONE.sub(Q.ONE.div(gammaT));
      const hit = spectrum.find((e) => Q.parse(e.q).eq(qT));
      const below = [...spectrum].reverse().find((e) => Q.parse(e.gamma).lt(gammaT)), above = spectrum.find((e) => Q.parse(e.gamma).gt(gammaT));
      const target = { gamma: String(gammaT), q: String(qT), achievable: !!hit, nearest_below: below ? below.gamma : null, nearest_above: above ? above.gamma : null };
      if (hit) target.candidates = hit.mechanisms.slice(0, 4).map((m) => Object.assign({}, m, { check: outcome(local, Object.assign({}, inputs, { perturbation: m.perturbation }), null) }));
      out.target = target;
    }
    return out;
  }

  // ===== Sweep: an automatic phase fan ========================================
  function rootsIn(coeffs, lo, hi) {
    // coeffs: Map power -> Q for a polynomial in t. Exact roots for degree <= 2 when rational; bracketed otherwise.
    const deg = Math.max(0, ...coeffs.keys());
    const c = (k) => coeffs.get(k) || Q.ZERO;
    const inRange = (x) => x.ge(lo) && x.le(hi);
    const evalT = (x) => { let v = Q.ZERO; for (const [k, a] of coeffs) v = v.add(a.mul(x.pow(k))); return v; };
    const bracket = (a, b) => { let fa = evalT(a).sign(); for (let i = 0; i < 60; i++) { const m = a.add(b).div(new Q(2n)), fm = evalT(m).sign(); if (fm === 0) return { at: m }; if (fm === fa) { a = m; } else { b = m; } } return { lo: a, hi: b }; };
    if (deg === 0) return [];
    if (deg === 1) { const r = c(0).neg().div(c(1)); return inRange(r) ? [{ at: r }] : []; }
    if (deg === 2) {
      const a = c(2), b = c(1), cc = c(0), disc = b.mul(b).sub(new Q(4n).mul(a).mul(cc));
      if (disc.sign() < 0) return [];
      const sqrtBig = (v) => { if (v < 0n) return null; if (v < 2n) return v; let x = v, y = (x + 1n) / 2n; while (y < x) { x = y; y = (x + v / x) / 2n; } return x; };
      const sn = sqrtBig(disc.n), sd = sqrtBig(disc.d);
      if (sn !== null && sd !== null && sn * sn === disc.n && sd * sd === disc.d) {
        const root = new Q(sn, sd);
        return [b.neg().sub(root), b.neg().add(root)].map((x) => x.div(a.mul(new Q(2n)))).filter(inRange).map((at) => ({ at }));
      }
    }
    const out = [], steps = 256, width = hi.sub(lo).div(new Q(BigInt(steps)));
    let prev = lo, fprev = evalT(lo).sign();
    if (fprev === 0) out.push({ at: lo });
    for (let i = 1; i <= steps; i++) {
      const x = lo.add(width.mul(new Q(BigInt(i)))), fx = evalT(x).sign();
      if (fx === 0) out.push({ at: x });
      else if (fprev !== 0 && fx !== fprev) out.push(bracket(prev, x));
      prev = x; fprev = fx;
    }
    return out;
  }
  function sweep(request) {
    const inputs = { system: request.system, base: request.base };
    const local = localize(inputs);
    if (!local.model) return { status: "not_applicable", reason: local.result.reason || "no simple base maximizer", links: local.result.links };
    const model = local.model;
    if (!model.weights) return { status: "not_applicable", reason: "the phase fan needs the exact diagonal principal part (Hypothesis 2)", links: local.result.links };
    let lo, hi, tree;
    try { lo = Q.parse(String(request.from ?? "-1")); hi = Q.parse(String(request.to ?? "1")); tree = G.parseExpression(request.perturbation, model.n, true); }
    catch (error) { return { status: "not_applicable", reason: error.message }; }
    if (!lo.lt(hi)) return { status: "not_applicable", reason: "the range needs from < to" };
    const P = G.centered(G.transport(tree, model, null, true), model.n);
    const laws = new Map();
    for (const [k, c] of P) { const e = exps(k), ck = key(e.slice(0, model.n)), tp = e[model.n]; if (!laws.has(ck)) laws.set(ck, new Map()); laws.get(ck).set(tp, (laws.get(ck).get(tp) || Q.ZERO).add(c)); }
    const coefficientLaws = [...laws].map(([ck, law]) => ({ monomial: monomialText(exps(ck), model.axes), degree: String(wdeg(exps(ck), model.weights)),
      law: polyText(new Map([...law].map(([p, c]) => [String(p), c])), ["t"]) }));
    const walls = [];
    for (const [ck, law] of laws) for (const r of rootsIn(law, lo, hi)) walls.push(Object.assign({ kind: "coefficient", monomial: monomialText(exps(ck), model.axes) }, r));
    const pos = (w) => (w.at ? w.at : w.lo.add(w.hi).div(new Q(2n)));
    walls.sort((a, b) => pos(a).cmp(pos(b)));
    const unique = walls.filter((w, i) => i === 0 || !pos(w).eq(pos(walls[i - 1])));
    const sig = (o) => `${o.verdict}|${o.gamma}|${o.winners}`;
    const at = (t) => outcome(local, { perturbation: request.perturbation }, t);
    const cuts = [lo, ...unique.map(pos), hi];
    const chambers = [], extra = [];
    for (let i = 0; i < cuts.length - 1; i++) {
      const a = cuts[i], b = cuts[i + 1];
      if (!a.lt(b)) continue;
      const samples = [1n, 2n, 3n].map((k) => a.add(b.sub(a).mul(new Q(k, 4n))));
      const outs = samples.map(at);
      let start = a;
      for (let j = 1; j < samples.length; j++) {
        if (sig(outs[j]) !== sig(outs[j - 1])) {
          let l = samples[j - 1], r = samples[j]; const ls = sig(outs[j - 1]);
          for (let it = 0; it < 48; it++) { const m = l.add(r).div(new Q(2n)); if (sig(at(m)) === ls) l = m; else r = m; }
          extra.push({ kind: "outcome", lo: l, hi: r, monomial: null });
          chambers.push({ from: start, to: l, outcome: outs[j - 1] });
          start = r;
        }
      }
      chambers.push({ from: start, to: b, outcome: outs[outs.length - 1] });
    }
    const allWalls = unique.concat(extra).sort((x, y) => pos(x).cmp(pos(y))).map((w) => ({
      kind: w.kind, monomial: w.monomial, at: w.at ? String(w.at) : null, lo: w.lo ? String(w.lo) : null, hi: w.hi ? String(w.hi) : null,
      value: pos(w).toNumber(), outcome: w.at ? at(w.at) : null,
    }));
    return { status: "complete", range: [String(lo), String(hi)], coefficient_laws: coefficientLaws, walls: allWalls,
      chambers: chambers.map((c) => ({ from: String(c.from), to: String(c.to), from_value: c.from.toNumber(), to_value: c.to.toNumber(), outcome: c.outcome })) };
  }

  // ===== Attack: counterexamples generated for this input ======================
  function decimalText(x) { // exact decimal spelling when one exists
    let d = x.d, twos = 0, fives = 0; while (d % 2n === 0n) { d /= 2n; twos++; } while (d % 5n === 0n) { d /= 5n; fives++; }
    if (d !== 1n) return null;
    const places = Math.max(twos, fives), scaled = x.mul(new Q(10n ** BigInt(places)));
    const s = (scaled.n < 0n ? -scaled.n : scaled.n).toString().padStart(places + 1, "0");
    const body = places ? `${s.slice(0, -places)}.${s.slice(-places)}` : s;
    return (x.sign() < 0 ? "-" : "") + body;
  }
  function attack(request, options = {}) {
    const inputs = normalize(request);
    const local = localize(inputs);
    if (!local.model) return { status: "not_applicable", reason: local.result.reason || "no simple base maximizer", links: local.result.links };
    const model = local.model;
    const base = outcome(local, inputs, null);
    const eps = "1/100";
    const slacks = model.active.map((j) => affineText(model.rows[j], model.rhs[j], model.n));
    const mutations = [];
    const add = (kind, description, mutated, expectation) => mutations.push({ kind, description, input: Object.assign({}, inputs, mutated), expectation });
    add("control", "Double the perturbation: rescaling should not change the class.", { perturbation: `2*(${inputs.perturbation})` }, "unchanged");
    if (model.weights) {
      const { groups } = spectrumOf(model, 4000);
      const qStar = base.q_star ? Q.parse(base.q_star) : Q.ONE;
      const lower = groups.filter((g) => g.q.lt(qStar));
      for (const g of lower.slice(0, 4)) {
        const alpha = g.alphas[0], mono = slackMonomial(slacks, alpha);
        add("intrusion", `Add +${eps}·${monomialText(alpha, model.axes)} (degree ${g.q} below the current cutoff ${qStar}).`, { perturbation: `(${inputs.perturbation}) + ${eps}*${mono}` }, "γ drops");
        add("suppression", `Add −${eps}·${monomialText(alpha, model.axes)}: a negative layer below the winner.`, { perturbation: `(${inputs.perturbation}) - ${eps}*${mono}` }, "may disqualify");
      }
      const { result } = analyze(local, inputs, null);
      const winning = (result._table || []).filter((e) => e.winning && e.edges.length === Math.min(...result._table.filter((x) => x.winning).map((x) => x.edges.length)));
      const flipped = new Set();
      for (const face of winning) for (const [k, c] of face._initial || []) {
        if (flipped.has(k)) continue; flipped.add(k);
        const alpha = exps(k), mono = slackMonomial(slacks, alpha), twice = c.mul(new Q(2n));
        add("sign flip", `Flip the sign of the winning term ${c}·${monomialText(alpha, model.axes)}.`, { perturbation: `(${inputs.perturbation}) - (${twice})*${mono}` }, "winner lost");
        if (flipped.size >= 3) break;
      }
      for (const [i, j] of combinations(model.n, 2)) {
        if (wdeg(model.axes.map((_, k) => (k === i || k === j ? 1 : 0)), model.weights).le(Q.ONE)) {
          const cross = `${slackPower(slacks[i], 1)}*${slackPower(slacks[j], 1)}`;
          add("base cross term", `Add ${eps}·${model.axes[i]}·${model.axes[j]} to the base loss: a cross term at or below the principal weight.`, { base: `(${inputs.base}) - ${eps}*${cross}` }, "H2 fails");
        }
      }
    }
    model.active.forEach((j) => {
      for (let k = 0; k < model.n; k++) {
        const row = model.rows[j].map((a, c) => (c === k ? a.add(new Q(1n, 100n)) : a)), rhs = model.rhs[j].add(new Q(1n, 100n).mul(model.vertex[k]));
        const rowText = row.map(decimalText), rhsText = decimalText(rhs);
        if (rowText.some((x) => x === null) || rhsText === null) continue;
        const rows = model.rows.map((r, jj) => (jj === j ? rowText : r.map(decimalText))), rhsAll = model.rhs.map((b, jj) => (jj === j ? rhsText : decimalText(b)));
        if (rows.flat().some((x) => x === null) || rhsAll.some((x) => x === null)) continue;
        add("facet tilt", `Tilt facet ${j} about v (coefficient of x${k} + 0.01): the edges move, the vertex stays.`, { system: `([${rows.map((r) => `[${r.join(",")}]`).join(",")}], [${rhsAll.join(",")}])` }, "portability");
      }
    });
    const limit = options.limit || 24;
    const results = mutations.slice(0, limit).map((m) => {
      let out;
      try { const l = m.input.system === inputs.system && m.input.base === inputs.base ? local : localize(m.input); out = l.model ? outcome(l, m.input, null) : { verdict: "refused", gamma: null, winners: "", status: l.result.status, conclusion: l.result.reason }; }
      catch (error) { out = { verdict: "refused", gamma: null, winners: "", status: "error", conclusion: error.message }; }
      const changed = out.verdict !== base.verdict || out.gamma !== base.gamma;
      return Object.assign(m, { outcome: out, changed });
    });
    const fragile = results.filter((r) => r.changed), stable = results.filter((r) => !r.changed);
    return { status: "complete", base, mutations: results, summary: { total: results.length, changed: fragile.length, unchanged: stable.length,
      kinds_changed: [...new Set(fragile.map((r) => r.kind))], kinds_stable: [...new Set(stable.map((r) => r.kind))].filter((k) => !fragile.some((r) => r.kind === k)) } };
  }

  // ===== proof sheets: a receipt as GitHub Markdown, as gitcalculator/sheet.py writes it =====
  const SHEET_VERDICTS = { proved: "proved", "proved-v22": "proved by V.22", licensed: "licensed", unlicensed: "not licensed", refused: "refused", contradicted: "contradicted" };
  const GITHUB_RE = /^(?:https:\/\/github\.com\/|git@github\.com:)([^/\s]+)\/([^/\s]+?)(?:\.git)?\/?$/;
  const filled = (o) => Boolean(o) && Object.keys(o).length > 0;
  const mdText = (v) => String(v).split(/\s+/).filter(Boolean).join(" ").replace(/([\\`*_<>|$~])/g, "\\$1");
  function mdCode(v) {
    const body = String(v).replace(/\|/g, "\\|"), runs = body.match(/`+/g) || [];
    const fence = "`".repeat(Math.max(0, ...runs.map((r) => r.length)) + 1), pad = body.startsWith("`") || body.endsWith("`") ? " " : "";
    return fence + pad + body + pad + fence;
  }
  function tex(v) {
    let body = String(v).trim(), sign = "";
    if (body.startsWith("-")) { sign = "-"; body = body.slice(1); }
    const i = body.indexOf("/");
    return i < 0 ? sign + body : `${sign}\\tfrac{${body.slice(0, i)}}{${body.slice(i + 1)}}`;
  }
  const shellQuote = (v) => "'" + String(v).replace(/'/g, "'\\''") + "'";
  function githubRepository(remote) { const m = GITHUB_RE.exec(remote || ""); return m ? `https://github.com/${m[1]}/${m[2]}` : null; }
  function pagesUrl(repository) { const m = GITHUB_RE.exec(repository || ""); return m ? `https://${m[1].toLowerCase()}.github.io/${m[2]}/` : null; }
  function formula(answer) {
    const gamma = answer.gamma, q = answer.q_star, coefficient = (answer.coefficient || {}).exact;
    if (answer.certificate_status === "zero_response") return "\\Delta(s) = 0 \\quad \\text{for all sufficiently small } s \\gt 0";
    if (answer.verdict === "proved-v22" && gamma) return `\\Delta(s) \\sim ${coefficient ? tex(coefficient) : "C"}\\, s^{${gamma}}`;
    if (gamma && q) return `\\Delta(s) = \\Theta\\big(s^{\\gamma}\\big), \\quad \\gamma = \\frac{1}{1 - q^\\ast} = \\frac{1}{1 - ${tex(q)}} = ${tex(gamma)}`;
    return null;
  }
  function calculationPairs(request) {
    const pairs = ["system", "base", "perturbation"].filter((k) => request[k]).map((k) => [k, String(request[k])]);
    if (request.observed_exponent != null) pairs.push(["observed", String(request.observed_exponent)]);
    return pairs;
  }
  const SHEET_FLAGS = { system: "--system", base: "--base", perturbation: "--perturbation", observed: "--observed" };
  const sheetCommand = (request) => "python -m gitcalculator calc " + calculationPairs(request).map(([k, v]) => `${SHEET_FLAGS[k]} ${shellQuote(v)}`).join(" ");
  const sheetLink = (request, calculator) => `${calculator}?${new URLSearchParams(calculationPairs(request))}#solve`;
  function sheet(receipt, options = {}) {
    const answer = receipt.answer, request = receipt.input, git = (receipt.provenance || {}).git || {};
    const repository = options.repository || githubRepository(git.remote), ref = options.ref || git.commit;
    const calculator = options.calculator || pagesUrl(repository), files = options.linkable == null ? null : new Set(options.linkable);
    const doc = (label, path) => {
      const i = path.indexOf("#"), file = i < 0 ? path : path.slice(0, i), anchor = i < 0 ? "" : path.slice(i + 1);
      if (!repository || !ref || (files && !files.has(file))) return mdText(label);
      return `[${mdText(label).replace(/\[/g, "(").replace(/\]/g, ")")}](${repository}/blob/${ref}/${file}${anchor ? "#" + anchor : ""})`;
    };
    const out = [`### ${mdText(answer.headline)} · ${SHEET_VERDICTS[answer.verdict] || mdText(answer.verdict)}`, ""];
    const math = formula(answer);
    if (math != null) out.push("```math", math, "```", "");
    out.push(mdText(answer.meaning), "");

    out.push("| Input | |", "| :--- | :--- |", `| Polyhedron $Ax \\le b$ | ${mdCode(request.system)} |`,
      `| Base objective $F$ | ${mdCode(request.base)} |`, `| Perturbation $G$ | ${mdCode(request.perturbation)} |`);
    if (request.observed_exponent != null) out.push(`| Observed exponent | ${mdCode(String(request.observed_exponent))} |`);
    out.push("");

    const certificate = receipt.certificate || {};
    out.push(`#### Exact certificate: ${mdText(String(certificate.status ?? "—").replace(/_/g, " "))}`, "", "| Clause | Status | What was checked |", "| :--- | :--- | :--- |");
    for (const l of certificate.links || []) out.push(`| ${doc(l.clause, l.doc)} | ${mdText(l.status.replace(/_/g, " "))} | ${mdText(l.detail || "")} |`);
    out.push("");

    const alternatives = receipt.alternatives || {}, curved = alternatives.curved_reduction, ambient = alternatives.ambient_axes, rows = [];
    if (filled(curved)) {
      const found = curved.status === "licensed"
        ? `licensed: $\\gamma = ${tex(curved.gamma)}$` + (curved.coefficient ? `, $C = ${tex(curved.coefficient)}$` : "")
        : mdText(String(curved.status ?? "").replace(/_/g, " ")) + ((curved.blockers || []).length ? `: ${mdText(curved.blockers[0])}` : "");
      rows.push(`| V.22 curved reduction | ${found} |`);
    }
    if (filled(ambient)) rows.push(`| Ambient axes, ignoring the edge chart | ${ambient.gamma ? `$\\gamma = ${tex(ambient.gamma)}$` : "no exponent"} |`);
    if (rows.length) out.push("#### Alternatives", "", "| Reading | Result |", "| :--- | :--- |", ...rows, "");

    const measurement = receipt.measurement || {}, verdicts = measurement.verdicts || [];
    if (measurement.status === "complete" && (verdicts.length || measurement.measured_exponent != null)) {
      const exponent = measurement.measured_exponent, scales = measurement.series_length ?? (measurement.rows || []).length;
      out.push("#### Measurement", "", `Certified lower bounds $\\Delta(s) \\ge L(s)$ at ${scales} scales, each witnessed by a point of $P$ checked in exact arithmetic`
        + (exponent != null ? `; measured exponent ${mdText(String(exponent))}.` : "."), "");
      if (verdicts.length) {
        out.push("| Prediction | $\\gamma$ | Verdict |", "| :--- | :--- | :--- |");
        for (const v of verdicts) out.push(`| ${mdText(v.label)} | ${v.gamma ? `$${tex(v.gamma)}$` : "—"} | ${mdText(v.verdict)} |`);
        out.push("");
      }
    }

    const counters = receipt.counterarguments || [], bearing = counters.filter((c) => c.effect !== "clear");
    if (counters.length) {
      out.push("#### Counter-arguments", "");
      if (bearing.length) {
        out.push("| Counter-argument | Effect | Here |", "| :--- | :--- | :--- |");
        for (const c of bearing) out.push(`| ${mdText(c.title)} | ${mdText(c.effect)} | ${mdText(c.detail || "")} |`);
        out.push("");
      }
      const clear = counters.length - bearing.length;
      if (clear) out.push(`${clear} other counter-argument${clear !== 1 ? "s" : ""} do${clear === 1 ? "es" : ""} not apply to this input.`, "");
    }

    const provenance = receipt.provenance || {};
    const engine = receipt.engine ? `exact JS engine ${mdCode(receipt.engine)}` : `Python ${mdCode(provenance.code_id || "—")} · ${mdCode(provenance.calculator_id || "—")}`;
    const commit = git.commit, short = git.short || (commit ? commit.slice(0, 7) : "—");
    const pinned = repository && commit && ref === commit ? `[${mdCode(short)}](${repository}/commit/${commit})` : mdCode(short);
    out.push(`<sub>Receipt ${mdCode(receipt.id || "—")} · ${engine} · commit ${pinned}</sub>`, "");
    out.push(calculator ? `[Open this calculation in the gitcalculator](${sheetLink(request, calculator)}). Reproduce it:` : "Reproduce it:", "");
    out.push("```bash", sheetCommand(request), "```", "");
    return out.join("\n");
  }

  Object.assign(G, { ENGINE_VERSION, normalize, assess, REGISTRY, solve, outcome, design, sweep, attack, spectrumOf, affineText, slackMonomial, decimalText, sheet, sheetLink, sheetCommand, githubRepository, pagesUrl });
})(typeof globalThis !== "undefined" ? globalThis : this);
