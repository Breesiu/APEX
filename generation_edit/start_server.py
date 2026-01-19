#!/usr/bin/env python3
"""
APEX & PosterGen Server Startup Script
Usage: python start_server.py
This script starts the Unified Backend Proxy which manages both APEX and PosterGen backends.
"""

import sys
import subprocess
from pathlib import Path

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent  # F:\APEX
    
    print("=" * 60)
    print("=== Starting APEX & PosterGen Backend Services ===")
    print("=" * 60)
    print(f"Project Root: {project_root}")
    print(f"Script Dir: {script_dir}")
    print()
    
    # Check if run_services.py exists
    run_services = script_dir / "run_services.py"
    if not run_services.exists():
        print(f"Error: run_services.py not found in {script_dir}")
        sys.exit(1)
    
    # Run the unified service runner
    # This python script will spawn:
    # 1. APEX Backend (Port 8001)
    # 2. PosterGen Backend (Port 8002)
    # 3. Proxy Service (Port 8000)
    print("Starting Python Service Manager...")
    print("This will start APEX (8001), PosterGen (8002), and Proxy (8000)")
    print()
    
    try:
        subprocess.run([sys.executable, str(run_services)], cwd=str(project_root), check=True)
    except KeyboardInterrupt:
        print("\n\nShutting down services...")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"\nError: Service manager exited with code {e.returncode}")
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
