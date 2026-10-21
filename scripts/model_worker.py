"""Run the outbound model worker with runtime-only credentials."""

import os
import signal
import threading
from pathlib import Path

from torob.codex_cli import CodexCliClient
from torob.model_worker import PullWorker


def main():
    model = CodexCliClient(
        binary=Path(os.environ["CODEX_BINARY_PATH"]),
        auth_file=Path(os.environ["CODEX_AUTH_FILE"]),
        image=os.environ["CODEX_IMAGE"],
        gate_dir=Path(f"/tmp/starcoach-codex-{os.getuid()}"),
        model=os.environ.get("MODEL_ID", "gpt-6.1-sol"),
    )
    worker = PullWorker(
        os.environ["MODEL_WORKER_BASE_URL"],
        os.environ["MODEL_WORKER_TOKEN"],
        model,
        allow_loopback_http=os.environ.get("MODEL_WORKER_LOOPBACK_TEST") == "1",
    )
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    worker.run(stop)


if __name__ == "__main__":
    main()
