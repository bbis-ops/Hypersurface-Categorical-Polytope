import os
import subprocess
import sys
from pathlib import Path

from categorical_polytope.api_rate_limit import (
    load_rate_state,
    note_success,
    note_throttle,
    reserve_request,
    seconds_until_allowed,
)


def test_shared_rate_state_throttles_and_recovers():
    path = Path(__file__).resolve().parents[1] / "experiments" / "_test_api_rate_state.json"
    path.unlink(missing_ok=True)
    try:
        reserve_request(path, base_interval=60, batch_size=32, now=1000)
        assert seconds_until_allowed(path, now=1001) == 59

        state = note_throttle(path, base_interval=60, batch_size=32, now=1010)
        assert state["recommended_batch_size"] == 16
        assert state["consecutive_throttles"] == 1
        assert seconds_until_allowed(path, now=1010) >= 120

        state = note_throttle(path, base_interval=60, batch_size=16, now=1020)
        assert state["recommended_batch_size"] == 8
        assert state["interval_seconds"] >= 240

        for offset in range(2000, 2800, 100):
            state = note_success(path, base_interval=60, configured_batch_size=32, now=offset)
        assert state["consecutive_throttles"] == 0
        assert state["recommended_batch_size"] == 10
        assert state["recovery_batch_ceiling"] == 13
        assert load_rate_state(path)["total_successes"] == 8
    finally:
        path.unlink(missing_ok=True)
        path.with_suffix(path.suffix + ".lock").unlink(missing_ok=True)


def test_concurrent_reservations_receive_distinct_slots():
    path = (
        Path(__file__).resolve().parents[1]
        / "experiments"
        / f"_test_concurrent_rate_state_{os.getpid()}.json"
    )
    path.unlink(missing_ok=True)
    marker = path.with_suffix(".start")
    marker.unlink(missing_ok=True)
    code = (
        "import sys,time; from pathlib import Path; "
        "from categorical_polytope.api_rate_limit import reserve_request; "
        "path=Path(sys.argv[1]); marker=Path(sys.argv[2]); "
        "\nwhile not marker.exists(): time.sleep(0.001)\n"
        "reserve_request(path,base_interval=60,batch_size=8,now=1000)"
    )
    workers = [
        subprocess.Popen([sys.executable, "-c", code, str(path), str(marker)])
        for _ in range(2)
    ]
    try:
        marker.touch()
        for worker in workers:
            assert worker.wait(timeout=15) == 0
        assert load_rate_state(path)["next_allowed_epoch"] == 1120
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.terminate()
                worker.wait()
        marker.unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        path.with_suffix(path.suffix + ".lock").unlink(missing_ok=True)


def test_success_cannot_erase_a_later_reserved_slot():
    path = Path(__file__).resolve().parents[1] / "experiments" / "_test_reserved_slot.json"
    path.unlink(missing_ok=True)
    try:
        reserve_request(path, base_interval=60, batch_size=8, now=1000)
        reserve_request(path, base_interval=60, batch_size=8, now=1000)

        state = note_success(
            path, base_interval=60, configured_batch_size=8, now=1001
        )

        assert state["next_allowed_epoch"] == 1120
    finally:
        path.unlink(missing_ok=True)
        path.with_suffix(path.suffix + ".lock").unlink(missing_ok=True)
