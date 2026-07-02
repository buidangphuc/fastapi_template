from argparse import Namespace

from scripts.run_eval import DEFAULT_CASES, _run
from tests.factories import build_test_settings


async def test_eval_gate_passes_on_default_dataset(capsys):
    """Deterministic cases pass; judge cases skip without JUDGE_CHAT_MODEL."""
    exit_code = await _run(
        Namespace(cases=DEFAULT_CASES, min_score=0.8), settings=build_test_settings()
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert '"pass_rate": 1.0' in out
    assert '"skipped_judge": 2' in out


async def test_eval_gate_fails_below_threshold():
    exit_code = await _run(
        Namespace(cases=DEFAULT_CASES, min_score=1.01), settings=build_test_settings()
    )
    assert exit_code == 1
