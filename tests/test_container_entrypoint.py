"""Only the mounted state directory may be prepared by the brief root initializer."""

import importlib.util
import os
from pathlib import Path
import pytest


def module():
    spec = importlib.util.spec_from_file_location(
        "container_entrypoint", Path(__file__).parents[1] / "scripts/container_entrypoint.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_only_state_directory_fd_is_changed_without_recursing(tmp_path, monkeypatch):
    m = module()
    state = tmp_path / "state"
    state.mkdir()
    child = state / "existing"
    child.write_bytes(b"preserve")
    before = child.stat()
    calls = []
    monkeypatch.setattr(m, "STATE_DIR", state)
    monkeypatch.setattr(
        os, "fchown", lambda fd, uid, gid: calls.append(("owner", os.fstat(fd).st_ino, uid, gid))
    )
    monkeypatch.setattr(os, "fchmod", lambda fd, mode: calls.append(("mode", os.fstat(fd).st_ino, mode)))
    m.prepare_state()
    assert calls[0] == ("owner", state.stat().st_ino, 10001, 10001)
    assert calls[1][0:2] == ("mode", state.stat().st_ino)
    assert child.read_bytes() == b"preserve" and child.stat().st_uid == before.st_uid


def test_symlinked_state_directory_is_rejected_before_ownership_changes(tmp_path, monkeypatch):
    m = module()
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "state"
    link.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(m, "STATE_DIR", link)
    called = []
    monkeypatch.setattr(os, "fchown", lambda *args: called.append(args))
    with pytest.raises(OSError):
        m.prepare_state()
    assert called == []
