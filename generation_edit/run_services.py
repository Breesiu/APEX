import asyncio
import os
import sys
import subprocess
import uvicorn
import httpx
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
import signal

# Configuration
APEX_PORT = 8001
POSTERGEN_PORT = 8002
PROXY_PORT = 8000

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # F:\APEX
APEX_DIR = BASE_DIR / "APEX"
POSTERGEN_DIR = BASE_DIR / "PosterGen"
GEN_EDIT_DIR = Path(__file__).resolve().parent

# Subprocesses
processes = {}

def start_apex():
    print(f"Starting APEX Backend on port {APEX_PORT}...")
    # APEX uses a script that accepts --port
    cmd = [sys.executable, "start_backend.py", "--port", str(APEX_PORT)]
    # We must run it from the APEX directory so relative paths work
    processes['apex'] = subprocess.Popen(
        cmd, 
        cwd=str(APEX_DIR),
        stdout=sys.stdout,
        stderr=sys.stderr
    )

def start_postergen():
    print(f"Starting PosterGen Backend on port {POSTERGEN_PORT}...")
    # Using our custom runner which sets up paths properly
    runner_script = GEN_EDIT_DIR / "postergen_runner.py"
    cmd = [sys.executable, str(runner_script)]
    processes['postergen'] = subprocess.Popen(
        cmd,
        cwd=str(GEN_EDIT_DIR),
        stdout=sys.stdout, 
        stderr=sys.stderr
    )

def cleanup():
    print("Shutting down services...")
    for name, proc in processes.items():
        if proc.poll() is None:
            print(f"Terminating {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        start_apex()
        start_postergen()
    except Exception as e:
        print(f"Failed to start services: {e}")
        cleanup()
        sys.exit(1)
        
    yield
    
    # Shutdown
    cleanup()

app = FastAPI(lifespan=lifespan)
client = httpx.AsyncClient()

@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()

async def forward_request(target_port: int, request: Request, path: str):
    url = f"http://localhost:{target_port}/{path}"
    if request.query_params:
        url += f"?{request.query_params}"
    
    # Exclude host header to let httpx/target handle it
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None) # Let httpx handle content length
    
    try:
        req = client.build_request(
            request.method,
            url,
            headers=headers,
            content=request.stream(),
            timeout=120.0
        )
        r = await client.send(req, stream=True)
        return StreamingResponse(
            r.aiter_raw(),
            status_code=r.status_code,
            headers=dict(r.headers),
            background=BackgroundTasks([r.aclose])
        )
    except Exception as e:
        print(f"Proxy error to port {target_port}: {e}")
        return {"error": f"Service unavailable: {str(e)}"}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy(request: Request, path: str):
    # Routing Logic
    # APEX handles /edit and /pptx
    if path.startswith("edit") or path.startswith("pptx"):
        target = APEX_PORT
    else:
        # Default to PosterGen for everything else (including /, /models, etc.)
        target = POSTERGEN_PORT
        
    return await forward_request(target, request, path)

if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    print(f"Starting Unified Proxy on port {PROXY_PORT}")
    print(f"APEX acts on {APEX_PORT}")
    print(f"PosterGen acts on {POSTERGEN_PORT}")
    print("Use Ctrl+C to stop all services.")
    
    # Install httpx if missing? 
    # Validated it acts as import.
    
    uvicorn.run(app, host="0.0.0.0", port=PROXY_PORT)
