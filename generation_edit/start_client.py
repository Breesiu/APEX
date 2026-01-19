#!/usr/bin/env python3
"""
APEX & PosterGen Client Launcher (Windows/Linux/Mac)
This script will:
1. Start APEX Frontend.
2. Start PosterGen Frontend.
3. Open the Unified Dashboard.
"""

import sys
import subprocess
import time
import webbrowser
from pathlib import Path
import platform

def start_frontend(name, path, command):
    """Start a frontend development server."""
    if not path.exists():
        print(f"Error: {name} frontend not found at {path}")
        return False
    
    print(f"Starting {name} Frontend...")
    
    if platform.system() == "Windows":
        # On Windows, start in a new window
        subprocess.Popen(
            ["start", f"{name} Frontend", "cmd", "/c", command],
            shell=True,
            cwd=str(path)
        )
    else:
        # On Linux/Mac, start in background
        subprocess.Popen(
            command.split(),
            cwd=str(path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    
    return True

def main():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent  # F:\APEX
    
    print("=" * 60)
    print("       APEX & PosterGen Client Launcher")
    print("=" * 60)
    print()
    
    # Step 1: Start APEX Frontend
    print("[1/3] Starting APEX Frontend...")
    apex_frontend = project_root / "APEX" / "frontend"
    start_frontend("APEX", apex_frontend, "npm run dev")
    
    # Step 2: Start PosterGen Frontend
    print("\n[2/3] Starting PosterGen Frontend...")
    postergen_frontend = project_root / "PosterGen" / "webui" / "frontend"
    start_frontend("PosterGen", postergen_frontend, "npm run dev")
    
    # Step 3: Open Unified Dashboard
    print("\n[3/3] Opening Unified Dashboard...")
    time.sleep(3)
    
    index_path = script_dir / "index.html"
    if index_path.exists():
        webbrowser.open(f"file://{index_path}")
        print(f"Opened: {index_path}")
    else:
        print(f"Warning: index.html not found at {index_path}")
    
    print()
    print("=" * 60)
    print("               Startup Sequence Complete")
    print("=" * 60)
    print()
    print("Note: Ensure backend service is available on localhost:8000")
    print("To stop, close all opened terminal windows.")
    print()
    
    if platform.system() != "Windows":
        input("Press Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStartup cancelled by user.")
        sys.exit(0)
