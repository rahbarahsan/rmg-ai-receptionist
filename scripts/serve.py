"""One command to bring the agent online in a chosen language.

    uv run python scripts/serve.py          # English (default)
    uv run python scripts/serve.py bn        # Bangla / Banglish
    uv run python scripts/serve.py en        # English

It does the whole dance for you, so you never touch the tunnel URL by hand:
  1. makes sure the FastAPI app is running on :8000 (starts it if not),
  2. opens a cloudflared tunnel and reads its public URL automatically,
  3. runs scripts/sync_agent.py for the locale with that URL, so the agent's
     order tools point at your app and the phone number answers in that language,
  4. holds the tunnel + app open. Press Ctrl+C to stop and take it down.

Re-run with the other locale to flip the number between English and Bangla — no
URL to copy, no env vars to remember.

cloudflared is found on PATH, else $CLOUDFLARED_PATH, else .tools/cloudflared.exe.
Install it once with `winget install --id Cloudflare.cloudflared` to have it on PATH.
"""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from types import FrameType

import httpx

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "agent" / "config" / "agent.config.json"
APP_PORT = 8000
APP_URL = f"http://localhost:{APP_PORT}"
TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def log(msg: str = "") -> None:
    """Print and flush immediately, so progress shows even when stdout is a pipe."""
    print(msg, flush=True)


def die(msg: str) -> None:
    print(f"serve: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def pick_locale() -> str:
    locales: dict[str, object] = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get(
        "locales", {}
    )
    arg = next((a for a in sys.argv[1:] if not a.startswith("-")), "en")
    if arg not in locales:
        die(f"unknown locale '{arg}' - config has: {', '.join(locales) or '(none)'}")
    return arg


def find_cloudflared() -> str:
    on_path = shutil.which("cloudflared")
    if on_path:
        return on_path
    env_path = os.environ.get("CLOUDFLARED_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    local = ROOT / ".tools" / "cloudflared.exe"
    if local.exists():
        return str(local)
    die(
        "cloudflared not found. Install it with `winget install --id Cloudflare.cloudflared`, "
        "or set CLOUDFLARED_PATH to the binary."
    )
    raise AssertionError  # unreachable, keeps mypy happy


def app_is_up() -> bool:
    try:
        return httpx.get(f"{APP_URL}/health", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def wait_until(predicate: Callable[[], bool], timeout: float, label: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(1)
    die(f"timed out waiting for {label}")


def start_app() -> subprocess.Popen[bytes] | None:
    """Start uvicorn only if the app isn't already answering. Returns the process we
    started (to stop later), or None if we're reusing one that was already up."""
    if app_is_up():
        log(f"app: already running on :{APP_PORT} (reusing)")
        return None
    log(f"app: starting on :{APP_PORT} ...")
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app.main:app", "--port", str(APP_PORT)],
        cwd=ROOT,
    )
    wait_until(app_is_up, timeout=40, label="the app to answer /health")
    log("app: up")
    return proc


def start_tunnel(cloudflared: str) -> tuple[subprocess.Popen[str], str]:
    """Launch cloudflared and read its public URL out of the output. A reader thread
    keeps draining the pipe so the process never blocks on a full buffer."""
    log("tunnel: opening ...")
    proc = subprocess.Popen(
        [cloudflared, "tunnel", "--url", APP_URL],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    url_box: dict[str, str] = {}

    def reader() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            if "url" not in url_box:
                m = TUNNEL_RE.search(line)
                if m:
                    url_box["url"] = m.group(0)

    threading.Thread(target=reader, daemon=True).start()
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if "url" in url_box:
            log(f"tunnel: {url_box['url']}")
            return proc, url_box["url"]
        if proc.poll() is not None:
            die("cloudflared exited before printing a URL")
        time.sleep(0.5)
    proc.terminate()
    die("timed out waiting for the tunnel URL")
    raise AssertionError  # unreachable


def run_sync(locale: str, url: str) -> None:
    log(f"sync: pushing '{locale}' agent + tools at {url} ...")
    env = {**os.environ, "LANGUAGE_LOCALE": locale, "PUBLIC_BASE_URL": url}
    result = subprocess.run(["uv", "run", "python", "scripts/sync_agent.py"], cwd=ROOT, env=env)
    if result.returncode != 0:
        die("sync_agent.py failed - see its output above")


def main() -> None:
    locale = pick_locale()
    cloudflared = find_cloudflared()

    app_proc = start_app()
    tunnel_proc, url = start_tunnel(cloudflared)
    run_sync(locale, url)

    log()
    log("=" * 60)
    log(f"  LIVE - the number now answers in: {locale.upper()}")
    log(f"  Tunnel URL : {url}")
    log(f"  App        : {APP_URL}")
    log("  Dashboard  : run  uv run streamlit run dashboard/main.py")
    log("  Ctrl+C to stop.")
    log("=" * 60)

    stopping = threading.Event()

    def shutdown(_sig: int, _frame: FrameType | None) -> None:
        stopping.set()

    signal.signal(signal.SIGINT, shutdown)
    try:
        while not stopping.is_set():
            if tunnel_proc.poll() is not None:
                log("\ntunnel: exited - stopping.")
                break
            time.sleep(1)
    finally:
        log("stopping tunnel ...")
        tunnel_proc.terminate()
        if app_proc is not None:
            log("stopping app ...")
            app_proc.terminate()
        log("done.")


if __name__ == "__main__":
    main()
