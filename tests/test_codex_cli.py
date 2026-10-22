"""Risks: invalid outputs accepted, secrets inherited, expired work, orphan containers, unbounded spend."""

import json
import threading
import time

import pytest

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["HOLD"]},
        "evidence_ids": {"type": "array", "items": {"enum": ["fixture-1"]}},
        "reason_fa": {"type": "string"},
    },
    "required": ["action", "evidence_ids", "reason_fa"],
    "additionalProperties": False,
}
GOOD = {"action": "HOLD", "evidence_ids": ["fixture-1"], "reason_fa": "اطلاعات کافی نیست."}


def client(tmp_path, runner, **kw):
    from torob.codex_cli import CodexCliClient

    binary = tmp_path / "codex"
    binary.write_text("binary")
    auth = tmp_path / "auth.json"
    auth.write_text("{}")
    auth.chmod(0o600)
    return CodexCliClient(
        binary=binary,
        auth_file=auth,
        image="example@sha256:abc",
        gate_dir=tmp_path / "gate",
        runner=runner,
        **kw,
    )


def request(**kw):
    from torob.model_types import ModelRequest

    return ModelRequest(
        id="req-1",
        schema_id="probe",
        schema_version="1",
        prompt_version="1",
        evidence_ids=["fixture-1"],
        payload={"question": "سلام"},
        deadline_utc=time.time() + 60,
        **kw,
    )


def fake(value=GOOD, code=0, missing=False, raw=None):
    def run(spec, cancel):
        if not missing:
            spec.output.write_text(raw if raw is not None else json.dumps(value))
        return code

    return run


def test_schema_roundtrip_persian_and_provenance(tmp_path):
    c = client(tmp_path, fake())
    out = c.generate(request(), SCHEMA)
    assert out.value == GOOD and out.request_id == "req-1" and out.provider == "codex_cli"
    assert out.model == "gpt-6.1-sol" and out.elapsed_ms >= 0


@pytest.mark.parametrize(
    "value",
    [
        {**GOOD, "action": "BUY"},
        {**GOOD, "evidence_ids": ["invented"]},
        {**GOOD, "extra": True},
        {"action": "HOLD"},
        [],
        "answer",
        {**GOOD, "reason_fa": None},
    ],
)
def test_reject_invalid_schema(tmp_path, value):
    from torob.model_types import ModelError

    with pytest.raises(ModelError, match="invalid_output"):
        client(tmp_path, fake(value)).generate(request(), SCHEMA)


@pytest.mark.parametrize(
    "runner,code",
    [
        (fake(raw="{"), "invalid_output"),
        (fake(missing=True), "missing_output"),
        (fake(code=1), "provider_failed"),
        (fake(raw=" " * 17000), "oversized_output"),
    ],
)
def test_failed_process_or_output_fails_closed(tmp_path, runner, code):
    from torob.model_types import ModelError

    with pytest.raises(ModelError, match=code):
        client(tmp_path, runner).generate(request(), SCHEMA)


def test_expired_never_starts_process(tmp_path):
    from torob.model_types import ModelError

    calls = []
    c = client(tmp_path, lambda *args: calls.append(args))
    req = request().model_copy(update={"deadline_utc": time.time() - 1})
    with pytest.raises(ModelError, match="expired"):
        c.generate(req, SCHEMA)
    assert calls == []


def test_oversized_input_rejected_before_call(tmp_path):
    from torob.model_types import ModelError

    req = request().model_copy(update={"payload": {"text": "x" * 50000}})
    calls = []
    with pytest.raises(ModelError, match="oversized_input"):
        client(tmp_path, lambda *args: calls.append(args)).generate(req, SCHEMA)
    assert calls == []


def test_isolated_arguments_and_unique_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("LIARA_API_KEY", "secret-liara-sentinel")
    monkeypatch.setenv("MODEL_WORKER_TOKEN", "secret-relay-sentinel")
    captured = []

    def run(spec, cancel):
        captured.append(spec)
        assert all("sentinel" not in x for x in spec.args)
        assert "LIARA_API_KEY" not in spec.env and "MODEL_WORKER_TOKEN" not in spec.env
        assert "--read-only" in spec.args and "--cap-drop=ALL" in spec.args
        assert not any("docker.sock" in x for x in spec.args)
        assert "--ignore-user-config" in spec.args and "--output-schema" in spec.args
        spec.output.write_text(json.dumps(GOOD))
        return 0

    c = client(tmp_path, run)
    c.generate(request(), SCHEMA)
    c.generate(request(), SCHEMA)
    assert captured[0].output != captured[1].output
    assert not captured[0].output.exists() and not captured[1].output.exists()


def test_budget_survives_client_restart_and_counts_failures(tmp_path):
    from torob.model_types import ModelError

    calls = []

    def bad(spec, cancel):
        calls.append(spec)
        return 1

    for _ in range(2):
        with pytest.raises(ModelError, match="provider_failed"):
            client(tmp_path, bad, limit=2).generate(request(), SCHEMA)
    with pytest.raises(ModelError, match="budget_exhausted"):
        client(tmp_path, bad, limit=2).generate(request(), SCHEMA)
    assert len(calls) == 2


def test_rolling_budget_boundary(tmp_path):
    from torob.codex_cli import ModelGate
    from torob.model_types import ModelError

    gate = ModelGate(tmp_path / "gate", limit=2)
    with gate.claim(now=100):
        pass
    with gate.claim(now=101):
        pass
    with pytest.raises(ModelError, match="budget_exhausted"), gate.claim(now=86499):
        pass
    with gate.claim(now=86500):
        pass
    with pytest.raises(ModelError, match="budget_exhausted"), gate.claim(now=86500):
        pass


def test_concurrent_gate_refuses_second_and_symlinks(tmp_path):
    from torob.codex_cli import ModelGate
    from torob.model_types import ModelError

    gate = ModelGate(tmp_path / "gate")
    with gate.claim(now=100), pytest.raises(ModelError, match="busy"), gate.claim(now=100):
        pass
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path / "gate", target_is_directory=True)
    with pytest.raises(ModelError, match="unsafe_gate"):
        ModelGate(alias)


def test_precanceled_never_starts(tmp_path):
    from torob.model_types import ModelError

    cancel = threading.Event()
    cancel.set()
    calls = []
    with pytest.raises(ModelError, match="canceled"):
        client(tmp_path, lambda *a: calls.append(a)).generate(request(), SCHEMA, cancel)
    assert not calls


def test_schema_does_not_allow_remote_reference(tmp_path):
    from torob.model_types import ModelError

    with pytest.raises(ModelError, match="invalid_schema"):
        client(tmp_path, fake()).generate(request(), {"$ref": "https://bad.invalid/schema"})


def test_runtime_timeout_removes_child_and_cleans_up(tmp_path):
    import sys

    from torob.codex_cli import ProcessSpec, run_isolated
    from torob.model_types import ModelError

    marker = tmp_path / "cleaned"
    spec = ProcessSpec(
        [sys.executable, "-c", "import time; time.sleep(20)"],
        [sys.executable, "-c", f'from pathlib import Path; Path({str(marker)!r}).write_text("cleaned")'],
        {"PATH": "/usr/bin:/bin"},
        "",
        tmp_path / "result",
        0.15,
    )
    started = time.monotonic()
    with pytest.raises(ModelError, match="timeout"):
        run_isolated(spec, threading.Event())
    assert marker.read_text() == "cleaned" and time.monotonic() - started < 3


def test_runtime_cancel_during_running_process(tmp_path):
    import sys

    from torob.codex_cli import ProcessSpec, run_isolated
    from torob.model_types import ModelError

    marker = tmp_path / "cleaned"
    cancel = threading.Event()
    spec = ProcessSpec(
        [sys.executable, "-c", "import time; time.sleep(20)"],
        [sys.executable, "-c", f'from pathlib import Path; Path({str(marker)!r}).write_text("cleaned")'],
        {"PATH": "/usr/bin:/bin"},
        "",
        tmp_path / "result",
        10,
    )
    timer = threading.Timer(0.15, cancel.set)
    timer.start()
    try:
        with pytest.raises(ModelError, match="canceled"):
            run_isolated(spec, cancel)
    finally:
        timer.cancel()
    assert marker.read_text() == "cleaned"


def test_late_runner_result_never_accepted(tmp_path):
    from torob.model_types import ModelError

    def late(spec, cancel):
        time.sleep(0.05)
        spec.output.write_text(json.dumps(GOOD))
        return 0

    req = request().model_copy(update={"deadline_utc": time.time() + 0.02})
    with pytest.raises(ModelError, match="expired"):
        client(tmp_path, late).generate(req, SCHEMA)


def test_global_budget_cannot_be_reset_by_new_request_ids(tmp_path):
    from torob.model_types import ModelError

    calls = []

    def run(spec, cancel):
        calls.append(1)
        spec.output.write_text(json.dumps(GOOD))
        return 0

    c = client(tmp_path, run)
    for n in range(100):
        c.generate(request().model_copy(update={"id": f"session-{n}"}), SCHEMA)
    with pytest.raises(ModelError, match="budget_exhausted"):
        client(tmp_path, run).generate(request(), SCHEMA)
    assert len(calls) == 100


@pytest.mark.parametrize("deadline", [float("nan"), float("inf")])
def test_nonfinite_deadline_rejected(deadline):
    from pydantic import ValidationError
    from torob.model_types import ModelRequest

    value = request().model_dump()
    value["deadline_utc"] = deadline
    with pytest.raises(ValidationError):
        ModelRequest.model_validate(value)


def test_reservation_before_claim_does_not_spend_until_generation(tmp_path):
    from torob.model_types import ModelError

    c = client(tmp_path, fake(), limit=1)
    with c.gate.reserve() as permit:
        with pytest.raises(ModelError, match="busy"):
            with c.gate.claim(time.time()):
                pass
    assert not (tmp_path / "gate" / "starts.json").exists()
    with c.gate.reserve() as permit:
        assert c.generate(request(), SCHEMA, permit=permit).value == GOOD
    with pytest.raises(ModelError, match="invalid_reservation"):
        c.generate(request(), SCHEMA, permit=permit)


@pytest.mark.parametrize("kind", ["permissions", "lock_symlink", "ledger_symlink", "corrupt_ledger"])
def test_gate_rejects_unsafe_or_corrupt_state(tmp_path, kind):
    from torob.codex_cli import ModelGate
    from torob.model_types import ModelError

    root = tmp_path / "gate"
    root.mkdir(mode=0o700)
    if kind == "permissions":
        root.chmod(0o755)
    elif kind == "lock_symlink":
        (root / "worker.lock").symlink_to(tmp_path / "other")
    elif kind == "ledger_symlink":
        (root / "starts.json").symlink_to(tmp_path / "other")
    else:
        (root / "starts.json").write_text("{invalid")
    with pytest.raises(ModelError):
        with ModelGate(root).claim(100):
            pass


def test_bad_schema_and_missing_auth_fail_before_provider(tmp_path):
    from torob.model_types import ModelError

    c = client(tmp_path, fake())
    with pytest.raises(ModelError, match="invalid_schema"):
        c.generate(request(), {"type": "not-a-json-schema-type"})
    c.auth_file.unlink()
    with pytest.raises(ModelError, match="runtime_unavailable"):
        c.generate(request(), SCHEMA)


def test_missing_process_binary_still_runs_cleanup(tmp_path):
    from torob.codex_cli import ProcessSpec, run_isolated
    from torob.model_types import ModelError
    import sys

    marker = tmp_path / "cleanup"
    spec = ProcessSpec(
        ["/no-such-binary"],
        [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"],
        {},
        "",
        tmp_path / "result",
        1,
    )
    with pytest.raises(ModelError, match="runtime_unavailable"):
        run_isolated(spec, threading.Event())
    assert marker.exists()


def test_unverified_container_cleanup_is_an_error(tmp_path):
    import sys
    from torob.codex_cli import ProcessSpec, run_isolated
    from torob.model_types import ModelError

    spec = ProcessSpec(
        [sys.executable, "-c", "pass"],
        [sys.executable, "-c", "pass"],
        {},
        "",
        tmp_path / "result",
        1,
        verify_cleanup_args=[sys.executable, "-c", 'print("container-still-present")'],
    )
    with pytest.raises(ModelError, match="cleanup_failed"):
        run_isolated(spec, threading.Event())


def test_cleanup_uncertainty_latches_off_future_model_starts(tmp_path):
    from torob.model_types import ModelError

    calls = []

    def uncertain(spec, cancel):
        calls.append(1)
        raise ModelError("cleanup_failed")

    c = client(tmp_path, uncertain)
    with pytest.raises(ModelError, match="cleanup_failed"):
        c.generate(request(), SCHEMA)
    with pytest.raises(ModelError, match="runtime_fault"):
        client(tmp_path, uncertain).generate(request(), SCHEMA)
    assert calls == [1]


def test_cancel_waits_for_container_creation_before_cleanup(tmp_path, monkeypatch):
    import subprocess
    from torob.codex_cli import ProcessSpec, run_isolated
    from torob.model_types import ModelError

    cancel = threading.Event()
    created = [False]
    cleanup_after_create = []

    class Process:
        pid = 999999
        returncode = 0

        def poll(self):
            return 0

    def popen(*args, **kw):
        cancel.set()
        return Process()

    def run(args, **kw):
        if args[1] == "create":
            created[0] = True
            cancel.set()
        if args[1] == "rm":
            cleanup_after_create.append(created[0])
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(subprocess, "run", run)
    spec = ProcessSpec(
        ["docker", "run", "--rm", "--name", "owned", "-i", "image", "exec"],
        ["docker", "rm", "-f", "owned"],
        {},
        "prompt",
        tmp_path / "output",
        1,
        verify_cleanup_args=["docker", "ps"],
    )
    with pytest.raises(ModelError, match="canceled"):
        run_isolated(spec, cancel)
    assert created[0] and cleanup_after_create == [True]


def test_uncertain_creation_latches_cleanup_failure_even_if_absence_snapshot_is_empty(tmp_path, monkeypatch):
    import subprocess
    from torob.codex_cli import ProcessSpec, run_isolated
    from torob.model_types import ModelError

    def run(args, **kw):
        if args[1] == "create":
            raise subprocess.TimeoutExpired(args, 1)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **kw: (_ for _ in ()).throw(OSError("unexpected old launch"))
    )
    spec = ProcessSpec(
        ["docker", "run", "--rm", "--name", "owned", "-i", "image", "exec"],
        ["docker", "rm", "-f", "owned"],
        {},
        "prompt",
        tmp_path / "output",
        1,
        verify_cleanup_args=["docker", "ps"],
    )
    with pytest.raises(ModelError, match="cleanup_failed"):
        run_isolated(spec, threading.Event())
