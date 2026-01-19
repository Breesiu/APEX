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

*   **Backend (Linux):** Runs APEX backend (Python) and PosterGen backend (Python) in separate Conda environments, managed by a unified proxy service.
*   **Frontend (Windows/Linux/Mac):** Runs APEX frontend (Node.js), PosterGen frontend (Node.js), and the browser interface.

## 2. Deployment Steps

### Step 1: Backend Environment Preparation (Linux)

Since APEX and PosterGen have conflicting dependencies, we need to use **Conda** to create separate environments for them.

**1. Create PosterGen Environment:**

```bash
# Create an environment named postergen_env (can be customized)
conda create -n postergen_env python=3.10 -y

# Install PosterGen dependencies (uv is recommended for faster speed and conflict resolution)
# Replace 'postergen_env' with your actual environment name
conda run -n postergen_env pip install uv
conda run -n postergen_env uv pip install -r PosterGen/requirements.txt

# Install required components for service startup
conda run -n postergen_env pip install fastapi uvicorn httpx
```

**2. Create APEX Environment:**

```bash
# Create an environment named apex_env (can be customized)
conda create -n apex_env python=3.11 -y

# Install APEX dependencies
# Replace 'apex_env' with your actual environment name
conda run -n apex_env pip install -r APEX/requirements.txt

# Install required components for service startup
conda run -n apex_env pip install fastapi uvicorn httpx
```

### Step 2: Configure Environment Names (Required)

Before starting the services, you must tell the startup script which environment names you used.

1.  Open the file `APEX/generation_edit/env_config.json`.
2.  Modify the values to match the environment names you created in Step 1.

Example:
```json
{
    "apex_env_name": "apex_env",
    "postergen_env_name": "postergen_env"
}
```

### Step 3: Start the Backend Service

You can start the service from any environment (including base), and the script will automatically switch to the correct Conda environments.

1.  Enter the `APEX/generation_edit` directory.
2.  **Start the backend service**:
    ```bash
    python start_server.py
    ```
    *Success indicator: you should see the output "Starting Unified Proxy on port 8000"*

### Step 4: Frontend Preparation (Windows/Linux/Mac)

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

### Step 5: Start the Frontend Client

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
A: Please check the frontend server terminal for errors and ensure `npm install` has been executed successfully.


** If you encounter `ModuleNotFoundError: No module named 'langchain_core.memory'` when running PosterGen， The following workaround may help resolve the issue.

Locate the file:

```
PosterGen/utils/langgraph_utils.py
```

Change:

```python
from langchain.schema import HumanMessage, SystemMessage
```

to:

```python
from langchain_core.messages import HumanMessage, SystemMessage
```

This may work because in newer versions of LangChain, message-related classes have been moved to `langchain_core.messages`.
