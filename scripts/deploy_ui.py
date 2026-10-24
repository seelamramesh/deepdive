"""Stage and promote a DeepDive image while preserving data and rollback."""

import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import urllib.request


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("release_dir")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    release = Path(args.release_dir).resolve()
    original = json.loads(docker("inspect", "deepdive"))[0]
    mounts = original["Mounts"]
    data_mount = next(item for item in mounts if item["Destination"] == "/app/data")
    data_dir = Path(data_mount["Source"])
    backup_dir = release / "validation-data"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / "deepdive.db"
    with sqlite3.connect(f"file:{data_dir / 'deepdive.db'}?mode=ro", uri=True) as source:
        states = source.execute("SELECT id,current_state FROM runs WHERE current_state NOT IN ('END','FAILED')").fetchall()
        if states:
            raise RuntimeError("Active or interrupted runs require review before deployment: " + repr(states))
        with sqlite3.connect(backup_path) as target:
            source.backup(target)
    with sqlite3.connect(backup_path) as backup:
        if backup.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("Backup integrity check failed")
        count = backup.execute("SELECT count(*) FROM runs").fetchone()[0]
    print(f"Consistent backup verified: {count} runs", flush=True)
    network = original["HostConfig"]["NetworkMode"]
    descriptor, env_path = tempfile.mkstemp(prefix="deepdive-ui-env-")
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as env_file:
            env_file.write("\n".join(original["Config"]["Env"]))
        candidate = "deepdive-ui-candidate-" + time.strftime("%Y%m%d%H%M%S")
        if subprocess.run(["docker", "container", "inspect", candidate], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            raise RuntimeError("Candidate already exists; inspect it before restarting deployment")
        common = ["--env-file", env_path, "--env", "DEEPDIVE_DB_PATH=/app/data/deepdive.db", "--network", network]
        docker("run", "-d", "--name", candidate, *common, "-v", f"{backup_dir}:/app/data", "--label", "traefik.enable=false", args.image)
        try:
            subprocess.run(["docker", "exec", candidate, "python", "-m", "pytest", "-q", "-p", "no:cacheprovider"], check=True)
            for attempt in range(30):
                result = subprocess.run(["docker", "exec", candidate, "python", "-c", "import urllib.request,json; d=json.load(urllib.request.urlopen('http://localhost:8000/health')); assert d['db_ok'] and d['status']=='ok'; r=json.load(urllib.request.urlopen('http://localhost:8000/runs')); assert len(r)>0; html=urllib.request.urlopen('http://localhost:8000/').read().decode(); assert '/assets/' in html"], capture_output=True)
                if result.returncode == 0:
                    break
                time.sleep(2)
            else:
                raise RuntimeError("Candidate readiness failed")
            print("Candidate backend tests, persisted runs, DB readiness, SPA shell passed", flush=True)
        finally:
            docker("stop", candidate)
        if not args.promote:
            return
        # A research request may have arrived while candidate checks ran.
        with sqlite3.connect(f"file:{data_dir / 'deepdive.db'}?mode=ro", uri=True) as source:
            states = source.execute("SELECT id,current_state FROM runs WHERE current_state NOT IN ('END','FAILED')").fetchall()
            if states:
                raise RuntimeError("New active runs detected; production promotion withheld: " + repr(states))
        rollback_name = "deepdive-rollback-ui-" + time.strftime("%Y%m%d%H%M%S")
        docker("stop", "deepdive")
        docker("rename", "deepdive", rollback_name)
        try:
            labels = []
            for key, value in original["Config"].get("Labels", {}).items():
                # Keep routing configuration, but let the new image identify itself.
                if key.startswith("org.opencontainers.image."):
                    continue
                labels.extend(["--label", f"{key}={value}"])
            docker("run", "-d", "--name", "deepdive", "--restart", "unless-stopped", *common, "-v", f"{data_dir}:/app/data", *labels, args.image)
            for attempt in range(40):
                try:
                    with urllib.request.urlopen("https://deepdive.srv1493167.hstgr.cloud/health", timeout=5) as response:
                        health = json.load(response)
                    with urllib.request.urlopen("https://deepdive.srv1493167.hstgr.cloud/", timeout=5) as response:
                        html = response.read().decode()
                    if health.get("db_ok") and "/assets/" in html:
                        break
                except Exception:
                    pass
                time.sleep(2)
            else:
                raise RuntimeError("Public readiness failed")
            print(f"Deployment verified; rollback={rollback_name}; backup={backup_path}", flush=True)
        except Exception:
            subprocess.run(["docker", "rm", "-f", "deepdive"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            docker("rename", rollback_name, "deepdive")
            docker("start", "deepdive")
            raise
    finally:
        os.unlink(env_path)


if __name__ == "__main__":
    main()
