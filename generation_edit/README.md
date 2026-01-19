# PosterGen & APEX Integrated System Quick Start Guide

> **Note:** This folder (`generation_edit`) is designed for users who want a seamless workflow from **poster generation to poster editing**. If you only need to use PosterGen or APEX individually, please refer to each project's own README.

This guide is optimized for a **frontend-backend separation** scenario (backend deployed on a Linux server, frontend running locally), with no need to modify any source code.

## 0. Project Acquisition

Please follow these steps to clone the projects:

```bash
# Clone the APEX project (includes the integration system)
git clone https://github.com/Breesiu/APEX.git

# Clone the PosterGen project into the same directory
git clone https://github.com/Y-Research-SBU/PosterGen.git
```

Final directory structure:
```
.
├── APEX/                # APEX project source code
│   └── generation_edit/ # Integration system
└── PosterGen/           # PosterGen project source code
```

## 1. Architecture Overview

*   **Backend (Linux):** Runs APEX backend (Python), PosterGen backend (Python), and the unified proxy service.
*   **Frontend (Windows/Linux/Mac):** Runs APEX frontend (Node.js), PosterGen frontend (Node.js), and the browser interface.
*   **Connection:** Use VSCode port forwarding or other methods to map the backend service to `localhost:8000`.

## 2. Deployment Steps

### Step 1: Backend Preparation (Linux)

1.  Prepare the `APEX` and `PosterGen` project code on your server.
2.  Enter the `APEX/generation_edit` directory.
3.  Make sure your Python environment is activated and all dependencies are installed:
    ```bash
    # In the project root (the directory containing both APEX and PosterGen)
    pip install -r APEX/requirements.txt
    pip install -r PosterGen/requirements.txt
    pip install fastapi uvicorn httpx
    ```
    
    **Note:** If you encounter a GitHub clone error when running `pip install -r PosterGen/requirements.txt`, change line 48 in `requirements.txt` from `git+https://github.com/Hadlay-Zhang/marker.git` to `marker-pdf[full]`, then rerun the command.

### Step 2: Frontend Preparation (Windows/Linux/Mac)

1.  Make sure you have `Node.js` installed locally.
2.  Install frontend dependencies (if not already installed):
    ```bash
    # APEX frontend
    cd APEX/frontend
    npm install

    # PosterGen frontend
    cd PosterGen/webui/frontend
    npm install
    ```

### Step 3: Start the Frontend Client

1.  Make sure the backend service is running on the server (or connected to localhost:8000 via port forwarding).
2.  In the `APEX/generation_edit` directory, run the client startup script:
    ```bash
    python start_client.py
    ```
3.  The script will automatically:
    *   Start the APEX frontend development server.
    *   Start the PosterGen frontend development server.
    *   Automatically open the browser to access the integrated dashboard.

## 3. FAQ

**Q: Browser says it can't connect to localhost:8000?**
A: Please make sure the backend service is running. If the backend is on a remote server, use VSCode port forwarding or an SSH tunnel to map remote port 8000 to your local machine.

**Q: The frontend page is blank?**
A: Check the frontend server windows for errors and make sure `npm install` completed successfully.