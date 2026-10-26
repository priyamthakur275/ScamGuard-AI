#!/usr/bin/env python3
"""One command to run ScamGuard locally on Windows, macOS or Linux.

    python run.py          (Windows: py run.py also works)

First run: creates backend/.venv, installs the Python packages, installs the
frontend's npm packages and writes local config files. Later runs skip what is
already done (packages are reinstalled only when requirements change).
Then it starts the backend on http://127.0.0.1:8000 and the frontend on
http://localhost:3000, waits until both answer and opens the browser.
Press Ctrl+C once to stop both.

Options:
    --setup-only      install everything, don't start the servers
    --no-browser      don't open the browser
    --backend-only    start only the API
"""
from __future__ import annotations

import hashlib
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"
LOGS = ROOT / ".run-logs"
WINDOWS = os.name == "nt"
BACKEND_PORT, FRONTEND_PORT = 8000, 3000
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"


# ---------------------------------------------------------------- output ----
def _c(code: str, text: str) -> str:
    if WINDOWS and not os.environ.get("WT_SESSION") and not os.environ.get("TERM_PROGRAM"):
        return text  # old cmd.exe: no colours
    return f"\033[{code}m{text}\033[0m"


def info(msg: str) -> None:
    print(_c("36", "==> ") + msg, flush=True)


def ok(msg: str) -> None:
    print(_c("32", "OK  ") + msg, flush=True)


def fail(msg: str, hint: str = "") -> None:
    print(_c("31", "ERROR ") + msg, flush=True)
    if hint:
        print("      " + hint, flush=True)
    sys.exit(1)


# ---------------------------------------------------------------- checks ----
def check_python() -> None:
    v = sys.version_info
    if v < (3, 10) or v >= (3, 15):
        fail(f"Python {v.major}.{v.minor} found; ScamGuard needs Python 3.10 to 3.14.",
             "Install Python 3.12 or 3.13 from https://www.python.org/downloads/ and run this again.")
    ok(f"Python {v.major}.{v.minor}.{v.micro}")


def npm_cmd() -> str:
    exe = shutil.which("npm.cmd" if WINDOWS else "npm") or shutil.which("npm")
    if not exe:
        fail("Node.js / npm was not found.",
             "Install the LTS version from https://nodejs.org (it includes npm), reopen VS Code, and run this again.")
    return exe


def check_node() -> None:
    node = shutil.which("node")
    if not node:
        fail("Node.js was not found.", "Install the LTS version from https://nodejs.org, reopen VS Code, and run this again.")
    out = subprocess.run([node, "-v"], capture_output=True, text=True).stdout.strip()
    major = int(out.lstrip("v").split(".")[0]) if out else 0
    if major < 18:
        fail(f"Node {out} found; the frontend needs Node 18 or newer.", "Install the LTS version from https://nodejs.org.")
    ok(f"Node {out}")


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) != 0


def http_ok(url: str, timeout: float = 3) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def pids_on_port(port: int) -> list[int]:
    """Best-effort: the process ids listening on a local port."""
    pids: set[int] = set()
    try:
        if WINDOWS:
            out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3].upper() == "LISTENING":
                    pids.add(int(parts[4]))
        else:
            if shutil.which("lsof"):
                out = subprocess.run(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
                pids.update(int(p) for p in out.split() if p.isdigit())
            if not pids and shutil.which("ss"):
                import re
                out = subprocess.run(["ss", "-ltnpH", f"sport = :{port}"], capture_output=True, text=True).stdout
                pids.update(int(p) for p in re.findall(r"pid=(\d+)", out))
            if not pids and shutil.which("fuser"):
                out = subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True).stdout
                pids.update(int(p) for p in out.split() if p.isdigit())
            if not pids and Path("/proc/net/tcp").exists():
                pids.update(_procfs_listeners(port))
    except Exception:
        pass
    pids.discard(os.getpid())
    return sorted(pids)


def _is_scamguard(port: int) -> bool:
    """True only when the program on the port is an earlier ScamGuard server."""
    try:
        if port == BACKEND_PORT:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=4) as r:
                return b'"status"' in r.read(200)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=20) as r:
            return b"ScamGuard" in r.read(20000)
    except Exception:
        pass
    # A frozen server doesn't answer; recognise it by how it was started.
    for pid in pids_on_port(port):
        cmd = _cmdline(pid).lower()
        if "app_service.main" in cmd or "scamguard" in cmd or ("next" in cmd and (" dev" in cmd or "start-server" in cmd or "next-server" in cmd)):
            return True
    return False


def _cmdline(pid: int) -> str:
    try:
        if WINDOWS:
            out = subprocess.run(["powershell", "-NoProfile", "-Command",
                                  f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
                                 capture_output=True, text=True, timeout=15).stdout
            return out.strip()
        p = Path(f"/proc/{pid}/cmdline")
        if p.exists():
            return p.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        return subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""


def _procfs_listeners(port: int) -> set[int]:
    """Linux without lsof/ss/fuser: map the listening socket's inode to its process."""
    inodes: set[str] = set()
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            for line in Path(table).read_text().splitlines()[1:]:
                f = line.split()
                if len(f) > 9 and f[3] == "0A" and int(f[1].rsplit(":", 1)[1], 16) == port:
                    inodes.add(f[9])
        except Exception:
            pass
    found: set[int] = set()
    if not inodes:
        return found
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            for fd in (proc / "fd").iterdir():
                link = os.readlink(fd)
                if link.startswith("socket:[") and link[8:-1] in inodes:
                    found.add(int(proc.name))
                    break
        except Exception:
            continue
    return found


def free_port(port: int, what: str) -> None:
    """A server left running from an earlier session is the most common reason
    the app looks 'busy' or 'down'. Stop whatever is listening on the port."""
    if port_free(port):
        return
    if not _is_scamguard(port):
        fail(f"Port {port} is used by another program (not ScamGuard).",
             f"Close that program, then run this again. ScamGuard needs ports {BACKEND_PORT} and {FRONTEND_PORT}.")
    pids = pids_on_port(port)
    info(f"Port {port} is held by an old {what} that is still running; stopping it")
    for pid in pids:
        try:
            if WINDOWS:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
    for _ in range(20):
        if port_free(port):
            ok(f"Port {port} is free")
            return
        time.sleep(0.5)
    fail(f"Port {port} is still in use by another program.",
         f"Close the other program (or the old terminal running ScamGuard) and run this again. PIDs: {pids or 'unknown'}")


# ----------------------------------------------------------------- setup ----
def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if WINDOWS else "bin/python")


def write_local_config() -> None:
    env = BACKEND / ".env"
    if not env.exists():
        import secrets
        env.write_text(
            "APP_ENV=development\nDEBUG=false\n"
            f"SECRET_KEY={secrets.token_urlsafe(48)}\n"
            "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000\n",
            encoding="utf-8",
        )
        ok("Created backend/.env (local settings, private key, local SQLite database)")
    else:
        # Repair settings from older versions that break local runs.
        text = env.read_text(encoding="utf-8")
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("ML_SERVICE_URL=")]
        if not any(ln.strip().startswith("APP_ENV=") for ln in lines):
            lines.insert(0, "APP_ENV=development")
        new = "\n".join(lines) + "\n"
        if new != text:
            env.write_text(new, encoding="utf-8")
            ok("Updated backend/.env for local use")
    fe = FRONTEND / ".env.local"
    want = f"APP_SERVICE_URL={BACKEND_URL}\n"
    if not fe.exists() or "APP_SERVICE_URL=http://localhost:8000" in fe.read_text(encoding="utf-8"):
        fe.write_text(want, encoding="utf-8")
        ok("Pointed the frontend at the local backend (frontend/.env.local)")


def setup_backend() -> None:
    if not venv_python().exists():
        info("Creating the Python environment backend/.venv (first run only)")
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    reqs = [BACKEND / "requirements.txt", BACKEND / "requirements-ml.txt"]
    digest = hashlib.sha256(b"".join(p.read_bytes() for p in reqs) + sys.version.encode()).hexdigest()
    stamp = VENV / ".scamguard-reqs"
    if stamp.exists() and stamp.read_text().strip() == digest:
        ok("Backend packages already installed")
        return
    info("Installing backend packages (first run takes 1-4 minutes)")
    LOGS.mkdir(exist_ok=True)
    py = str(venv_python())
    with open(LOGS / "pip.log", "w", encoding="utf-8") as log:
        subprocess.run([py, "-m", "pip", "install", "--upgrade", "pip"], stdout=log, stderr=subprocess.STDOUT)
        r = subprocess.run([py, "-m", "pip", "install", "--prefer-binary", "-r", str(reqs[0]), "-r", str(reqs[1])],
                           stdout=log, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        tail = (LOGS / "pip.log").read_text(encoding="utf-8", errors="replace").splitlines()[-15:]
        print("\n".join(tail))
        fail("Installing backend packages failed (full log: .run-logs/pip.log).",
             "Check your internet connection. If it mentions a compiler or 'Microsoft Visual C++', use Python 3.12 or 3.13.")
    stamp.write_text(digest)
    ok("Backend packages installed")


def setup_frontend() -> None:
    nm = FRONTEND / "node_modules"
    lock = FRONTEND / "package-lock.json"
    stamp = nm / ".scamguard-lock"
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    if nm.exists() and stamp.exists() and stamp.read_text().strip() == digest:
        ok("Frontend packages already installed")
        return
    info("Installing frontend packages (first run takes 1-3 minutes)")
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / "npm.log", "w", encoding="utf-8") as log:
        r = subprocess.run([npm_cmd(), "ci", "--no-audit", "--no-fund"], cwd=FRONTEND, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        tail = (LOGS / "npm.log").read_text(encoding="utf-8", errors="replace").splitlines()[-15:]
        print("\n".join(tail))
        fail("Installing frontend packages failed (full log: .run-logs/npm.log).",
             "Close any running 'npm run dev', delete frontend/node_modules and run this again.")
    stamp.write_text(digest)
    ok("Frontend packages installed")


# ------------------------------------------------------------------- run ----
def wait_for(url: str, proc: subprocess.Popen, seconds: int, name: str, log: Path) -> None:
    for _ in range(seconds):
        if http_ok(url):
            return
        if proc.poll() is not None:
            tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]
            print("\n".join(tail))
            fail(f"The {name} stopped while starting (log: {log.relative_to(ROOT)}).")
        time.sleep(1)
    fail(f"The {name} did not answer within {seconds} s (log: {log.relative_to(ROOT)}).")


def start(backend_only: bool, browser: bool) -> None:
    free_port(BACKEND_PORT, "ScamGuard backend")
    if not backend_only:
        free_port(FRONTEND_PORT, "ScamGuard frontend")
    LOGS.mkdir(exist_ok=True)
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if WINDOWS else 0
    procs: list[subprocess.Popen] = []

    def stop(*_):
        info("Stopping ScamGuard")
        for p in procs:
            try:
                if WINDOWS:
                    subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
                else:
                    os.killpg(p.pid, signal.SIGTERM)
            except Exception:
                pass
        sys.exit(0)

    be_log = LOGS / "backend.log"
    info(f"Starting the backend on {BACKEND_URL}")
    procs.append(subprocess.Popen(
        [str(venv_python()), "-m", "uvicorn", "app_service.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        cwd=BACKEND, env=env, stdout=open(be_log, "w", encoding="utf-8"), stderr=subprocess.STDOUT,
        creationflags=flags, start_new_session=not WINDOWS))
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    wait_for(f"{BACKEND_URL}/api/v1/health", procs[0], 120, "backend", be_log)
    ok(f"Backend is up: {BACKEND_URL}/docs")

    if not backend_only:
        fe_log = LOGS / "frontend.log"
        info(f"Starting the frontend on {FRONTEND_URL} (first start compiles for ~30 s)")
        procs.append(subprocess.Popen(
            [npm_cmd(), "run", "dev", "--", "-p", str(FRONTEND_PORT)],
            cwd=FRONTEND, env={**env, "APP_SERVICE_URL": BACKEND_URL},
            stdout=open(fe_log, "w", encoding="utf-8"), stderr=subprocess.STDOUT,
            creationflags=flags, start_new_session=not WINDOWS))
        wait_for(FRONTEND_URL, procs[1], 180, "frontend", fe_log)
        if not http_ok(f"{FRONTEND_URL}/backend-api/api/v1/health", timeout=30):
            fail("The frontend is up but cannot reach the backend through its proxy.",
                 f"Check frontend/.env.local says APP_SERVICE_URL={BACKEND_URL}, then run this again.")
        ok(f"ScamGuard is running: {FRONTEND_URL}")
        if browser:
            try:
                webbrowser.open(FRONTEND_URL)
            except Exception:
                pass
    print(_c("32", "\nEverything is running. Leave this terminal open; press Ctrl+C to stop.\n"
             "Logs: .run-logs/backend.log and .run-logs/frontend.log\n"), flush=True)
    try:
        while True:
            for p in procs:
                if p.poll() is not None:
                    name = "backend" if p is procs[0] else "frontend"
                    log = LOGS / f"{name}.log"
                    print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]))
                    print(_c("31", f"The {name} stopped unexpectedly (log: .run-logs/{name}.log)."))
                    stop()
            time.sleep(2)
    except KeyboardInterrupt:
        stop()


def main() -> None:
    args = set(sys.argv[1:])
    os.chdir(ROOT)
    print(_c("35", "\n  ScamGuard local runner\n"))
    check_python()
    if "--backend-only" not in args:
        check_node()
    write_local_config()
    setup_backend()
    if "--backend-only" not in args:
        setup_frontend()
    if "--setup-only" in args:
        ok("Setup complete. Start with: python run.py")
        return
    start("--backend-only" in args, "--no-browser" not in args)


if __name__ == "__main__":
    main()
