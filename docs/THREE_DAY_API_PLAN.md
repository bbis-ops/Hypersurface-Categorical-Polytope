# Three-day continuous API verification event

## Objective

Keep `stealth/ox-alpha` generating adversarial V.7--V.14 candidates for 72 hours,
with high reasoning and a 15,000-token completion cap per 32-candidate round.
Every parse-valid candidate is retained; only candidates satisfying a theorem's
hypotheses count toward its verification denominator.

## Continuous schedule

- **Hours 0--6: calibration and verifier hardening.** Drive every law to at
  least 64 in-scope outcomes. Independently shrink strength scales for exponent
  mismatches and improve numerical searches when model candidates expose them.
- **Hours 6--36: breadth.** Repeated 32-candidate rounds prioritize the law with
  the smallest in-scope denominator. Every fourth cycle is round-robin so no law
  starves.
- **Hours 36--60: hard-case replication.** A live numerical survivor gets every
  fourth batch devoted to coefficient, scale, and functional mutations. The
  original and all variants remain in the counterexample ledger.
- **Hours 60--70: saturation and global-search pressure.** Continue breadth but
  prioritize V.11 and V.13 when their denominators lag, because narrow peaks and
  off-corner maxima most strongly stress numerical guards.
- **Hours 70--72: freeze while still generating.** Generation continues until
  the deadline. The final local pass rewrites the certificate and counterexample
  ledger from the immutable checkpoint.

## Reliability and accounting

- One API request is active at a time to avoid the known free-tier 429 mode.
- High-reasoning responses normally occupy the API for minutes; the 75-second
  interval is measured from request start, so it adds no delay when inference
  already lasts longer.
- A heartbeat identifies the active theorem and phase. A failed subprocess backs
  off for 30 seconds and resumes; successful rounds launch the next round
  immediately.
- Adjudicators are versioned. A theorem-local repair replays that law's retained
  corpus and appends status transitions to each record's history; it does not
  recompute unaffected laws or erase the model's original attack.
- Raw responses and provider-reported prompt/completion/total token usage append
  to `experiments/verification_api_raw.jsonl`.
- `verification_campaign.json` is the resumable corpus;
  `verification_counterexamples.json` is the live survivor ledger;
  `verification_guard_failures.json` preserves attacks that broke a retired
  numerical guard but not the theorem;
  `VERIFICATION_CERTIFICATE.md` reports honest parse-valid and in-scope counts.

## Start

```powershell
$env:OPENROUTER_API_KEY = [Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY','User')
python experiments/run_72h_verification.py --hours 72 --batch-size 32 --max-tokens 15000 --model stealth/ox-alpha
```

The scheduler resumes an unfinished event from `verification_72h_state.json`.
Delete or archive that state only when intentionally starting a separate event.
