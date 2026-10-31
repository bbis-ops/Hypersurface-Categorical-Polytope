/* gitcalculator browser engine.
 *
 * An independent, exact implementation of the face-selection calculator in
 * JavaScript, so the calculator runs anywhere a page does. It mirrors
 * gitcalculator/certify.py, measure.py and counter.py, and the repository's
 * V.22 reduction, using BigInt rationals throughout. It does not run the
 * Python backend's numerical predictor; where the Python receipt reports
 * backend evidence, this engine reports its own exact evidence instead.
 * tests/test_gitcalculator.py checks it against the Python implementation.
 */
(function (global) {
  "use strict";

  // ===== exact rationals ======================================================
  function gcd(a, b) { if (a < 0n) a = -a; if (b < 0n) b = -b; while (b) { const r = a % b; a = b; b = r; } return a; }
  class Q {
    constructor(n, d = 1n) {
      if (d === 0n) throw new RangeError("division by zero");
      if (d < 0n) { n = -n; d = -d; }
      const g = gcd(n, d) || 1n;
      this.n = n / g; this.d = d / g;
    }
    static of(v) {
      if (v instanceof Q) return v;
      if (typeof v === "bigint") return new Q(v);
      if (typeof v === "number") { if (!Number.isFinite(v)) throw new RangeError("numbers must be finite"); return Q.parse(String(v)); }
      return Q.parse(String(v));
    }
    static parse(text) {
      const s = String(text).trim();
      const frac = s.match(/^([+-]?\d+)\s*\/\s*(\d+)$/);
      if (frac) return new Q(BigInt(frac[1]), BigInt(frac[2]));
      const m = s.match(/^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/);
      if (!m || (m[2] === "" && (m[3] === undefined || m[3] === ""))) throw new SyntaxError(`not a number: ${s}`);
      const digits = (m[2] || "0") + (m[3] || "");
      let exp = (m[4] ? parseInt(m[4], 10) : 0) - (m[3] || "").length;
      let n = BigInt(digits), d = 1n;
      if (exp >= 0) n *= 10n ** BigInt(exp); else d = 10n ** BigInt(-exp);
      return new Q(m[1] === "-" ? -n : n, d);
    }
    add(o) { return new Q(this.n * o.d + o.n * this.d, this.d * o.d); }
    sub(o) { return new Q(this.n * o.d - o.n * this.d, this.d * o.d); }
    mul(o) { return new Q(this.n * o.n, this.d * o.d); }
    div(o) { if (o.n === 0n) throw new RangeError("division by zero"); return new Q(this.n * o.d, this.d * o.n); }
    neg() { return new Q(-this.n, this.d); }
    abs() { return this.n < 0n ? this.neg() : this; }
    pow(k) {
      if (k < 0) return Q.ONE.div(this.pow(-k));
      return new Q(this.n ** BigInt(k), this.d ** BigInt(k));
    }
    cmp(o) { const l = this.n * o.d, r = o.n * this.d; return l < r ? -1 : l > r ? 1 : 0; }
    eq(o) { return this.n === o.n && this.d === o.d; }
    lt(o) { return this.cmp(o) < 0; } le(o) { return this.cmp(o) <= 0; }
    gt(o) { return this.cmp(o) > 0; } ge(o) { return this.cmp(o) >= 0; }
    sign() { return this.n > 0n ? 1 : this.n < 0n ? -1 : 0; }
    isZero() { return this.n === 0n; }
    isInt() { return this.d === 1n; }
    floor() { const q = this.n / this.d; return (this.n < 0n && q * this.d !== this.n) ? q - 1n : q; }
    toString() { return this.d === 1n ? String(this.n) : `${this.n}/${this.d}`; }
    toNumber() {
      if (this.n === 0n) return 0;
      const neg = this.n < 0n, n = neg ? -this.n : this.n;
      // Small terms: one correctly rounded division.
      if (n <= 9007199254740991n && this.d <= 9007199254740991n) return Number(this.n) / Number(this.d);
      const k = 17 - (n.toString().length - this.d.toString().length);
      const scaled = k >= 0 ? (n * 10n ** BigInt(k)) / this.d : n / (this.d * 10n ** BigInt(-k));
      const v = k >= 0 ? Number(scaled) / Math.pow(10, k) : Number(scaled) * Math.pow(10, -k);
      return neg ? -v : v;
    }
  }
  Q.ZERO = new Q(0n); Q.ONE = new Q(1n); Q.MINUS_ONE = new Q(-1n);
  const label = (x) => (x == null ? null : x.toString());

  function log10Q(x) {
    const part = (b) => { const s = b.toString(); return Math.log10(Number(s.slice(0, 17))) + Math.max(0, s.length - 17); };
    return part(x.n < 0n ? -x.n : x.n) - part(x.d);
  }
  function floorDecimal(x, digits = 12) {
    if (x.sign() <= 0) return "0";
    const ten = (k) => (k >= 0 ? new Q(10n ** BigInt(k)) : new Q(1n, 10n ** BigInt(-k)));
    let e = x.n.toString().length - x.d.toString().length;
    while (ten(e).gt(x)) e--;
    while (ten(e + 1).le(x)) e++;
    const m = x.mul(ten(digits - 1 - e)).floor().toString();
    return `${m[0]}.${m.slice(1)}e${e >= 0 ? "+" : ""}${e}`;
  }

  // ===== expressions ==========================================================
  const FUNCTIONS = new Set(["sin", "cos", "exp", "log", "sqrt", "abs", "tanh", "atan"]);
  class NonPolynomial extends Error {}
  function parseExpression(text, dimension, allowParameter = false) {
    if (typeof text !== "string" || !text.trim()) throw new SyntaxError("expression must be a non-empty string");
    if (text.length > 20000) throw new SyntaxError("expression exceeds 20000 characters");
    const tokens = [];
    const re = /\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z_][A-Za-z_0-9]*)|(\*\*|[-+*/^(),]))/y;
    let pos = 0;
    while (pos < text.length) {
      if (/^\s*$/.test(text.slice(pos))) break;
      re.lastIndex = pos;
      const m = re.exec(text);
      if (!m) throw new SyntaxError(`cannot read the expression near "${text.slice(pos, pos + 12)}"`);
      pos = re.lastIndex;
      tokens.push(m[1] !== undefined ? { t: "num", v: m[1] } : m[2] !== undefined ? { t: "name", v: m[2] } : { t: "op", v: m[3] === "^" ? "**" : m[3] });
    }
    let i = 0;
    const peek = () => tokens[i], take = () => tokens[i++];
    const expect = (v) => { const tok = take(); if (!tok || tok.v !== v) throw new SyntaxError(`expected "${v}"`); };
    function atom() {
      const tok = take();
      if (!tok) throw new SyntaxError("unexpected end of expression");
      if (tok.t === "num") return { k: "num", v: Q.parse(tok.v) };
      if (tok.t === "op" && tok.v === "(") { const e = expr(); expect(")"); return e; }
      if (tok.t === "name") {
        if (peek() && peek().v === "(") {
          if (!FUNCTIONS.has(tok.v)) throw new SyntaxError(`unknown function ${tok.v}`);
          take(); const args = [expr()]; while (peek() && peek().v === ",") { take(); args.push(expr()); } expect(")");
          return { k: "fn", name: tok.v, args };
        }
        const x = tok.v.match(/^x(\d+)$/);
        if (x) { const index = parseInt(x[1], 10); if (index >= dimension) throw new SyntaxError(`${tok.v} exceeds the dimension ${dimension}`); return { k: "var", i: index }; }
        if (tok.v === "t" && allowParameter) return { k: "par" };
        if (tok.v === "t") throw new SyntaxError("the parameter t is only allowed in Sweep");
        if (tok.v === "pi" || tok.v === "e") return { k: "const", name: tok.v };
        throw new SyntaxError(`unknown name ${tok.v}`);
      }
      throw new SyntaxError(`unexpected "${tok.v}"`);
    }
    function power() { const base = atom(); if (peek() && peek().v === "**") { take(); return { k: "pow", a: base, b: unary() }; } return base; }
    function unary() { const tok = peek(); if (tok && (tok.v === "-" || tok.v === "+")) { take(); const a = unary(); return tok.v === "-" ? { k: "neg", a } : a; } return power(); }
    function term() { let left = unary(); while (peek() && (peek().v === "*" || peek().v === "/")) { const op = take().v; left = { k: op === "*" ? "mul" : "div", a: left, b: unary() }; } return left; }
    function expr() { let left = term(); while (peek() && (peek().v === "+" || peek().v === "-")) { const op = take().v; left = { k: op === "+" ? "add" : "sub", a: left, b: term() }; } return left; }
    const tree = expr();
    if (i !== tokens.length) throw new SyntaxError(`unexpected "${tokens[i].v}"`);
    return tree;
  }
  function constValue(node) {
    switch (node.k) {
      case "num": return node.v;
      case "neg": { const a = constValue(node.a); return a && a.neg(); }
      case "add": case "sub": case "mul": case "div": {
        const a = constValue(node.a), b = constValue(node.b);
        if (!a || !b) return null;
        return node.k === "add" ? a.add(b) : node.k === "sub" ? a.sub(b) : node.k === "mul" ? a.mul(b) : a.div(b);
      }
      case "pow": { const a = constValue(node.a), b = constValue(node.b); return a && b && b.isInt() ? a.pow(Number(b.n)) : null; }
      default: return null;
    }
  }
  function evalQ(node, point, t) {
    switch (node.k) {
      case "num": return node.v;
      case "var": return point[node.i];
      case "par": if (!t) throw new Error("no value for t"); return t;
      case "neg": return evalQ(node.a, point, t).neg();
      case "add": return evalQ(node.a, point, t).add(evalQ(node.b, point, t));
      case "sub": return evalQ(node.a, point, t).sub(evalQ(node.b, point, t));
      case "mul": return evalQ(node.a, point, t).mul(evalQ(node.b, point, t));
      case "div": return evalQ(node.a, point, t).div(evalQ(node.b, point, t));
      case "pow": { const k = constValue(node.b); if (!k || !k.isInt()) throw new NonPolynomial("non-integer exponent"); return evalQ(node.a, point, t).pow(Number(k.n)); }
      default: throw new NonPolynomial(`${node.name} is not rational`);
    }
  }
  function curvature(node) {
    const negate = (k) => (k === "convex" ? "concave" : k === "concave" ? "convex" : k);
    const add = (l, r) => { const ks = new Set([l, r]); ks.delete("constant"); if (!ks.size) return "constant"; if (ks.has("unknown") || (ks.has("convex") && ks.has("concave"))) return "unknown"; if (ks.size === 1 && ks.has("affine")) return "affine"; ks.delete("affine"); return [...ks][0]; };
    const scale = (k, f) => (f.isZero() ? "constant" : f.sign() > 0 ? k : negate(k));
    function walk(n) {
      if (constValue(n)) return "constant";
      switch (n.k) {
        case "var": return "affine";
        case "const": return "constant";
        case "neg": return negate(walk(n.a));
        case "add": return add(walk(n.a), walk(n.b));
        case "sub": return add(walk(n.a), negate(walk(n.b)));
        case "mul": { const fa = constValue(n.a), fb = constValue(n.b); if (fa) return scale(walk(n.b), fa); if (fb) return scale(walk(n.a), fb); return "unknown"; }
        case "div": { const f = constValue(n.b); return f && !f.isZero() ? scale(walk(n.a), Q.ONE.div(f)) : "unknown"; }
        case "pow": { const k = constValue(n.b); const base = walk(n.a); if (k && k.eq(Q.ONE)) return base; if (base === "affine" && k && k.isInt() && k.n >= 2n && k.n % 2n === 0n) return "convex"; return "unknown"; }
        default: return "unknown";
      }
    }
    return walk(node);
  }

  // ===== polynomials ==========================================================
  const MAX_MONOMIALS = 4096;
  const key = (e) => e.join(",");
  const exps = (k) => k.split(",").map(Number);
  const zeroKey = (m) => key(new Array(m).fill(0));
  function pconst(c, m) { const p = new Map(); if (!c.isZero()) p.set(zeroKey(m), c); return p; }
  function pvar(j, m) { const e = new Array(m).fill(0); e[j] = 1; return new Map([[key(e), Q.ONE]]); }
  function padd(a, b, sign = 1) {
    const r = new Map(a);
    for (const [k, v] of b) { const s = (r.get(k) || Q.ZERO).add(sign < 0 ? v.neg() : v); if (s.isZero()) r.delete(k); else r.set(k, s); }
    return r;
  }
  function pscale(a, c) { const r = new Map(); if (c.isZero()) return r; for (const [k, v] of a) r.set(k, v.mul(c)); return r; }
  function pmul(a, b) {
    const r = new Map();
    for (const [ka, va] of a) {
      const ea = exps(ka);
      for (const [kb, vb] of b) {
        const eb = exps(kb), k = key(ea.map((x, i) => x + eb[i]));
        const s = (r.get(k) || Q.ZERO).add(va.mul(vb));
        if (s.isZero()) r.delete(k); else r.set(k, s);
      }
    }
    if (r.size > MAX_MONOMIALS) throw new RangeError(`more than ${MAX_MONOMIALS} monomials`);
    return r;
  }
  function ppow(a, k, m) { let r = pconst(Q.ONE, m), base = a; while (k > 0) { if (k & 1) r = pmul(r, base); k >>= 1; if (k) base = pmul(base, base); } return r; }
  function isConstPoly(p, m) { return p.size === 0 || (p.size === 1 && p.has(zeroKey(m))); }
  function evalPoly(node, ctx) {
    const m = ctx.m;
    switch (node.k) {
      case "num": return pconst(node.v, m);
      case "var": return ctx.xs[node.i];
      case "par": if (!ctx.t) throw new Error("the parameter t is only allowed in Sweep"); return ctx.t;
      case "neg": return pscale(evalPoly(node.a, ctx), Q.MINUS_ONE);
      case "add": return padd(evalPoly(node.a, ctx), evalPoly(node.b, ctx));
      case "sub": return padd(evalPoly(node.a, ctx), evalPoly(node.b, ctx), -1);
      case "mul": return pmul(evalPoly(node.a, ctx), evalPoly(node.b, ctx));
      case "div": {
        const d = evalPoly(node.b, ctx);
        if (!isConstPoly(d, m)) throw new NonPolynomial("division by a non-constant");
        if (d.size === 0) throw new RangeError("division by zero");
        return pscale(evalPoly(node.a, ctx), Q.ONE.div(d.get(zeroKey(m))));
      }
      case "pow": {
        const k = constValue(node.b);
        if (!k || !k.isInt() || k.n < 0n) throw new NonPolynomial("exponents must be nonnegative integers");
        return ppow(evalPoly(node.a, ctx), Number(k.n), m);
      }
      default: throw new NonPolynomial(`${node.name} is not a polynomial`);
    }
  }
  function pevalQ(p, point) {
    let total = Q.ZERO;
    for (const [k, c] of p) { let term = c; exps(k).forEach((e, i) => { if (e) term = term.mul(point[i].pow(e)); }); total = total.add(term); }
    return total;
  }
  function floatPlan(p) { return [...p].map(([k, c]) => [c.toNumber(), exps(k)]); }
  function pevalF(plan, point) {
    let total = 0;
    for (const [c, e] of plan) { let term = c; for (let i = 0; i < e.length; i++) if (e[i]) term *= Math.pow(point[i], e[i]); total += term; }
    return total;
  }
  const wdeg = (e, w) => e.reduce((acc, a, i) => (a ? acc.add(w[i].mul(new Q(BigInt(a)))) : acc), Q.ZERO);
  function monomialText(e, axes) { return e.map((p, i) => (p ? (p === 1 ? axes[i] : `${axes[i]}^${p}`) : null)).filter(Boolean).join("·") || "1"; }
  function polyText(p, axes, limit = 12) {
    const items = [...p].map(([k, c]) => [exps(k), c]).filter(([, c]) => !c.isZero())
      .sort((a, b) => { const sa = a[0].reduce((x, y) => x + y, 0), sb = b[0].reduce((x, y) => x + y, 0); if (sa !== sb) return sa - sb; for (let i = 0; i < a[0].length; i++) if (a[0][i] !== b[0][i]) return a[0][i] - b[0][i]; return 0; });
    if (!items.length) return "0";
    const pieces = items.slice(0, limit).map(([e, c], index) => {
      const mag = c.abs(), body = monomialText(e, axes);
      const text = body === "1" ? label(mag) : mag.eq(Q.ONE) ? body : `${label(mag)}·${body}`;
      return index === 0 ? (c.sign() < 0 ? "-" : "") + text : ` ${c.sign() < 0 ? "-" : "+"} ${text}`;
    });
    if (items.length > limit) pieces.push(` + … (${items.length - limit} more)`);
    return pieces.join("");
  }
  const divides = (s, l) => s.some((x, i) => x !== l[i]) && s.every((x, i) => x <= l[i]);

  // ===== geometry =============================================================
  function parseSystem(text) {
    let raw;
    try { raw = JSON.parse(String(text).trim().replace(/\(/g, "[").replace(/\)/g, "]")); }
    catch { throw new SyntaxError("write the polyhedron as ([[a11, a12, …], …], [b1, …])"); }
    if (!Array.isArray(raw) || raw.length !== 2 || !Array.isArray(raw[0]) || !Array.isArray(raw[1])) throw new SyntaxError("write the polyhedron as ([[...]], [...])");
    const rows = raw[0].map((r) => r.map((v) => Q.of(v))), rhs = raw[1].map((v) => Q.of(v));
    if (!rows.length || rows.length !== rhs.length || new Set(rows.map((r) => r.length)).size !== 1) throw new SyntaxError("A must have one row per entry of b, all of equal length");
    if (rows[0].length > 6) throw new RangeError("dimension above 6 is not supported here");
    return { rows, rhs };
  }
  const dot = (a, b) => a.reduce((acc, x, i) => acc.add(x.mul(b[i])), Q.ZERO);
  function solveQ(A, b) {
    const n = A.length, M = A.map((r, i) => [...r, b[i]]);
    for (let c = 0; c < n; c++) {
      let p = c; while (p < n && M[p][c].isZero()) p++;
      if (p === n) return null;
      [M[c], M[p]] = [M[p], M[c]];
      const lead = M[c][c]; M[c] = M[c].map((v) => v.div(lead));
      for (let r = 0; r < n; r++) if (r !== c && !M[r][c].isZero()) { const f = M[r][c]; M[r] = M[r].map((v, j) => v.sub(f.mul(M[c][j]))); }
    }
    return M.map((r) => r[n]);
  }
  function* combinations(m, k, start = 0, acc = []) {
    if (acc.length === k) { yield acc.slice(); return; }
    for (let i = start; i < m; i++) { acc.push(i); yield* combinations(m, k, i + 1, acc); acc.pop(); }
  }
  function binom(m, k) { let r = 1; for (let i = 1; i <= k; i++) r = (r * (m - k + i)) / i; return r; }
  function vertexEnum(rows, rhs, limit = 6000) {
    const m = rows.length, n = rows[0].length;
    if (binom(m, n) > limit) return null;
    const found = [], seen = new Set();
    for (const subset of combinations(m, n)) {
      const x = solveQ(subset.map((i) => rows[i]), subset.map((i) => rhs[i]));
      if (!x) continue;
      const k = x.map(String).join("|");
      if (seen.has(k)) continue;
      if (rows.every((r, j) => dot(r, x).le(rhs[j]))) { seen.add(k); found.push(x); }
    }
    return found;
  }
  function fmFeasible(rows, bounds, budget = 6000) {
    const norm = (r, b) => { const s = r.find((a) => !a.isZero()); if (!s) return [r, b]; const f = s.abs(); return [r.map((a) => a.div(f)), b.div(f)]; };
    let system = new Map();
    const put = (map, r, b) => { const [rr, bb] = norm(r, b); const k = rr.map(String).join(","); const old = map.get(k); if (!old || bb.lt(old[1])) map.set(k, [rr, bb]); };
    rows.forEach((r, i) => put(system, r, bounds[i]));
    const n = rows[0].length;
    for (let k = n - 1; k >= 0; k--) {
      const all = [...system.values()], pos = all.filter(([r]) => r[k].sign() > 0), neg = all.filter(([r]) => r[k].sign() < 0);
      const next = new Map();
      all.filter(([r]) => r[k].isZero()).forEach(([r, b]) => put(next, r, b));
      for (const [p, pb] of pos) for (const [q, qb] of neg) {
        const fp = p[k], fq = q[k].neg();
        put(next, p.map((a, j) => a.div(fp).add(q[j].div(fq))), pb.div(fp).add(qb.div(fq)));
        if (next.size > budget) throw new RangeError("feasibility budget exceeded");
      }
      system = next;
      for (const [r, b] of system.values()) if (r.every((a) => a.isZero()) && b.sign() < 0) return false;
    }
    return [...system.values()].every(([r, b]) => !r.every((a) => a.isZero()) || b.sign() >= 0);
  }
  function isBounded(rows) {
    const n = rows[0].length;
    try {
      for (let i = 0; i < n; i++) for (const sign of [1, -1]) {
        const unit = new Array(n).fill(Q.ZERO); unit[i] = new Q(BigInt(-sign));
        if (fmFeasible([...rows, unit], [...rows.map(() => Q.ZERO), Q.MINUS_ONE])) return false;
      }
    } catch { return null; }
    return true;
  }

  // ===== the exact certificate ================================================
  const THEOREM = "docs/FORMAL_FACE_SELECTION.md";
  const LINKS = {
    standing: ["§0 Standing assumptions", `${THEOREM}#0-standing-assumptions`, "P is a bounded full-dimensional polyhedron; F and G are real analytic near v."],
    vertex: ["§1 Setup", `${THEOREM}#1-setup`, "v is a simple vertex; Φ(c) = v + Σ cᵢuᵢ identifies the orthant with the tangent cone."],
    transport: ["V.20 Feasible-chart transport", "docs/FORMAL_AMBIENT_FACE_TRANSPORT.md#statement", "The Newton data are the exact pullbacks D(c) = F(v) − F(Φ(c)) and R(c) = G(Φ(c)) − G(v)."],
    H0: ["Hypothesis 0 · global isolation", `${THEOREM}#2-global-isolation`, "v is the unique maximizer of F on P, so Lemma 1 localizes every perturbed maximizer."],
    H1: ["Hypothesis 1 · strict local maximality", `${THEOREM}#4-hypotheses-with-uniform-remainders`, "D(c) ≥ 0 near zero, with equality only at zero."],
    H2: ["Hypothesis 2 · diagonal principal part", `${THEOREM}#4-hypotheses-with-uniform-remainders`, "in_w(D) = D₀ = Σ Aᵢcᵢ^βᵢ with Aᵢ > 0, βᵢ > 1, and a uniform weighted remainder."],
    H3: ["Hypothesis 3 · polynomial perturbation", `${THEOREM}#4-hypotheses-with-uniform-remainders`, "R is a finite polynomial with R(0) = 0."],
    faces: ["§5 Faces and admissibility", `${THEOREM}#5-faces-and-admissibility-defined-from-the-data-alone`, "Restrict the combined R to each face; qualify its first nonzero layer if 0 < q_S < 1 and it is positive in the relative interior."],
    H5: ["Hypothesis 5 · positive-gain envelope", `${THEOREM}#6-upper-control-on-unqualified-faces`, "R₊ ≤ K·D₀^q* near zero (with q* = 1 and Lemma 2 when no face qualifies)."],
    selection: ["§8 Selection, qualified", `${THEOREM}#8-selection-qualified`, "Under Hypotheses 0–5, Δ(s) = Θ(s^γ) with γ = 1/(1 − q*)."],
  };
  const ORDER = Object.keys(LINKS);
  function link(id, status, method, detail, values) {
    const [clause, doc, statement] = LINKS[id];
    const out = { id, clause, doc, statement, status, method, detail };
    if (values) out.values = values;
    return out;
  }

  function transport(tree, model, t, withParameter = false) {
    const n = model.n, m = n + (withParameter ? 1 : 0);
    const xs = model.vertex.map((v, k) => {
      let p = pconst(v, m);
      model.axes.forEach((_, i) => { const u = model.generators[i][k]; if (!u.isZero()) p = padd(p, pscale(pvar(i, m), u)); });
      return p;
    });
    const ctx = { m, xs, t: withParameter ? pvar(n, m) : t ? pconst(t, m) : null };
    return evalPoly(tree, ctx);
  }
  function centered(p, n) { const r = new Map(); for (const [k, c] of p) if (!exps(k).slice(0, n).every((e) => e === 0)) r.set(k, c); return r; }

  /* Localize at the base maximizer and certify everything that depends on F. */
  function localize(request) {
    const links = [];
    const result = { status: "not_applicable", conclusion: null, links };
    let rows, rhs, n, baseTree;
    try {
      ({ rows, rhs } = parseSystem(request.system));
      n = rows[0].length;
      baseTree = parseExpression(request.base, n);
    } catch (error) { result.reason = `input is outside the exact checker: ${error.message}`; return { result, model: null }; }
    const bounded = isBounded(rows);
    const corners = vertexEnum(rows, rhs);
    if (bounded === false) { links.push(link("standing", "failed", "exact Fourier–Motzkin recession test", "P is unbounded: some direction d ≠ 0 has A·d ≤ 0.")); result.status = "incomplete"; return { result, model: null }; }
    if (!corners || !corners.length) { links.push(link("standing", corners ? "failed" : "unresolved", "exact vertex enumeration", corners ? "P has no vertices." : "too many constraints to enumerate vertices exactly.")); result.status = "incomplete"; return { result, model: null }; }
    let values;
    try { values = corners.map((c) => evalQ(baseTree, c)); }
    catch (error) { result.reason = "The browser engine handles polynomial F and G; run the Python engine for other inputs."; return { result, model: null }; }
    let best = values[0]; values.forEach((v) => { if (v.gt(best)) best = v; });
    const bestCorners = corners.filter((_, i) => values[i].eq(best));
    const vertex = bestCorners[0];
    const active = rows.map((r, j) => (dot(r, vertex).eq(rhs[j]) ? j : -1)).filter((j) => j >= 0);
    // The polyhedron itself, for pictures: each constraint's facet as the exact
    // list of vertices on it, recorded before the simplicity check.
    result.geometry = {
      n, vertices: corners.map((c) => c.map((x) => x.toNumber())), vertex: vertex.map((x) => x.toNumber()),
      vertex_index: corners.indexOf(vertex), active,
      facets: rows.map((r, j) => corners.map((c, i) => (dot(r, c).eq(rhs[j]) ? i : -1)).filter((i) => i >= 0)),
    };
    if (active.length !== n) {
      links.push(link("standing", bounded ? "exact" : "unresolved", "exact recession test and vertex enumeration", `P is bounded with ${corners.length} vertices.`));
      links.push(link("vertex", "failed", "exact active-set count", `The best vertex (${vertex.map(String).join(", ")}) has ${active.length} active constraints in dimension ${n}: its tangent cone is not simplicial, which the theorem excludes.`, { active }));
      result.status = "incomplete"; return { result, model: null };
    }
    const AS = active.map((j) => rows[j]);
    const generators = [];
    for (let i = 0; i < n; i++) generators.push(solveQ(AS, AS.map((_, r) => (r === i ? Q.MINUS_ONE : Q.ZERO))));
    const axes = generators.map((_, i) => `c${i}`);
    let rho = Q.ONE;
    rows.forEach((r, j) => {
      if (active.includes(j)) return;
      const slack = rhs[j].sub(dot(r, vertex));
      const growth = generators.reduce((acc, u) => { const g = dot(r, u); return g.sign() > 0 ? acc.add(g) : acc; }, Q.ZERO);
      if (growth.sign() > 0) { const cand = slack.div(growth); if (cand.lt(rho)) rho = cand; }
    });
    const half = rho.div(new Q(2n));
    const interior = vertex.map((v, k) => generators.reduce((acc, u) => acc.add(half.mul(u[k])), v));
    const fullDimensional = rows.every((r, j) => dot(r, interior).lt(rhs[j]));
    const model = { rows, rhs, n, baseTree, base: request.base, vertex, active, axes, generators, rho, interior, corners, bounded };
    model.point = (c) => vertex.map((v, k) => c.reduce((acc, ci, i) => acc.add(ci.mul(generators[i][k])), v));
    model.contains = (x) => rows.every((r, j) => dot(r, x).le(rhs[j]));
    // The browser engine pulls back by its own exact substitution: independent of the Python compiler.
    let basePull;
    try { basePull = transport(baseTree, model); } catch (error) { result.reason = `F is not a polynomial: ${error.message}`; return { result, model: null }; }
    model.baseAtVertex = evalQ(baseTree, vertex);
    model.loss = pscale(centered(basePull, n), Q.MINUS_ONE);
    const standingOk = bounded && fullDimensional;
    links.push(link("standing", standingOk ? "exact" : (fullDimensional ? "unresolved" : "failed"), "exact recession test, interior point, polynomial degree",
      standingOk ? "P is bounded and full-dimensional; F and G are polynomials, hence analytic." : (fullDimensional ? "Boundedness was not decided." : "P has empty interior."),
      { vertices: corners.length, interior_point: interior.map(String) }));
    links.push(link("vertex", "exact", "exact active-constraint solve A_S·v = b_S, A_S·uᵢ = −eᵢ",
      `v = (${vertex.map(String).join(", ")}) with active constraints [${active.join(", ")}]; Φ([0, ${rho}]ⁿ) ⊂ P.`, { vertex: vertex.map(String), active }));
    // H2 first: its exact form also discharges H1.
    const orders = [], coefficients = [];
    let h1Problem = null, h2Problem = null;
    for (let i = 0; i < n && !h1Problem; i++) {
      const pure = [...model.loss].map(([k, c]) => [exps(k), c]).filter(([e]) => e[i] && e.reduce((a, b) => a + b, 0) === e[i]).map(([e, c]) => [e[i], c]).sort((a, b) => a[0] - b[0]);
      if (!pure.length) { h1Problem = `D has no pure term along ${axes[i]}: F is constant on that edge to every order.`; break; }
      const [beta, coef] = pure[0];
      orders.push(beta); coefficients.push(coef);
      if (coef.sign() < 0) h1Problem = `F increases along ${axes[i]} (leading coefficient ${coef.neg()} > 0 in F).`;
      else if (beta === 1) h2Problem = `β = 1 along ${axes[i]}: the base decays linearly, but the theorem needs βᵢ > 1.`;
    }
    if (!h1Problem) model.principal = axes.map((a, i) => [orders[i], coefficients[i]]);
    if (!h1Problem && !h2Problem) {
      const w = orders.map((b) => new Q(1n, BigInt(b)));
      model.weights = w;
      const principal = new Set(axes.map((_, i) => key(axes.map((__, j) => (j === i ? orders[i] : 0)))));
      const low = [...model.loss.keys()].filter((k) => !principal.has(k) && wdeg(exps(k), w).le(Q.ONE));
      if (low.length) h2Problem = `in_w(D) is not diagonal: ${low.map((k) => `${monomialText(exps(k), axes)} (weight ${wdeg(exps(k), w)})`).join(", ")} sits at or below the principal weight 1.`;
    }
    const lossText = polyText(model.loss, axes);
    if (h1Problem) {
      links.push(link("H0", "not_reached", "—", "Global isolation needs strict local maximality first."));
      links.push(link("H1", "failed", "exact Newton data of D", h1Problem));
      links.push(link("H2", "not_reached", "exact Newton data of D", h1Problem));
    } else {
      const d0 = axes.map((a, i) => `${coefficients[i].eq(Q.ONE) ? "" : coefficients[i] + "·"}${a}^${orders[i]}`).join(" + ");
      const tie = bestCorners.length > 1;
      const positiveLoss = [...model.loss.values()].every((c) => c.sign() >= 0);
      const shape = curvature(baseTree);
      let h0;
      if (tie) h0 = link("H0", "failed", "exact vertex comparison", `F attains its maximum ${best} at ${bestCorners.length} vertices.`);
      else if (positiveLoss) h0 = link("H0", "exact", "global positivity of the base loss", "Every coefficient of D is nonnegative and each edge carries a positive pure term, so D > 0 on the whole cone minus 0; since P ⊂ v + T_vP, F(x) < F(v) for every x ∈ P other than v.");
      else if ((shape === "concave" || shape === "affine") && !h2Problem) h0 = link("H0", "exact", "concavity certificate plus strict local maximality", `F is ${shape} by structural rules; a strict local maximum of a concave function on a convex set is its unique global maximum.`);
      else h0 = link("H0", "unresolved", "no exact route", "No exact certificate; the Python engine adds the backend's isolation probe. A finite probe cannot prove uniqueness.");
      links.push(h0);
      links.push(link("H1", h2Problem ? "unresolved" : "exact", "implied by the exact H2", h2Problem ? "Not implied without H2." : "D ≥ a·D₀ > 0 near zero on the cone, by compactness of the section D₀ = 1."));
      links.push(link("H2", h2Problem ? "failed" : "exact", "exact weighted Newton polygon of D", h2Problem || `D₀ = ${d0}; every other monomial of D has weighted degree > 1, so the remainder is uniform on compact sets.`, { orders }));
    }
    result.model = describe(model, lossText);
    return { result, model };
  }

  function describe(model, lossText) {
    return {
      vertex: model.vertex.map(String), active_constraints: model.active, edge_axes: model.axes,
      generators: Object.fromEntries(model.axes.map((a, i) => [a, model.generators[i].map(String)])),
      released_by_axis: Object.fromEntries(model.axes.map((a, i) => [a, model.active[i]])),
      local_box_radius: String(model.rho), loss: lossText,
      weights: model.weights ? Object.fromEntries(model.axes.map((a, i) => [a, String(model.weights[i])])) : null,
    };
  }

  function faceTable(model, gain) {
    const n = model.n, w = model.weights, table = [];
    const grid = [new Q(1n, 4n), new Q(1n, 2n), Q.ONE, new Q(2n), new Q(4n)];
    for (let size = 1; size <= n; size++) for (const face of combinations(n, size)) {
      const restricted = [...gain].map(([k, c]) => [exps(k), c]).filter(([e]) => e.every((x, i) => !x || face.includes(i)));
      const entry = { face: face.map((i) => model.axes[i]), edges: face };
      if (!restricted.length) { table.push(Object.assign(entry, { status: "inactive", reason: "the perturbation vanishes on this face" })); continue; }
      let q = null; restricted.forEach(([e]) => { const d = wdeg(e, w); if (!q || d.lt(q)) q = d; });
      const initial = new Map(restricted.filter(([e]) => wdeg(e, w).eq(q)).map(([e, c]) => [key(e), c]));
      Object.assign(entry, { degree: String(q), initial_form: polyText(initial, model.axes), _q: q, _initial: initial });
      const signs = new Set([...initial.values()].map((c) => c.sign() > 0));
      if (q.ge(Q.ONE)) Object.assign(entry, q.eq(Q.ONE) ? { status: "critical", reason: "q_S = 1 needs a different balance" } : { status: "subleading", reason: "q_S > 1: dominated by the base" });
      else if (signs.size === 1 && !signs.has(true)) Object.assign(entry, { status: "non_positive", reason: "every initial coefficient is negative" });
      else {
        const candidates = [new Array(n).fill(Q.ZERO).map((_, i) => (face.includes(i) ? Q.ONE : Q.ZERO))];
        if (face.length <= 4) {
          const walk = (depth, acc) => { if (depth === face.length) { const pt = new Array(n).fill(Q.ZERO); face.forEach((i, j) => { pt[i] = acc[j]; }); candidates.push(pt); return; } for (const g of grid) walk(depth + 1, [...acc, g]); };
          walk(0, []);
        }
        const witness = candidates.find((pt) => face.every((i) => pt[i].sign() > 0) && pevalQ(initial, pt).sign() > 0);
        if (witness) Object.assign(entry, { status: "qualified", witness: witness.map(String), witness_value: String(pevalQ(initial, witness)), reason: "0 < q_S < 1 with an exact positive relative-interior witness" });
        else Object.assign(entry, { status: "unresolved", reason: "mixed signs and no rational witness found" });
      }
      table.push(entry);
    }
    const qualified = table.filter((e) => e.status === "qualified");
    let qStar = null; qualified.forEach((e) => { if (!qStar || e._q.lt(qStar)) qStar = e._q; });
    table.forEach((e) => { e.winning = !!qStar && e.status === "qualified" && e._q.eq(qStar); });
    return { table, qStar };
  }

  function envelope(model, gain, cutoff) {
    const entries = [...gain].map(([k, c]) => [exps(k), c]);
    const negatives = entries.filter(([, c]) => c.sign() < 0).map(([e]) => e);
    const uncontrolled = [], absorbed = [];
    entries.sort((a, b) => (key(a[0]) < key(b[0]) ? -1 : 1)).forEach(([e, c]) => {
      if (c.sign() <= 0 || wdeg(e, model.weights).ge(cutoff)) return;
      const divisor = negatives.find((nmono) => divides(nmono, e));
      const text = monomialText(e, model.axes);
      if (divisor) absorbed.push(`${text} by −${monomialText(divisor, model.axes)}`);
      else uncontrolled.push(`${text} (degree ${wdeg(e, model.weights)})`);
    });
    return { ok: !uncontrolled.length, uncontrolled, absorbed };
  }

  /* Certify everything that depends on G, for a fixed value of the parameter t. */
  function analyze(local, request, t) {
    const { model } = local;
    const result = JSON.parse(JSON.stringify(local.result));
    const links = result.links;
    if (!model) return { result, gain: null };
    let pertTree;
    try { pertTree = parseExpression(request.perturbation, model.n, !!t); }
    catch (error) { result.status = "not_applicable"; result.reason = error.message; return { result, gain: null }; }
    let gain;
    try { gain = centered(transport(pertTree, model, t), model.n); }
    catch (error) { result.reason = `G is not a polynomial: ${error.message}`; result.status = "incomplete"; return { result, gain: null }; }
    model.perturbationTree = pertTree; model.t = t || null;
    model.perturbationAtVertex = evalQ(pertTree, model.vertex, t);
    model.gain = gain;
    const at = (id) => links.findIndex((l) => l.id === id);
    links.splice(at("H0"), 0, link("transport", "exact", "exact symbolic substitution (independent of the repository's compiler)",
      `D(c) = ${polyText(model.loss, model.axes)}, R(c) = ${polyText(gain, model.axes)}.`, { loss: polyText(model.loss, model.axes), gain: polyText(gain, model.axes) }));
    const status = (id) => (links.find((l) => l.id === id) || {}).status;
    links.push(link("H3", "exact", "exact pullback", gain.size ? `R(c) = ${polyText(gain, model.axes)} is a finite polynomial with R(0) = 0.` : "R ≡ 0 near v: the perturbation is constant there, so Δ(s) = 0."));
    if (!model.weights) {
      ["faces", "H5", "selection"].forEach((id) => links.push(link(id, "not_reached", "—", "Face weights need the exact principal part (H1/H2).")));
      result.status = "incomplete"; return { result, gain };
    }
    if (!gain.size) {
      links.push(link("faces", "exact", "exact face restriction", "Every face is inactive."));
      links.push(link("H5", "exact", "trivial", "R ≡ 0."));
      links.push(link("selection", "exact", "trivial", "Δ(s) = 0 for every s ≥ 0."));
      Object.assign(result, { status: "zero_response", conclusion: "Δ(s) = 0 for every s ≥ 0", q_star: null, gamma: null });
      return { result, gain };
    }
    const { table, qStar } = faceTable(model, gain);
    const counts = {}; table.forEach((e) => { counts[e.status] = (counts[e.status] || 0) + 1; });
    const unresolved = table.some((e) => e.status === "unresolved");
    const publicTable = table.map(({ _q, _initial, ...rest }) => rest);
    const nWinning = table.filter((e) => e.winning).length;
    links.push(link("faces", unresolved ? "unresolved" : "exact", "exact face restriction and rational witnesses",
      (qStar ? `q* = ${qStar} on ${nWinning} face(s); ` : "No face qualifies; ") + Object.keys(counts).sort().map((k) => `${counts[k]} ${k}`).join(", ") + ".", { faces: publicTable }));
    const cutoff = qStar || Q.ONE;
    const env = envelope(model, gain, cutoff);
    links.push(link("H5", env.ok ? "exact" : "unresolved", "monomial domination and absorption (sufficient test)",
      env.ok ? `Every positive monomial has weighted degree ≥ ${cutoff}` + (env.absorbed.length ? ` or is absorbed (${env.absorbed.join("; ")})` : "") + "."
        : `Positive terms below ${cutoff} are not controlled: ${env.uncontrolled.join(", ")}. A curved approach can open a channel that no coordinate face sees.`,
      { uncontrolled: env.uncontrolled, absorbed: env.absorbed }));
    const open = ["standing", "vertex", "transport", "H0", "H1", "H2", "H3", "faces", "H5"].filter((id) => status(id) !== "exact");
    if (qStar && !open.length) {
      const gamma = Q.ONE.div(Q.ONE.sub(qStar));
      links.push(link("selection", "exact", "Hypotheses 0–5 discharged exactly", `q* = ${qStar}, so Δ(s) = Θ(s^${gamma}).`, { q_star: String(qStar), gamma: String(gamma) }));
      Object.assign(result, { status: "theorem", conclusion: `Δ(s) = Θ(s^${gamma})`, q_star: String(qStar), gamma: String(gamma) });
    } else if (!qStar && !open.length) {
      links.push(link("selection", "exact", "Lemma 2 with R₊ ≤ K·D₀", "No face qualifies and the positive part is dominated by the base: Δ(s) = 0 for all small s > 0."));
      Object.assign(result, { status: "zero_response", conclusion: "Δ(s) = 0 for all sufficiently small s > 0", q_star: null, gamma: null });
    } else {
      const gamma = qStar ? Q.ONE.div(Q.ONE.sub(qStar)) : null;
      links.push(link("selection", qStar ? "unresolved" : "not_reached", "conditional on the open links",
        (qStar ? `The exact face data give q* = ${qStar} and γ = ${gamma}, but ` : "No qualified face; ") + `open links: ${open.join(", ")}.`, { open_links: open }));
      Object.assign(result, { status: "incomplete", conclusion: null, open_links: open, q_star: qStar ? String(qStar) : null, gamma: gamma ? String(gamma) : null });
    }
    result._table = table; result._qStar = qStar;
    return { result, gain };
  }

  // ===== V.22: exact quadratic elimination ====================================
  function curvedReduction(model) {
    if (!model || model.n !== 2 || !model.gain) return null;
    const base = [...model.loss].map(([k, c]) => [exps(k), c]), pert = [...model.gain].map(([k, c]) => [exps(k), c]);
    const out = (reason) => ({ status: "outside_scope", blockers: [reason] });
    if (base.length !== 2 || base.some(([e]) => e.filter((x) => x > 0).length !== 1)) return out("the full base loss must be exactly two pure powers");
    const terms = {};
    for (const [e, c] of base) { const i = e[0] ? 0 : 1; if (terms[i] || e[i] <= 1 || c.sign() <= 0) return out("each base axis needs one positive power of order > 1"); terms[i] = [e[i], c]; }
    const reasons = [];
    for (const xi of [0, 1]) {
      const yi = 1 - xi, [p] = terms[xi], [q, B] = terms[yi];
      const driver = new Map(), remainder = new Map(); let a = Q.ZERO, bad = false;
      for (const [e, c] of pert) { const i = e[xi], j = e[yi]; if (i === 2 && j === 0) a = c.neg(); else if (i === 1 && j > 0) driver.set(j, c); else if (i === 0) remainder.set(j, c); else bad = true; }
      if (bad || a.sign() <= 0 || !driver.size) { reasons.push(`${model.axes[xi]}: requires -a*x**2+x*H(y)+K(y), a>0, H(0)=0`); continue; }
      const r = Math.min(...driver.keys());
      if (driver.get(r).sign() <= 0) { reasons.push(`${model.axes[xi]}: square-center curve is not positive near the origin`); continue; }
      const reduced = new Map(remainder);
      for (const [i, ci] of driver) for (const [j, cj] of driver) reduced.set(i + j, (reduced.get(i + j) || Q.ZERO).add(ci.mul(cj).div(a.mul(new Q(4n)))));
      [...reduced].forEach(([k, c]) => { if (c.isZero()) reduced.delete(k); });
      if (!reduced.size) { reasons.push(`${model.axes[xi]}: reduced gain has no positive initial layer`); continue; }
      const alpha = Math.min(...reduced.keys()), C = reduced.get(alpha);
      if (C.sign() <= 0) { reasons.push(`${model.axes[xi]}: reduced gain has no positive initial layer`); continue; }
      if (!(alpha > 0 && alpha < q)) { reasons.push(`${model.axes[xi]}: reduced order must lie strictly between 0 and ${q}`); continue; }
      if (p * r <= q) { reasons.push(`${model.axes[xi]}: omitted base cost is not subleading (p*r=${p * r} <= q=${q})`); continue; }
      const gamma = new Q(BigInt(q), BigInt(q - alpha));
      const prefactor = C.mul(new Q(BigInt(q - alpha), BigInt(q)));
      const scaleBase = C.mul(new Q(BigInt(alpha))).div(new Q(BigInt(q)).mul(B));
      const power = new Q(BigInt(alpha), BigInt(q - alpha));
      const exact = power.isInt() ? String(prefactor.mul(scaleBase.pow(Number(power.n)))) : `(${prefactor}) * (${scaleBase})**(${power})`;
      const value = prefactor.toNumber() * Math.pow(scaleBase.toNumber(), power.toNumber());
      return { status: "licensed", gamma: String(gamma), coefficient: exact, coefficient_value: value, effective_weight: String(new Q(BigInt(alpha), BigInt(q))),
        eliminated_axis: model.axes[xi], identity: "R = S(y) - a*(x - H(y)/(2*a))**2", proof_basis: "exact full-polynomial transport and quadratic elimination" };
    }
    return out(reasons.join("; "));
  }

  // ===== the ambient-axis counterfactual =======================================
  function ambientAxes(model) {
    if (!model || !model.gain) return null;
    const n = model.n, corners = model.corners;
    const signs = model.vertex.map((v, k) => (corners.every((c) => c[k].ge(v)) ? 1 : -1));
    const ghost = Object.assign({}, model, { generators: signs.map((s, k) => model.vertex.map((_, j) => (j === k ? new Q(BigInt(s)) : Q.ZERO))), axes: signs.map((_, k) => `a${k}`) });
    let loss, gain;
    try {
      loss = pscale(centered(transport(model.baseTree, ghost), n), Q.MINUS_ONE);
      gain = centered(transport(model.perturbationTree, ghost, model.t), n);
    } catch { return null; }
    const orders = [];
    for (let k = 0; k < n; k++) {
      const pure = [...loss].map(([kk, c]) => [exps(kk), c]).filter(([e]) => e[k] && e.reduce((a, b) => a + b, 0) === e[k]).sort((a, b) => a[0][k] - b[0][k]);
      if (!pure.length || pure[0][1].sign() <= 0 || pure[0][0][k] < 2) return null;
      orders.push(pure[0][0][k]);
    }
    if (!gain.size) return null;
    ghost.weights = orders.map((b) => new Q(1n, BigInt(b)));
    const { qStar } = faceTable(ghost, gain);
    const activeRows = model.rows.filter((r, j) => dot(r, model.vertex).eq(model.rhs[j]));
    const infeasible = ghost.generators.map((u, k) => (activeRows.every((r) => dot(r, u).sign() <= 0) ? null : ghost.axes[k])).filter(Boolean);
    return { directions: Object.fromEntries(ghost.axes.map((a, k) => [a, ghost.generators[k].map(String)])), infeasible_directions: infeasible,
      orders: Object.fromEntries(ghost.axes.map((a, k) => [a, orders[k]])), q_star: qStar ? String(qStar) : null, gamma: qStar ? String(Q.ONE.div(Q.ONE.sub(qStar))) : null };
  }

  // ===== certified measurement ===============================================
  const BUDGETS = { quick: { steps: 12, need: 6, starts: 2, iterations: 80 }, standard: { steps: 17, need: 7, starts: 3, iterations: 140 } };
  const DECADES = 16, GRID_STEP = { 1: 0.25, 2: 0.8, 3: 1.6, 4: 2.67 };
  function nelderMead(f, start, step, iterations) {
    const n = start.length;
    let simplex = [start.slice(), ...start.map((_, i) => start.map((x, j) => (j === i ? x + step : x)))];
    let values = simplex.map(f);
    for (let it = 0; it < iterations; it++) {
      const order = values.map((v, i) => i).sort((a, b) => values[a] - values[b]);
      simplex = order.map((i) => simplex[i]); values = order.map((i) => values[i]);
      let spread = 0; for (let k = 1; k <= n; k++) for (let j = 0; j < n; j++) spread = Math.max(spread, Math.abs(simplex[k][j] - simplex[0][j]));
      if (spread < 1e-7) break;
      const centroid = new Array(n).fill(0).map((_, j) => simplex.slice(0, n).reduce((a, p) => a + p[j], 0) / n);
      const worst = simplex[n];
      const reflected = centroid.map((c, j) => c + (c - worst[j])), fr = f(reflected);
      if (fr < values[0]) { const expanded = centroid.map((c, j) => c + 2 * (c - worst[j])), fe = f(expanded); if (fe < fr) { simplex[n] = expanded; values[n] = fe; } else { simplex[n] = reflected; values[n] = fr; } }
      else if (fr < values[n - 1]) { simplex[n] = reflected; values[n] = fr; }
      else {
        const towards = fr >= values[n] ? worst : reflected;
        const contracted = centroid.map((c, j) => c + 0.5 * (towards[j] - c)), fc = f(contracted);
        if (fc < Math.min(fr, values[n])) { simplex[n] = contracted; values[n] = fc; }
        else { const best = simplex[0]; simplex = [best, ...simplex.slice(1).map((p) => p.map((x, j) => best[j] + 0.5 * (x - best[j])))]; values = [values[0], ...simplex.slice(1).map(f)]; }
      }
    }
    let bi = 0; values.forEach((v, i) => { if (v < values[bi]) bi = i; });
    return [simplex[bi], values[bi]];
  }
  function measure(model, predictions, budgetName = "standard") {
    if (!model || !model.gain || model.baseAtVertex == null) return { status: "not_available", reason: "certified bounds need a simple vertex and polynomial F and G" };
    if (model.n > 4) return { status: "not_available", reason: "the search supports dimension ≤ 4" };
    if (!model.gain.size) return { status: "complete", rows: [], verdicts: [], summary: "R ≡ 0 near v: no gain at any s" };
    const budget = BUDGETS[budgetName], n = model.n, rho = model.rho.toNumber();
    const loss = floatPlan(model.loss), gainPlan = floatPlan(model.gain);
    const faces = []; for (let k = 1; k <= n; k++) for (const f of combinations(n, k)) faces.push(f);
    const champions = [];
    const point = (face, u) => { const c = new Array(n).fill(0); face.forEach((i, j) => { c[i] = rho * Math.pow(10, -Math.min(DECADES, Math.max(0, u[j]))); }); return c; };
    function best(s) {
      let champion = new Array(n).fill(0), championValue = 0;
      const continuations = champions.slice(-2).map(([, c]) => c);
      if (champions.length >= 2) {
        const [[s1, c1], [s2, c2]] = champions.slice(-2), r = Math.log(s / s2) / Math.log(s2 / s1);
        continuations.push(c1.map((a, i) => (a > 0 && c2[i] > 0 ? Math.min(rho, c2[i] * Math.pow(c2[i] / a, r)) : 0)));
      }
      for (const face of faces) {
        const objective = (u) => { const c = point(face, u); return pevalF(loss, c) - s * pevalF(gainPlan, c); };
        const step = GRID_STEP[face.length], axis = [];
        for (let k = 0; k <= Math.floor(DECADES / step); k++) axis.push(k * step);
        let grid = axis.map((a) => [a]);
        for (let d = 1; d < face.length; d++) grid = grid.flatMap((g) => axis.map((a) => [...g, a]));
        const scored = grid.map((u) => [objective(u), u]).sort((a, b) => a[0] - b[0]).slice(0, budget.starts);
        const starts = scored.map(([, u]) => u).concat(continuations.filter((c) => c.every((x, i) => (x > 0) === face.includes(i))).map((c) => face.map((i) => Math.log10(rho / c[i]))));
        for (const start of starts) {
          const [u, value] = nelderMead(objective, start, 1.0, budget.iterations * face.length);
          if (-value > championValue) { champion = point(face, u); championValue = -value; }
        }
      }
      const gainF = (c) => s * pevalF(gainPlan, c) - pevalF(loss, c);
      let bestValue = gainF(champion);
      const orderIdx = champion.map((v, i) => i).sort((a, b) => champion[a] - champion[b]);
      for (const i of orderIdx) if (champion[i] > 0) { const trial = champion.slice(); trial[i] = 0; const v = gainF(trial); if (v >= bestValue - 1e-9 * Math.abs(bestValue)) { champion = trial; bestValue = Math.max(bestValue, v); } }
      if (championValue > 0) champions.push([s, champion]);
      return champion;
    }
    function certifyPoint(cFloat, s) {
      const c = cFloat.map((ci) => (ci > 0 ? (() => { const v = Q.parse(ci.toExponential(11)); return v.lt(model.rho) ? v : model.rho; })() : Q.ZERO));
      const x = model.point(c), feasible = model.contains(x);
      const gain = evalQ(model.baseTree, x).sub(model.baseAtVertex).add(s.mul(evalQ(model.perturbationTree, x, model.t).sub(model.perturbationAtVertex)));
      const chartGain = pevalQ(model.loss, c).neg().add(s.mul(pevalQ(model.gain, c)));
      const lower = feasible && gain.sign() > 0 ? gain : Q.ZERO;
      return { s: floorDecimal(s, 6), lower_bound: floorDecimal(lower), witness_c: c.map((v) => (v.isZero() ? "0" : floorDecimal(v))),
        witness_x: x.map((v) => v.toNumber()), support: model.axes.filter((_, i) => !c[i].isZero()), feasible, pullback_consistent: gain.eq(chartGain), interior: c.every((v) => v.le(model.rho.div(new Q(4n)))) };
    }
    const rows = [];
    for (let k = 0; k < budget.steps; k++) {
      const s = Q.parse(Math.pow(10, -k / 2).toExponential(5));
      const row = certifyPoint(best(s.toNumber()), s);
      row.s_value = String(s.toNumber());
      rows.push(row);
      if (rows.length >= budget.need && rows.slice(-budget.need).every((r) => r.lower_bound !== "0")) break;
    }
    const series = [];
    for (let i = rows.length - 1; i >= 0; i--) { if (rows[i].lower_bound === "0") { if (series.length) break; continue; } series.unshift(rows[i]); }
    const slopes = (ser) => {
      const pts = ser.map((p) => [Math.log10(Number(p.s_value)), log10Q(Q.parse(p.lower_bound))]);
      const sl = pts.slice(1).map((p, i) => (p[1] - pts[i][1]) / (p[0] - pts[i][0]));
      const tail = sl.slice(-3).sort((a, b) => a - b);
      return [pts, tail.length ? tail[Math.floor(tail.length / 2)] : null];
    };
    const verdicts = predictions.map((pr) => {
      const [pts, measured] = slopes(series);
      const out = { id: pr.id, label: pr.label, gamma: String(pr.gamma) };
      if (measured == null || series.length < 3) return Object.assign(out, { verdict: "insufficient" });
      const g = pr.gamma.toNumber(), tol = Math.max(0.15, 0.1 * g);
      const ratios = pts.map(([a, b]) => b - g * a), tail = ratios.slice(-4), growth = tail[tail.length - 1] - tail[0];
      const rising = tail.every((v, i) => i === 0 || v > tail[i - 1]);
      if (measured < g - tol && rising && growth >= 0.2) Object.assign(out, { verdict: "contradicted", detail: `certified lower bounds grow like s^${+measured.toPrecision(3)}, faster than s^${out.gamma}: L(s)/s^γ rises by a factor of 10^${growth.toFixed(1)} as s decreases` });
      else if (Math.abs(measured - g) <= tol) Object.assign(out, { verdict: "consistent", detail: `local slopes approach ${measured.toFixed(3)} (prediction ${g.toFixed(3)})` });
      else Object.assign(out, { verdict: "inconclusive", detail: measured > g ? `lower bounds decay like s^${+measured.toPrecision(3)}; a lower bound below the predicted order may only mean the search missed the optimum` : `slopes near ${measured.toFixed(3)} but the ratio to s^γ has not separated yet` });
      out.ratio_growth_decades = +growth.toFixed(3);
      if (pr.coefficient) out.coefficient_ratio = +(Math.pow(10, ratios[ratios.length - 1]) / pr.coefficient).toFixed(6);
      return out;
    });
    const smallest = series.length ? series[series.length - 1] : rows[rows.length - 1];
    const [, measured] = series.length >= 2 ? slopes(series) : [null, null];
    return { status: "complete", method: "log-coordinate face search; witnesses certified by exact rational evaluation in P", budget: budgetName, rows,
      series_length: series.length, measured_exponent: measured == null ? null : +measured.toFixed(4), positive_gain_found: rows.some((r) => r.lower_bound !== "0"),
      support_at_smallest_s: smallest ? smallest.support : [], boundary_dominated: !!smallest && !smallest.interior,
      all_witnesses_feasible: rows.every((r) => r.feasible), pullback_consistent: rows.every((r) => r.pullback_consistent), verdicts };
  }

  global.GitCalc = Object.assign(global.GitCalc || {}, {
    Q, floorDecimal, log10Q, parseExpression, parseSystem, evalQ, curvature, transport, centered, polyText, monomialText, exps, key, wdeg,
    pconst, pvar, padd, pscale, pmul, ppow, pevalQ, dot, solveQ, vertexEnum, isBounded, combinations, LINKS, ORDER, link,
    localize, analyze, faceTable, envelope, curvedReduction, ambientAxes, measure, NonPolynomial,
  });
})(typeof globalThis !== "undefined" ? globalThis : this);
