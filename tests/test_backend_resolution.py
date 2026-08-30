"""
Backend resolution: the endpoint is chosen by configuration, never by vendor.

The discriminating test is `test_any_endpoint_needs_no_preset`. A backend that
is only nominally provider-agnostic still routes through a table of known
vendors, so an unlisted endpoint silently falls back to a default. Here an
arbitrary base URL and an arbitrary model id must survive resolution untouched,
with no preset and no key variable naming that vendor: that is what makes the
`--api` flag a generator interface rather than a dependency on one supplier.

`test_paid_default_is_diagnosed` pins the other half. A key alone resolves to a
placeholder model that costs money, so a good key can fail the `--check`
round-trip with `402 Payment Required`. That message has to name the model as
the cause, or the next person reads it as a bad key and re-pastes it.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import json

from categorical_polytope.loop_closure import (
    LOOP_SYSTEM_PROMPT,
    LearnerDiagramReport,
    _KEY_ENVS,
    _OPENAI_BASE,
    _OPENROUTER_BASE,
    PRESETS,
    _explain_failure,
    resolve_backend,
)

# Every variable that can steer resolution, cleared before each test so the
# developer's own shell cannot make one of these pass or fail.
_VARS = (*_KEY_ENVS, "LOOP_API_MODEL", "LOOP_API_BASE", "LOOP_API_PRESET",
         "OPENAI_BASE_URL", "POLYTOPE_API_REASONING")


class BackendResolutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {v: os.environ.pop(v, None) for v in _VARS}

    def tearDown(self) -> None:
        for v, old in self._saved.items():
            if old is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = old

    # --- offline stays the default ------------------------------------
    def test_no_key_resolves_to_nothing(self) -> None:
        """Without a key there is no endpoint: callers keep the scripted arc."""
        self.assertIsNone(resolve_backend())
        self.assertIsNone(resolve_backend(model="acme/model", preset="nemotron"))

    # --- the discriminating test --------------------------------------
    def test_any_endpoint_needs_no_preset(self) -> None:
        """An unlisted vendor is reachable with nothing but a key and two args."""
        os.environ["LOOP_API_KEY"] = "k"
        b = resolve_backend(model="acme/llm-7b", base_url="https://llm.acme.test/v1")
        assert b is not None
        self.assertEqual(b.model, "acme/llm-7b")
        self.assertEqual(b.base_url, "https://llm.acme.test/v1")
        self.assertEqual(b.descriptor(), "acme/llm-7b@llm.acme.test")
        # OpenRouter-only request fields must not be sent to a host that
        # never agreed to accept them.
        self.assertFalse(b.supports_extras)

    def test_key_choice_picks_the_matching_base(self) -> None:
        os.environ["OPENAI_API_KEY"] = "k"
        b = resolve_backend()
        assert b is not None
        self.assertEqual(b.base_url, _OPENAI_BASE)
        self.assertEqual(b.key_env, "OPENAI_API_KEY")

        del os.environ["OPENAI_API_KEY"]
        os.environ["OPENROUTER_API_KEY"] = "k"
        b = resolve_backend()
        assert b is not None
        self.assertEqual(b.base_url, _OPENROUTER_BASE)

    def test_explicit_argument_beats_env_beats_preset(self) -> None:
        """Precedence, most specific first. A preset is only a fallback."""
        os.environ["OPENROUTER_API_KEY"] = "k"
        os.environ["LOOP_API_PRESET"] = "nemotron"
        from_preset = resolve_backend()
        assert from_preset is not None
        self.assertEqual(from_preset.model, PRESETS["nemotron"][1])

        os.environ["LOOP_API_MODEL"] = "acme/from-env"
        from_env = resolve_backend()
        assert from_env is not None
        self.assertEqual(from_env.model, "acme/from-env")

        from_arg = resolve_backend(model="acme/from-arg")
        assert from_arg is not None
        self.assertEqual(from_arg.model, "acme/from-arg")

    def test_unknown_preset_falls_back_instead_of_raising(self) -> None:
        """A typo in --preset must not lose a run that a key could still serve."""
        os.environ["OPENROUTER_API_KEY"] = "k"
        b = resolve_backend(preset="no-such-preset")
        assert b is not None
        self.assertEqual(b.base_url, _OPENROUTER_BASE)
        self.assertTrue(b.model)

    def test_every_preset_names_a_model_and_a_base(self) -> None:
        os.environ["OPENROUTER_API_KEY"] = "k"
        for name in PRESETS:
            with self.subTest(preset=name):
                b = resolve_backend(preset=name)
                assert b is not None
                self.assertTrue(b.model.strip(), f"{name} resolves to no model")
                self.assertTrue(b.base_url.startswith("https://"))

    def test_reasoning_block_is_forced_by_capability_not_vendor(self) -> None:
        """
        The override wins over every preset in both directions.

        Asserted against the presets themselves rather than a hardcoded
        expectation: which model wants a `reasoning` block is a fact about
        that model and changes when the table is retuned, but the escape
        hatch has to keep working for a model nobody listed.
        """
        os.environ["OPENROUTER_API_KEY"] = "k"
        for name in PRESETS:
            with self.subTest(preset=name):
                self.assertEqual(
                    resolve_backend(preset=name).reasoning, PRESETS[name][2]
                )
                os.environ["POLYTOPE_API_REASONING"] = "1"
                self.assertTrue(resolve_backend(preset=name).reasoning)
                os.environ["POLYTOPE_API_REASONING"] = "0"
                self.assertFalse(resolve_backend(preset=name).reasoning)
                del os.environ["POLYTOPE_API_REASONING"]

        # ...including for an endpoint that no preset names.
        os.environ["POLYTOPE_API_REASONING"] = "1"
        b = resolve_backend(model="acme/llm-7b", base_url="https://llm.acme.test/v1")
        assert b is not None
        self.assertTrue(b.reasoning)


class LooseReplyTest(unittest.TestCase):
    """
    The learner is an untrusted generator, so a sloppy reply is expected input.

    The discriminating case is `test_range_echoed_as_value`: a small model that
    copies the schema's own range notation back as a value used to take down
    the whole turn with `could not convert string to float: '1-0'`. Salvaging
    the leading number keeps the turn, and `clamped()` bounds whatever comes
    out - a reply cannot push a coordinate off the polytope by being malformed.
    """

    def test_range_echoed_as_value(self) -> None:
        r = LearnerDiagramReport.from_json(
            '{"lam":"1-0","sigma":"0-1","b":2,"k":3,'
            '"confusion":"0-1","topic":"coexp","quote":"hm"}'
        ).clamped()
        self.assertEqual(r.lam, 1.0)
        self.assertEqual(r.sigma, 0.0)
        self.assertEqual(r.topic, "coexp")

    def test_quoted_numbers_and_code_fences(self) -> None:
        fenced = '''Sure! Here you go:
```json
{"lam":0.6,"sigma":"0.3","b":1.2,"k":2.5,"confusion":0.5,"topic":"t","quote":"q"}
```'''
        r = LearnerDiagramReport.from_json(fenced).clamped()
        self.assertAlmostEqual(r.lam, 0.6)
        self.assertAlmostEqual(r.sigma, 0.3)

    def test_unsalvageable_field_uses_its_default(self) -> None:
        r = LearnerDiagramReport.from_json(
            '{"lam":"high","sigma":0.4,"b":1,"k":2,'
            '"confusion":0.3,"topic":"t","quote":"q"}'
        ).clamped()
        self.assertEqual(r.lam, 0.5)
        self.assertAlmostEqual(r.sigma, 0.4)

    def test_a_reply_that_is_not_an_object_still_falls_back(self) -> None:
        """Salvage has a floor: nothing object-shaped means no report at all."""
        with self.assertRaises(ValueError):
            LearnerDiagramReport.from_json("[1, 2, 3]")

    def test_prompt_shows_valid_json(self) -> None:
        """
        The example in the system prompt must itself parse.

        This is what broke: the schema was written `{"lam":0-1,...}`, so a
        model copying its shape emitted a range where a number belonged.
        """
        line = next(
            ln for ln in LOOP_SYSTEM_PROMPT.splitlines()
            if ln.startswith('{"lam"')
        )
        parsed = json.loads(line)
        for key in ("lam", "sigma", "b", "k", "confusion"):
            self.assertIsInstance(parsed[key], (int, float), f"{key} is not a number")


class FailureExplanationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {v: os.environ.pop(v, None) for v in _VARS}
        os.environ["OPENROUTER_API_KEY"] = "k"

    def tearDown(self) -> None:
        for v, old in self._saved.items():
            if old is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = old

    # --- the discriminating test --------------------------------------
    def test_paid_default_is_diagnosed(self) -> None:
        """402 has to point at the model; the key it came with is usually fine."""
        backend = resolve_backend()
        assert backend is not None
        said = _explain_failure("HTTPError: HTTP Error 402: Payment Required", backend)
        self.assertIn(backend.model, said)
        self.assertIn("--model", said)
        # The raw error is kept: the hint annotates it, never replaces it.
        self.assertIn("402", said)

    def test_rejected_key_and_missing_model_read_differently(self) -> None:
        backend = resolve_backend(model="acme/gone")
        assert backend is not None
        unauthorized = _explain_failure("HTTP Error 401: Unauthorized", backend)
        missing = _explain_failure("HTTP Error 404: Not Found", backend)
        self.assertIn("key", unauthorized)
        self.assertIn("acme/gone", missing)
        self.assertNotEqual(unauthorized, missing)

    def test_parse_failure_absolves_the_key(self) -> None:
        """The model answered; saying "typo in the key" would send you backwards."""
        backend = resolve_backend()
        assert backend is not None
        said = _explain_failure(
            "ValueError: could not convert string to float: '1-0'", backend
        )
        self.assertIn("key and endpoint are fine", said)

    def test_unrecognized_error_is_passed_through_unchanged(self) -> None:
        backend = resolve_backend()
        assert backend is not None
        raw = "URLError: <urlopen error timed out>"
        self.assertEqual(_explain_failure(raw, backend), raw)


if __name__ == "__main__":
    unittest.main()
