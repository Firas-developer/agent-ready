# main.py - FIXED VERSION
import sys
import asyncio
import socket
import subprocess
from pathlib import Path

# 🔴 CRITICAL FIX: Python 3.13 + Windows + Playwright subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("✓ Set Windows ProactorEventLoop policy for Python 3.13")

# NOW import everything else
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()


# ─── Ripple sidecar bootstrap ──────────────────────────────────────────────
RIPPLE_SIDECAR_PORT = 7780
RIPPLE_SIDECAR_DIR = Path(__file__).resolve().parent.parent / "ripple-sidecar"


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_ripple_sidecar() -> None:
    """Spawn the Node.js Ripple sidecar if it isn't already running.

    Survives uvicorn --reload because we never kill it on shutdown and skip
    spawning when port 7780 already answers.
    """
    if _port_in_use(RIPPLE_SIDECAR_PORT):
        print(f"✓ Ripple sidecar already running on :{RIPPLE_SIDECAR_PORT}")
        return

    server_js = RIPPLE_SIDECAR_DIR / "server.js"
    if not server_js.exists():
        print(f"⚠ Ripple sidecar not found at {server_js} — impact will use Python fallback")
        return

    try:
        creationflags = 0
        if sys.platform == "win32":
            # Detach so it survives uvicorn reloads / Ctrl-C
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS
        subprocess.Popen(
            ["node", "server.js"],
            cwd=str(RIPPLE_SIDECAR_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags if sys.platform == "win32" else 0,
            close_fds=True,
        )
        print(f"✓ Spawned Ripple sidecar (node server.js) on :{RIPPLE_SIDECAR_PORT}")
    except FileNotFoundError:
        print("⚠ `node` not found on PATH — install Node.js to enable tree-sitter impact")
    except Exception as e:
        print(f"⚠ Could not spawn Ripple sidecar: {e}")


start_ripple_sidecar()

# DEBUG: Print environment variables
print("\n" + "="*60)
print("🔍 Environment Variables Check:")
print("="*60)
print(f"ANTHROPIC_FOUNDRY__API_KEY present: {bool(os.getenv('ANTHROPIC_FOUNDRY__API_KEY'))}")
print(f"ANTHROPIC_FOUNDRY__API_KEY length: {len(os.getenv('ANTHROPIC_FOUNDRY__API_KEY', ''))}")
print(f"ANTHROPIC_FOUNDRY__RESOURCE: {os.getenv('ANTHROPIC_FOUNDRY__RESOURCE')}")
print(f"ANTHROPIC_FOUNDRY__DEPLOYMENT_NAME: {os.getenv('ANTHROPIC_FOUNDRY__DEPLOYMENT_NAME')}")
print("="*60 + "\n")

# from routers import agent_ready, visualizer, playwright_testing, testing
from routers import agent_ready, visualizer, testing
app = FastAPI(title="Pipeline UI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_ready.router)
app.include_router(visualizer.router)
# app.include_router(playwright_testing.router)
app.include_router(testing.router)

@app.get("/")
def root():
    return {"status": "ok", "message": "Pipeline UI Backend"}

@app.get("/health")
def health():
    return {"status": "healthy"}
