import sys
import os
import uvicorn
from pathlib import Path

# Setup paths relative to this script
# This script is in F:\APEX\APEX\generation_edit\
# PosterGen is in F:\APEX\PosterGen\

current_dir = Path(__file__).resolve().parent
postergen_root = current_dir.parent.parent / "PosterGen"
webui_dir = postergen_root / "webui"

if not postergen_root.exists():
    print(f"Error: PosterGen root not found at {postergen_root}")
    sys.exit(1)

# Mimic PosterGen/webui/start_backend.py setup
print(f"Setting up PosterGen environment...")
sys.path.insert(0, str(postergen_root))
os.chdir(postergen_root)

# Import the app
# Note: PosterGen structure has backend module in webui/backend
# But webui/start_backend.py runs from 'project_root' (PosterGen) and does 'from backend.main import app'??
# Wait, PosterGen/webui/start_backend.py:
#   project_root = .../PosterGen
#   sys.path.insert(0, str(project_root)) # adds PosterGen/ to path
#   from backend.main import app
#
# But 'backend' is in 'webui/backend'.
# Unless 'backend' package is copied to root?
# Let's check logic in start_backend.py again.
# "sys.path.insert(0, str(project_root))"
# If 'backend' is inside 'webui', then 'import backend.main' would fail unless 'backend' is in sys.path.
# Maybe 'webui' is also in sys.path? Or 'backend' is in root?
# The list_dir of PosterGen/webui showed 'backend'.
# So 'backend' is inside 'webui'.
# If start_backend.py is inside webui, and it adds PosterGen root to path.
# Then 'from backend.main' works ONLY if 'webui' is a packages or added to path?
# Wait.
# Let's check PosterGen folder structure again.
# PosterGen/
#   src/
#   webui/
#      backend/
#      start_backend.py
#
# If I am in PosterGen root. 'import backend.main' will fail.
# It should be 'from webui.backend.main import app'.
# But start_backend.py says 'from backend.main import app'.
# This implies that 'webui' is added to python path OR 'backend' is in root?
# Ah, start_backend.py adds `project_root` to path.
# Maybe I should just check if start_backend.py actually adds webui to path?
# Or maybe the file I read was incomplete/misleading?
# 
# Let's re-read start_backend.py lines to be sure.
# Lines 7-8: project_root = ...parent.parent
# sys.path.insert(0, str(project_root))
# ...
# from backend.main import app
#
# If this works, then 'backend' must be importable from project_root.
# Maybe there is a backend folder in root?
# list_dir of F:\APEX\PosterGen might clarify.

# I'll rely on adding BOTH just in case.
sys.path.insert(0, str(webui_dir))

try:
    from backend.main import app
except ImportError:
    # Try importing via webui
    from webui.backend.main import app

if __name__ == "__main__":
    print("Starting PosterGen Backend on Port 8002 via Custom Runner")
    uvicorn.run(app, host="0.0.0.0", port=8002)
