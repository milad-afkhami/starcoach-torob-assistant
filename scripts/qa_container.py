"""Exercise the actual private image; never uses a cloud account or real provider token."""

import argparse
import hashlib
import json
import re
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
import httpx


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def main(state_storage="named", report_path=Path("docs/qa-evidence/container.json")):
    name = "torob-container-qa-" + secrets.token_hex(4)
    volume = name + "-state"
    port = 8653
    origin = f"http://127.0.0.1:{port}"
    report = {}
    with tempfile.TemporaryDirectory(prefix="torob-container-qa-") as temp:
        env = Path(temp) / "env"
        env.write_text(
            "PUBLIC_ORIGIN="
            + origin
            + "\nSESSION_SECRET="
            + secrets.token_hex(32)
            + "\nMODEL_WORKER_TOKEN="
            + secrets.token_hex(32)
            + "\n"
        )
        env.chmod(0o600)
        if state_storage == "root-bind":
            state = Path(temp) / "state"
            state.mkdir()
            docker(
                "run",
                "--rm",
                "--user",
                "0:0",
                "--entrypoint",
                "python",
                "-v",
                str(state) + ":/data",
                "starcoach-torob:local",
                "-c",
                "import os; os.chown('/data',0,0); os.chmod('/data',0o755)",
            )
            assert state.stat().st_uid == 0 and state.stat().st_mode & 0o777 == 0o755
            mount = str(state) + ":/data"
            report["root_bind_owner_before"] = state.stat().st_uid
        else:
            docker("volume", "create", volume)
            mount = volume + ":/data"
        report["state_storage"] = state_storage
        try:
            docker(
                "run",
                "-d",
                "--name",
                name,
                "--memory",
                "512m",
                "--cpus",
                "0.5",
                "--env-file",
                str(env),
                "-p",
                f"127.0.0.1:{port}:8000",
                "-v",
                mount,
                "starcoach-torob:local",
            )
            with httpx.Client(base_url=origin, headers={"origin": origin}, timeout=20) as client:
                for _ in range(40):
                    try:
                        if client.get("/readyz").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.5)
                else:
                    raise AssertionError("Container not ready")
                status = docker("exec", name, "cat", "/proc/1/status")
                identity = {
                    line.split(":", 1)[0]: line.split(":", 1)[1].split()
                    for line in status.splitlines()
                    if line.split(":", 1)[0] in ("Uid", "Gid", "NoNewPrivs", "CapEff")
                }
                assert identity["Uid"] == ["10001"] * 4 and identity["Gid"] == ["10001"] * 4
                assert identity["NoNewPrivs"] == ["1"] and int(identity["CapEff"][0], 16) == 0
                report["app_identity"] = identity
                permissions = docker(
                    "exec",
                    name,
                    "stat",
                    "-c",
                    "%u:%g %a",
                    "/app/data/catalogue.sqlite",
                    "/app/scripts/container_entrypoint.py",
                ).splitlines()
                assert permissions == ["0:0 444", "0:0 444"]
                report["immutable_runtime_file_permissions"] = permissions

                if state_storage == "root-bind":
                    assert state.stat().st_uid == 10001
                    report["root_bind_owner_after"] = state.stat().st_uid
                counts = json.loads(
                    docker(
                        "exec",
                        name,
                        "python",
                        "-c",
                        "import json,sqlite3; c=sqlite3.connect('file:/app/data/catalogue.sqlite?mode=ro',uri=True); print(json.dumps({t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['shops','products','offers']}))",
                    )
                )
                assert counts == {"shops": 6476, "products": 225903, "offers": 331506}
                report["catalogue_counts"] = counts
                root_page = client.get("/")
                assert root_page.status_code == 200
                assert (
                    hashlib.sha256(root_page.content).hexdigest()
                    == hashlib.file_digest(Path("frontend/dist/index.html").open("rb"), "sha256").hexdigest()
                )
                asset_hashes = {}
                for asset in re.findall(r'(?:src|href)="(/assets/[^" ]+)"', root_page.text):
                    delivered = client.get(asset)
                    assert delivered.status_code == 200
                    actual = hashlib.sha256(delivered.content).hexdigest()
                    with (Path("frontend/dist") / asset.lstrip("/")).open("rb") as local_asset:
                        assert actual == hashlib.file_digest(local_asset, "sha256").hexdigest()
                    asset_hashes[asset] = actual
                assert asset_hashes
                report["frozen_frontend_sha256"] = {
                    "index.html": hashlib.sha256(root_page.content).hexdigest(),
                    **asset_hashes,
                }
                assert client.post("/api/sessions").status_code == 200
                response = client.post(
                    "/api/missions",
                    json={
                        "product_id": "product_adfdc73bc839d15cd7754318",
                        "mode": "simulation",
                        "constraints": {
                            "max_price_toman": "40000000",
                            "visit_at": "2026-10-22T20:15:00+03:30",
                        },
                    },
                )
                assert response.status_code == 201, response.text
                result = response.json()
                mid = result["mission"]["id"]
                assert result["plan"]["primary"]["offer"]["price_toman"] == "39200000"
                for query in ["A07", "سامسونگ", "128", "Lenovo", "غیرواقعیقلمکالا"]:
                    assert client.post("/api/search", json={"query": query}).status_code == 200
                f = client.post(
                    f"/api/missions/{mid}/followups",
                    json={"offer_id": result["plan"]["primary"]["offer"]["offer_id"]},
                ).json()
                o = client.post(
                    f"/api/missions/{mid}/observations/preview",
                    json={"followup_id": f["id"], "expected_revision": 1, "kind": "unavailable"},
                ).json()
                reply = client.post(
                    f"/api/missions/{mid}/observations/{o['id']}/confirm", json={"expected_revision": 1}
                )
                assert reply.status_code == 200, reply.text
                assert reply.json()["delta"]["price_delta_toman"] == "300000"
                assert client.get("/api/capabilities").json()["model_available"] is False
                for path in [
                    "/data/catalogue.sqlite",
                    "/data/catalogue.sqlite.xz",
                    "/data/catalogue-build.json",
                    "/scripts/unpack_catalogue.py",
                    "/.env",
                    "/backend/torob/api.py",
                    "/data/state.sqlite",
                ]:
                    assert client.get(path).status_code == 404, path
                report["stats_before_restart"] = json.loads(
                    docker("stats", "--no-stream", "--format", "{{json .}}", name)
                )
                report["process_memory"] = docker(
                    "exec", name, "sh", "-c", "cat /proc/1/status | sed -n '/VmRSS/p;/VmHWM/p'"
                )
                report["catalogue_sha256"] = docker(
                    "exec", name, "sha256sum", "/app/data/catalogue.sqlite"
                ).split()[0]
                local = hashlib.file_digest(Path("data/catalogue.sqlite").open("rb"), "sha256").hexdigest()
                assert report["catalogue_sha256"] == local
                docker("restart", name)
                for _ in range(40):
                    try:
                        if client.get("/readyz").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.5)
                restored = client.get(f"/api/missions/{mid}").json()
                assert restored["mission"]["revision"] == 2
                assert restored["plan"]["primary"]["offer"]["price_toman"] == "39500000"
                report["persistence"] = True
                report["private_paths_404"] = True
                report["worker_offline_search_and_recovery"] = True
                report["image"] = json.loads(docker("image", "inspect", "starcoach-torob:local"))[0]["Id"]
                report["image_bytes"] = json.loads(docker("image", "inspect", "starcoach-torob:local"))[0][
                    "Size"
                ]
                report["catalogue_bytes"] = Path("data/catalogue.sqlite").stat().st_size
        except Exception:
            logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
            Path("docs/qa-evidence/container-failure.txt").write_text(logs.stdout + logs.stderr)
            print((logs.stdout + logs.stderr)[-4000:])
            raise
        finally:
            subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if state_storage == "root-bind":
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "--rm",
                        "--user",
                        "0:0",
                        "--entrypoint",
                        "sh",
                        "-v",
                        str(Path(temp)) + ":/qa",
                        "starcoach-torob:local",
                        "-c",
                        "rm -rf /qa/state",
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.run(
                    ["docker", "volume", "rm", volume], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
    dest = Path(report_path)
    dest.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-storage", choices=["named", "root-bind"], default="named")
    parser.add_argument("--report", type=Path, default=Path("docs/qa-evidence/container.json"))
    args = parser.parse_args()
    main(args.state_storage, args.report)
