import sys
import subprocess
import json
import signal
import time
from pathlib import Path

def cleanup_old_processes():
    """清理旧的服务进程"""
    print('Checking for existing service processes...')
    processes_to_kill = [
        'start_backend.py --port 8001',
        'postergen_runner.py',
        'run_services.py'
    ]
    
    killed_any = False
    for process_name in processes_to_kill:
        try:
            # 使用 pkill 查找并终止进程
            result = subprocess.run(
                ['pkill', '-9', '-f', process_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f'  ✓ Killed old process: {process_name}')
                killed_any = True
        except Exception:
            pass
    
    if killed_any:
        print('Waiting for ports to be released...')
        time.sleep(3)
    else:
        print('No existing processes found.')
    print()

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent  # /AAAAAAAAPEX
    
    print('=' * 60)
    print('=== Starting APEX & PosterGen Backend Services ===')
    print('=' * 60)
    print(f'Project Root: {project_root}')
    print(f'Script Dir: {script_dir}')
    print()

    # Cleanup old processes before starting
    cleanup_old_processes()

    # Load environment config
    config_file = script_dir / 'env_config.json'
    apex_env_name = 'Python.3.11'  # Default
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                apex_env_name = config.get('apex_env_name', apex_env_name)
                print(f'Loaded config from {config_file}')
        except Exception as e:
            print(f'Warning: Failed to load env_config.json: {e}')
    else:
        print(f'Warning: env_config.json not found, using default env: {apex_env_name}')
    
    # Check if run_services.py exists
    run_services = script_dir / 'run_services.py'
    if not run_services.exists():
        print(f'Error: run_services.py not found in {script_dir}')
        sys.exit(1)
    
    print('Starting Python Service Manager...')
    print(f"Using Conda environment '{apex_env_name}' to run the proxy service.")
    print('This will start APEX (8001), PosterGen (8002), and Proxy (8000)')
    print()
    
    # Run the unified service runner as a subprocess
    cmd = ['conda', 'run', '--no-capture-output', '-n', apex_env_name, 'python', str(run_services)]
    
    try:
        # Use Popen to allow the process to run and stream output
        process = subprocess.Popen(
            cmd, 
            cwd=str(project_root),
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        # Wait for the process (allows Ctrl+C to propagate)
        process.wait()
        
    except KeyboardInterrupt:
        print('\n\nShutting down services...')
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        sys.exit(0)
    except Exception as e:
        print(f'\nError: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
