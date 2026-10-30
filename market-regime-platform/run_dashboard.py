"""Start the local artifact-backed API and Vite UI together, on Windows/macOS/Linux."""
from __future__ import annotations
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def port_available(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('0.0.0.0', port))
        return True
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the PROFNITT research dashboard')
    parser.add_argument('--backend-port', type=int, default=8000)
    parser.add_argument('--frontend-port', type=int, default=5173)
    parser.add_argument('--check', action='store_true', help='check prerequisites without starting servers')
    args = parser.parse_args()
    npm = shutil.which('npm')
    missing = [p for p in ('fastapi', 'uvicorn', 'pandas', 'regime_backtester') if importlib.util.find_spec(p) is None]
    if missing:
        print('Missing Python packages:', ', '.join(missing), '\nRun: python -m pip install -e ".[dashboard,dev]"', file=sys.stderr)
        return 1
    if not npm or not (ROOT/'frontend'/'node_modules').is_dir():
        print('Node/npm or frontend dependencies are missing. Install Node 20+, then run: cd frontend && npm ci', file=sys.stderr)
        return 1
    if not (ROOT/'data'/'raw'/'nifty_index.csv').is_file():
        print('Expected supplied dataset at data/raw/nifty_index.csv', file=sys.stderr)
        return 1
    if args.check:
        print('Prerequisites OK. Dashboard: http://localhost:5173 · API: http://localhost:8000')
        return 0
    if not (1 <= args.backend_port <= 65535 and 1 <= args.frontend_port <= 65535):
        print('Ports must be between 1 and 65535.', file=sys.stderr); return 1
    if args.backend_port == args.frontend_port or any(not port_available(p) for p in (args.backend_port,args.frontend_port)):
        print('A requested port is already in use (or ports are identical). Stop the existing server or select other ports.', file=sys.stderr)
        return 1
    env=os.environ.copy();env['REGIME_API_TARGET']=f'http://127.0.0.1:{args.backend_port}'
    api=[sys.executable,'-m','uvicorn','backend.app:app','--host','0.0.0.0','--port',str(args.backend_port)]
    npm_cmd=([os.environ.get('COMSPEC','cmd.exe'),'/c',npm] if os.name=='nt' else [npm])
    front=npm_cmd+['run','dev','--','--host','0.0.0.0','--port',str(args.frontend_port)]
    children=[]
    def stop_signal(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop_signal)
    launch_options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    try:
        print(f'Dashboard: http://localhost:{args.frontend_port}\nAPI docs: http://localhost:{args.backend_port}/docs',flush=True)
        print('Historical research only. This local server has no authentication; do not expose it publicly. Press Ctrl+C to stop.\n',flush=True)
        children.append(subprocess.Popen(api,cwd=ROOT,env=env,**launch_options))
        children.append(subprocess.Popen(front,cwd=ROOT/'frontend',env=env,**launch_options))
        while True:
            for p in children:
                if p.poll() is not None:
                    print(f'A server exited with status {p.returncode}; stopping both.',file=sys.stderr)
                    return p.returncode or 1
            time.sleep(.5)
    except KeyboardInterrupt:
        print('\nStopping dashboard...')
        return 0
    finally:
        for p in children:
            if p.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                else:
                    try: os.killpg(p.pid, signal.SIGTERM)
                    except ProcessLookupError: pass
        for p in children:
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == 'nt': p.kill()
                else:
                    try: os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                p.wait()


if __name__ == '__main__':
    raise SystemExit(main())
