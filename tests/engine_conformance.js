// Runs the gitcalculator's browser engine on jobs read from stdin, for
// tests/test_gitcalculator.py, which compares the answers with the Python
// implementation. Usage: node tests/engine_conformance.js < jobs.json
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const web = path.join(__dirname, "..", "gitcalculator", "web");
for (const file of ["engine.js", "modes.js"]) {
  vm.runInThisContext(fs.readFileSync(path.join(web, file), "utf8"), { filename: file });
}
const G = globalThis.GitCalc;

function run(job) {
  if (job.mode === "solve") {
    const r = G.solve(job.request, { budget: "quick" });
    const curved = r.alternatives.curved_reduction;
    return {
      status: r.certificate.status, q_star: r.certificate.q_star ?? null, gamma: r.certificate.gamma ?? null,
      links: r.signature.certificate.links, curved: curved && curved.status === "licensed" ? curved.gamma : null,
      ambient: r.alternatives.ambient_axes ? r.alternatives.ambient_axes.gamma : null,
    };
  }
  if (job.mode === "sheet") return { markdown: G.sheet(job.receipt, job.options || {}) };
  if (job.mode === "solve-sheet") return { markdown: G.sheet(G.solve(job.request, { budget: "quick" }), job.options || {}) };
  if (job.mode === "geometry") {
    const g = G.solve(job.request, { measure: false }).geometry;
    return { n: g.n, vertex_index: g.vertex_index, active: g.active, simple: g.simple, facets: g.facets };
  }
  if (job.mode === "design") {
    const d = G.design(job.request);
    return { status: d.status, spectrum: (d.spectrum || []).map((e) => [e.q, e.gamma]),
      target: d.target ? [d.target.achievable, d.target.nearest_below, d.target.nearest_above] : null };
  }
  if (job.mode === "sweep") {
    const s = G.sweep(job.request);
    return { walls: s.walls.map((w) => [w.kind, w.at, w.value]), chambers: s.chambers.map((c) => [c.outcome.verdict, c.outcome.gamma]) };
  }
  const a = G.attack(job.request);
  return { base: [a.base.verdict, a.base.gamma], mutations: a.mutations.map((m) => [m.kind, m.outcome.verdict, m.outcome.gamma, m.changed]) };
}

const jobs = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(jobs.map((job) => {
  try { return run(job); } catch (error) { return { error: String(error && error.stack || error) }; }
})));
