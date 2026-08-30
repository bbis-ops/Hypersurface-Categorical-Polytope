#!/usr/bin/env python3
"""
Make ONE request to a backend and show exactly what came back.

The campaign's transport retries, paces, and degrades quietly, which is right
for a long run and useless for diagnosing a model that returns nothing. This
sends a single request with no retries and a short timeout, then prints the
status, the finish reason, the raw content, and the token usage.

    python experiments/probe_backend.py --preset nemotron
    python experiments/probe_backend.py --preset nemotron --no-reasoning
    python experiments/probe_backend.py --model nvidia/nemotron-3.5-lightning:free

Use it whenever a campaign prints a header and then stalls.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from categorical_polytope.loop_closure import resolve_backend  # noqa: E402

PROMPT = (
    'Reply with JSON only, no prose: '
    '{"candidates":[{"name":"a","args":"(\'a3\',)","why":"digit beside a run"},'
    '{"name":"b","args":"(\'aab7\',)","why":"digit after a run"}]}'
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--no-reasoning", action="store_true",
                    help="omit the reasoning block (isolates the null-content gotcha)")
    ap.add_argument("--no-json-mode", action="store_true",
                    help="omit response_format (some models reject it)")
    ap.add_argument("--show", type=int, default=600, help="characters of content to print")
    args = ap.parse_args()

    backend = resolve_backend(args.model, args.base_url, args.preset)
    if backend is None:
        print("no API key set: export LOOP_API_KEY / OPENROUTER_API_KEY / OPENAI_API_KEY",
              file=sys.stderr)
        return 2

    import os

    key = os.environ[backend.key_env].strip()
    body: dict = {
        "model": backend.model,
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0.7,
        "max_tokens": args.max_tokens,
    }
    if backend.supports_extras:
        if not args.no_json_mode:
            body["response_format"] = {"type": "json_object"}
        if backend.reasoning and not args.no_reasoning:
            body["reasoning"] = {"effort": "low", "exclude": True}

    print(f"backend      {backend.descriptor()}")
    print(f"key from     {backend.key_env}")
    print(f"sending      max_tokens={args.max_tokens} "
          f"response_format={'response_format' in body} "
          f"reasoning={'reasoning' in body}")
    print()

    req = urllib.request.Request(
        f"{backend.base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            status = resp.status
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:800]
        print(f"HTTP {exc.code}\n{detail}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    elapsed = time.monotonic() - started
    print(f"HTTP {status} in {elapsed:.1f}s")
    if not data.get("choices"):
        print("NO CHOICES -- provider error payload:")
        print(json.dumps(data, indent=2)[:1200])
        return 1

    choice = data["choices"][0]
    message = choice.get("message") or {}
    content = message.get("content")
    print(f"finish_reason  {choice.get('finish_reason')!r}")
    print(f"content type   {type(content).__name__}")
    print(f"content length {len(content) if isinstance(content, str) else 'n/a'}")
    usage = data.get("usage", {}) or {}
    print(f"usage          {json.dumps(usage)}")
    produced = int(usage.get("completion_tokens", 0) or 0)
    if produced and elapsed > 0:
        rate = produced / elapsed
        print(f"throughput     {rate:.0f} completion tokens/sec")
        # Generation is serial, so the completion cap IS the wall clock. This
        # is the number that should set --max-tokens, not the context window.
        for budget in (2000, 4000, 8000, 20000):
            print(f"   max_tokens={budget:<6} -> ~{budget / rate:.0f}s per request")
    for extra in ("reasoning", "reasoning_content", "reasoning_details"):
        if message.get(extra):
            value = message[extra]
            size = len(value) if isinstance(value, (str, list)) else "?"
            print(f"message.{extra}: present ({size})")
    print()

    if isinstance(content, str) and content.strip():
        print("--- content ---")
        print(content[: args.show])
        print()
        try:
            json.loads(content)
            print("VERDICT: parses as JSON. The transport should accept this.")
        except json.JSONDecodeError:
            print("VERDICT: content is present but not whole JSON. The campaign parser "
                  "salvages complete records from replies like this.")
        return 0

    print("VERDICT: EMPTY CONTENT. This is what stalls a campaign - the transport "
          "retries this 8 times, pacing 30s between attempts.")
    if "reasoning" in body:
        print("  Next: rerun with --no-reasoning. If content appears, the reasoning "
              "block is consuming the whole completion.")
    elif choice.get("finish_reason") == "length":
        print("  finish_reason is 'length': raise --max-tokens.")
    else:
        print("  Try --no-json-mode, or a different --model.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
