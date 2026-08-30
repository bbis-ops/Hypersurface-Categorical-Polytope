import importlib.util
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "experiments" / "run_72h_verification.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_72h_verification_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(directory):
    return {
        path.name: (path.stat().st_mtime_ns, path.read_bytes())
        for path in sorted(directory.iterdir())
    }


def run_dry(module, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run_72h_verification.py", "--dry-run", "--hours", "1"])
    module.main()


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    # Stand-in for a campaign caught mid-flight, with the module's state paths redirected here.
    module = load_runner()
    deadline = datetime.now(timezone.utc) + timedelta(hours=6)
    fixtures = {
        "EVENT": (tmp_path / "verification_72h_state.json", {
            "status": "running", "started_utc": "2026-08-24T12:57:59.436222+00:00",
            "deadline_utc": deadline.isoformat(), "cycle": 88, "pid": 31456,
            "attempts_by_law": {"V.11": 27, "V.14": 12}, "last_exit_code": 0,
        }),
        "HEARTBEAT": (tmp_path / "verification_72h_heartbeat.json", {
            "utc": "2026-08-25T01:27:52.511143+00:00", "cycle": 88, "phase": "shared_rate_cooldown",
        }),
        "RATE_STATE": (tmp_path / "verification_api_rate_state.json", {
            "version": 1, "next_allowed_epoch": 0.0, "recommended_batch_size": 4,
        }),
        "CORPUS": (tmp_path / "verification_campaign.json", {"records": [
            {"rule_id": "V.11", "status": "counterexample"},
            {"rule_id": "V.11", "status": "verified"},
            {"rule_id": "V.7", "status": "verified"},
        ]}),
    }
    for name, (path, payload) in fixtures.items():
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        monkeypatch.setattr(module, name, path)
    monkeypatch.setenv("LOOP_API_KEY", "unit-test-key")
    return module


def test_dry_run_leaves_campaign_state_untouched(campaign, tmp_path, monkeypatch, capsys):
    before = snapshot(tmp_path)
    run_dry(campaign, monkeypatch)
    # No rewrites, no truncations, and no .tmp siblings left behind.
    assert snapshot(tmp_path) == before
    event = json.loads(campaign.EVENT.read_text(encoding="utf-8"))
    assert event["cycle"] == 88 and event["status"] == "running"
    out = capsys.readouterr().out
    assert "run_verification_campaign.py" in out
    assert "--api" in out


def test_dry_run_reports_rate_cooldown_instead_of_sleeping_through_it(campaign, tmp_path, monkeypatch, capsys):
    campaign.RATE_STATE.write_text(json.dumps({
        "version": 1, "next_allowed_epoch": time.time() + 600.0, "recommended_batch_size": 4,
    }, indent=2), encoding="utf-8")
    before = snapshot(tmp_path)
    started = time.monotonic()
    run_dry(campaign, monkeypatch)
    assert time.monotonic() - started < 10.0
    assert snapshot(tmp_path) == before
    out = capsys.readouterr().out
    assert "would wait" in out
    assert "run_verification_campaign.py" in out


def test_only_the_dry_run_writer_is_inert(campaign, tmp_path):
    probe = tmp_path / "writer_probe.json"
    campaign._write(probe, {"cycle": 1})
    assert json.loads(probe.read_text(encoding="utf-8")) == {"cycle": 1}
    campaign._noop_write(probe, {"cycle": 2})
    assert json.loads(probe.read_text(encoding="utf-8")) == {"cycle": 1}
