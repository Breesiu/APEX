import asyncio
import os
import sys
import subprocess
import uvicorn
import httpx
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
import signal
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
APEX_PORT = 8001
POSTERGEN_PORT = 8002
PROXY_PORT = 8000

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APEX_DIR = BASE_DIR / 'APEX'
POSTERGEN_DIR = BASE_DIR / 'PosterGen'
GEN_EDIT_DIR = Path(__file__).resolve().parent

# Load environment config
config_file = GEN_EDIT_DIR / 'env_config.json'
apex_env_name = 'Python.3.11' # Default
postergen_env_name = 'postergen_env' # Default
if config_file.exists():
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            apex_env_name = config.get('apex_env_name', apex_env_name)
            postergen_env_name = config.get('postergen_env_name', postergen_env_name)
    except Exception as e:
        print(f'Warning: Failed to load env_config.json: {e}')

# Subprocesses
processes = {}

def start_apex():
    print(f'Starting APEX Backend on port {APEX_PORT} using {apex_env_name}...')
    # APEX uses a script that accepts --port
    # 添加 --no-capture-output 以实时查看输出和错误
    cmd = ['conda', 'run', '--no-capture-output', '-n', apex_env_name, 'python', 'start_backend.py', '--port', str(APEX_PORT)]
    # We must run it from the APEX directory so relative paths work
    processes['apex'] = subprocess.Popen(
        cmd, 
        cwd=str(APEX_DIR),
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    print(f'  → APEX process started (PID: {processes["apex"].pid})')

def start_postergen():
    print(f'Starting PosterGen Backend on port {POSTERGEN_PORT} using {postergen_env_name}...')
    # Using our custom runner which sets up paths properly
    runner_script = GEN_EDIT_DIR / 'postergen_runner.py'
    # 添加 --no-capture-output 以实时查看输出和错误
    cmd = ['conda', 'run', '--no-capture-output', '-n', postergen_env_name, 'python', str(runner_script)]
    processes['postergen'] = subprocess.Popen(
        cmd,
        cwd=str(GEN_EDIT_DIR),
        stdout=sys.stdout, 
        stderr=sys.stderr
    )
    print(f'  → PosterGen process started (PID: {processes["postergen"].pid})')

def cleanup():
    print('\nShutting down services...')
    for name, proc in processes.items():
        if proc.poll() is None:
            print(f'Terminating {name}...')
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f'Force killing {name}...')
                proc.kill()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        start_apex()
        start_postergen()
        # 等待子进程启动
        print('\nWaiting for backend services to initialize...')
        await asyncio.sleep(3)
        
        # 检查子进程是否仍在运行
        for name, proc in processes.items():
            if proc.poll() is not None:
                print(f'ERROR: {name} process exited prematurely with code {proc.returncode}')
                cleanup()
                sys.exit(1)
        
        print('Backend services initialized successfully!\n')
    except Exception as e:
        print(f'Failed to start services: {e}')
        cleanup()
        sys.exit(1)
        
    yield
    
    # Shutdown
    cleanup()

app = FastAPI(lifespan=lifespan)

# 增加超时时间到 10 分钟，防止长时间任务（如模型下载）超时
client = httpx.AsyncClient(timeout=600.0)

async def forward_request(target_port: int, request: Request, path: str):
    url = f'http://localhost:{target_port}/{path}'
    if request.query_params:
        url += f'?{request.query_params}'
    
    # 记录请求日志
    logger.info(f"[PROXY] {request.method} /{path} -> Port {target_port}")
    
    # Exclude host header to let httpx/target handle it
    headers = dict(request.headers)
    headers.pop('host', None)
    headers.pop('content-length', None) # Let httpx handle content length
    
    try:
        req = client.build_request(
            request.method,
            url,
            headers=headers,
            content=request.stream(),
            timeout=600.0  # 10 分钟超时
        )
        r = await client.send(req, stream=True)
        
        logger.info(f"[PROXY] {request.method} /{path} <- Status {r.status_code}")
        
        return StreamingResponse(
            r.aiter_raw(),
            status_code=r.status_code,
            headers=dict(r.headers),
            background=BackgroundTasks([r.aclose])
        )
    except httpx.TimeoutException as e:
        logger.error(f'[PROXY] Timeout forwarding to port {target_port}: {str(e)}')
        return {'error': f'Backend timeout: {str(e)}'}
    except httpx.ConnectError as e:
        logger.error(f'[PROXY] Connection error to port {target_port}: {str(e)}')
        return {'error': f'Backend connection failed: {str(e)}'}
    except Exception as e:
        logger.error(f'[PROXY] Error forwarding to port {target_port}: {str(e)}')
        logger.error(f'[PROXY] Traceback: {traceback.format_exc()}')
        return {'error': f'Service unavailable: {str(e)}'}

@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD', 'PATCH'])
async def proxy(request: Request, path: str):
    # Routing Logic
    # APEX handles /edit and /pptx
    if path.startswith('edit') or path.startswith('pptx'):
        target = APEX_PORT
    else:
        # Default to PosterGen for everything else (including /, /models, etc.)
        target = POSTERGEN_PORT
        
    return await forward_request(target, request, path)

if __name__ == '__main__':
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    print(f'Starting Unified Proxy on port {PROXY_PORT}')
    print(f'APEX acts on {APEX_PORT}')
    print(f'PosterGen acts on {POSTERGEN_PORT}')
    print('Use Ctrl+C to stop all services.\n')
    
    uvicorn.run(app, host='0.0.0.0', port=PROXY_PORT, log_level="info")
