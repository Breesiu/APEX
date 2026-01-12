import os
import sys
import uuid
import shutil
import re
import argparse
import tempfile
import uvicorn
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# from .src.tools.pptx_execuator import _state_context_var, PosterState
from src.tools.pptx_execuator import _state_context_var, PosterState
from src.config import MAX_ITERATIONS
# Add src to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent))

try:
    # Importing the graph creation function from APEX source
    from src.graph import create_poster_edit_graph_v3
    from src.schema import AgentState
except ImportError as e:
    print(f"Error importing APEX modules: {e}")
    # Fallback/Debug info if src is not found
    print("Ensure you are running this script from the root of the APEX repository.")
    sys.exit(1)

app = FastAPI(title="APEX - Academic Poster Editing Agentic Expert")

# Allow CORS for frontend connection (default frontend port is usually 5173 or 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration for Directories
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR = BASE_DIR / "uploads"
PREVIEW_DIR = BASE_DIR / "previews"

# Create directories if they don't exist
for d in [OUTPUT_DIR, UPLOAD_DIR, PREVIEW_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# In-memory storage for job status (in a real production app, use a database)
edit_jobs: Dict[str, Dict[str, Any]] = {}
edit_logs: Dict[str, List[str]] = {}
previews: Dict[str, Path] = {}

def find_soffice() -> Optional[str]:
    """Find LibreOffice soffice executable."""
    env_path = os.environ.get("LIBREOFFICE_PATH")
    candidates = []
    
    if env_path:
        candidates.append(env_path)
    
    if sys.platform.startswith("win"):
        candidates += [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
    else:
        candidates += ["soffice", "/usr/bin/soffice", "/usr/local/bin/soffice"]
    
    for c in candidates:
        if Path(c).exists():
            return str(Path(c))
        which = shutil.which(c)
        if which:
            return which
    return None

def add_log(job_id: str, message: str):
    """Helper to append logs to a job."""
    if job_id not in edit_logs:
        edit_logs[job_id] = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    edit_logs[job_id].append(f"[{timestamp}] {message}")

@app.post("/edit/upload_pptx_preview")
async def upload_pptx_preview(file: UploadFile = File(...)):
    """Handle PPTX upload and generate a preview image."""
    preview_id = str(uuid.uuid4())
    pptx_path = UPLOAD_DIR / f"{preview_id}.pptx"
    
    with open(pptx_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Try convert to PNG via LibreOffice for preview
    png_path = PREVIEW_DIR / f"{preview_id}.png"
    fallback = False
    fallback_type = "libreoffice"
    
    try:
        soffice_path = find_soffice()
        if not soffice_path:
            raise Exception("LibreOffice not found in system paths")

        # Command to convert PPTX to PNG using LibreOffice with robust flags
        subprocess_cmd = [
            soffice_path, "--headless", "--invisible", "--nologo", 
            "--nofirststartwizard", "--norestore", "--convert-to", "png", 
            "--outdir", str(PREVIEW_DIR), str(pptx_path)
        ]
        
        # Run conversion with timeout
        subprocess.run(subprocess_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        
        # LibreOffice names output as filename.png
        generated_png = PREVIEW_DIR / (pptx_path.stem + ".png")
        if generated_png.exists():
            shutil.move(generated_png, png_path)
        else:
            raise Exception("Preview generation failed - output file not found")
            
    except Exception as e:
        print(f"LibreOffice conversion warning: {e}")
        fallback = True
        fallback_type = "placeholder" 
        # In a real app, you might copy a default placeholder image here
    
    previews[preview_id] = pptx_path
    
    return {
        "preview_id": preview_id,
        "url": f"/edit/preview/raw/{preview_id}",
        "fallback": fallback,
        "fallback_type": fallback_type,
        "pptx_download_url": f"/edit/download_pptx/{preview_id}"
    }

@app.get("/edit/preview/raw/{preview_id}")
async def get_raw_preview(preview_id: str):
    """Serve the generated preview image."""
    png_path = PREVIEW_DIR / f"{preview_id}.png"
    if not png_path.exists():
        return JSONResponse({"error": "Preview not found"}, status_code=404)
    return FileResponse(png_path)

@app.get("/edit/download_pptx/{preview_id}")
async def download_pptx(preview_id: str):
    """Download the uploaded raw PPTX."""
    pptx_path = UPLOAD_DIR / f"{preview_id}.pptx"
    if not pptx_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(pptx_path, filename=f"uploaded_{preview_id}.pptx")

@app.post("/edit/submit")
async def submit_edit(
    background_tasks: BackgroundTasks,
    instruction: str = Form(...),
    pptx_file: Optional[UploadFile] = File(None),
    preview_id: Optional[str] = Form(None),
    job_id: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None)
):
    """Submit a new editing job."""
    # 1. Determine if this is a NEW job or CONTINUATION
    # Explicit new job if file provided or no job_id
    is_new_job = (pptx_file is not None) or (preview_id is not None) or (not job_id)
    
    if is_new_job:
        current_job_id = str(uuid.uuid4())
        job_root = OUTPUT_DIR / current_job_id
        job_root.mkdir(parents=True, exist_ok=True)
        iteration = 1
    else:
        # Continuation
        if job_id not in edit_jobs:
             # Fallback: check if directory exists on disk
             if (OUTPUT_DIR / job_id).exists():
                 current_job_id = job_id
                 job_root = OUTPUT_DIR / current_job_id
             else:
                 raise HTTPException(status_code=404, detail="Job not found")
        else:
             current_job_id = job_id
             job_root = OUTPUT_DIR / current_job_id
        
        # Determine iteration number by scanning directories for out_put_n
        existing_outputs = [d for d in job_root.iterdir() if d.is_dir() and d.name.startswith("out_put_")]
        max_idx = 0
        for d in existing_outputs:
            try:
                parts = d.name.split("_")
                # Expected format out_put_N
                if len(parts) >= 3 and parts[0] == "out" and parts[1] == "put":
                    idx = int(parts[2])
                    if idx > max_idx: max_idx = idx
            except: pass
        iteration = max_idx + 1

    # 2. Agent works in job_root for file reuse; out_put_n created after completion
    # Input PPTX goes to job_root (will be copied by agent workflow)
    
    # 3. Handle Input PPTX - place in job_root for reuse
    base_pptx_path = job_root / "input.pptx"
    
    if is_new_job:
        # Copy from upload or preview
        if pptx_file:
            with open(base_pptx_path, "wb") as f:
                shutil.copyfileobj(pptx_file.file, f)
        elif preview_id:
            source_pptx = UPLOAD_DIR / f"{preview_id}.pptx"
            if not source_pptx.exists():
                raise HTTPException(status_code=400, detail="Preview ID not found")
            shutil.copy(source_pptx, base_pptx_path)
    else:
        # Copy from PREVIOUS iteration's output
        prev_output = None
        # Try finding from memory
        if current_job_id in edit_jobs and edit_jobs[current_job_id].get("output_pptx"):
             prev_output = Path(edit_jobs[current_job_id]["output_pptx"])
        
        # Fallback: finding from disk (latest pptx in previous iteration folder)
        if (not prev_output or not prev_output.exists()) and iteration > 1:
            prev_dir = job_root / f"out_put_{iteration-1}"
            if prev_dir.exists():
                # Find latest modified pptx that isn't named 'input.pptx' if possible
                candidates = list(prev_dir.glob("*.pptx"))
                if candidates:
                    prev_output = max(candidates, key=os.path.getmtime)

        if prev_output and prev_output.exists():
            shutil.copy(prev_output, base_pptx_path)
        else:
             raise HTTPException(status_code=400, detail="Previous version not found for continuation.")
    
    # 4. Handle PDF - PDF stays in job_root for reuse across iterations
    target_pdf_path = job_root / "paper.pdf"
    
    if pdf_file:
        with open(target_pdf_path, "wb") as f:
            shutil.copyfileobj(pdf_file.file, f)
    # PDF in job_root is reused automatically for subsequent iterations

    # Initialize Job Status
    edit_jobs[current_job_id] = {
        "job_id": current_job_id,
        "status": "pending",
        "progress": 0,
        "message": f"Starting iteration {iteration}...",
        "output_pptx": None,
        "output_png": None,
        "current_iteration": iteration
    }
    
    # Start Agent in Background
    # Agent works in job_root for file reuse; iteration number passed for out_put_n creation
    background_tasks.add_task(
        run_apex_task, 
        current_job_id, 
        base_pptx_path, 
        instruction, 
        target_pdf_path if target_pdf_path.exists() else None, 
        job_root,
        iteration
    )
    
    return {"job_id": current_job_id, "status": "pending", "progress": 0, "message": "Job submitted"}

async def run_apex_task(job_id: str, pptx_path: Path, instruction: str, pdf_path: Optional[Path], job_dir: Path, iteration: int = 1):
    """Background task to run the APEX LangGraph workflow."""
    try:
        edit_jobs[job_id]["status"] = "processing"
        add_log(job_id, "Starting APEX Agentic Workflow...")
        
        # Initialize Graph
        graph = create_poster_edit_graph_v3()
        # 为每个并发运行创建一个全新的状态实例
        new_state = PosterState() 
        
        # 注入到当前协程上下文
        token = _state_context_var.set(new_state)
        
        initial_state = AgentState(
            user_instruction=instruction,
            pptx_path=pptx_path,
            pdf_path=pdf_path,
            output_dir=job_dir,
            max_iterations=MAX_ITERATIONS,
            mode="api",
            iterate_version="user_significant_version",
            iterate_debug=False,
            model = BACKEND_MODEL,
            use_paper_pdf_directly = BACKEND_USE_PAPER_PDF_DIRECTLY,
            no_vlm_in_paper_understanding_tool = BACKEND_NO_VLM_IN_PAPER_UNDERSTANDING_TOOL,
        )
        
        # Execute Graph
        add_log(job_id, f"Processing instruction: {instruction}")
        result = await graph.ainvoke(initial_state)

        _state_context_var.reset(token)

        # Check Results
        if result.get("error"):
            edit_jobs[job_id]["status"] = "failed"
            edit_jobs[job_id]["error"] = result["error"]
            add_log(job_id, f"❌ Error: {result['error']}")
            return

        final_pptx = result.get("current_pptx_path")
        if final_pptx and os.path.exists(final_pptx):
            add_log(job_id, f"Agent produced: {final_pptx}")
            
            # === Post-processing: Organize outputs into out_put_n folder ===
            output_folder = job_dir / f"out_put_{iteration}"
            output_folder.mkdir(parents=True, exist_ok=True)
            add_log(job_id, f"Created output folder: {output_folder}")
            
            # Determine latest version from filename pattern _vN
            import re as regex_module
            version_pattern = regex_module.compile(r'_v(\d+)')
            max_version = 0
            latest_pptx = Path(final_pptx)
            
            # Scan all pptx in job_dir (excluding input.pptx)
            for f in job_dir.glob("*.pptx"):
                if f.name == "input.pptx":
                    continue
                match = version_pattern.search(f.stem)
                if match:
                    ver = int(match.group(1))
                    if ver > max_version:
                        max_version = ver
                        latest_pptx = f
            
            add_log(job_id, f"Latest PPTX identified: {latest_pptx}")
            
            # Generate PNG and move files to output folder
            soffice_path = find_soffice()
            latest_png = None
            
            # Process all pptx files (except input.pptx)
            pptx_files = [f for f in job_dir.glob("*.pptx") if f.name != "input.pptx"]
            
            for pptx_file in pptx_files:
                png_name = pptx_file.stem + ".png"
                png_path = job_dir / png_name
                
                # Generate PNG if not exists
                if soffice_path and not png_path.exists():
                    try:
                        subprocess.run(
                            [soffice_path, "--headless", "--invisible", "--nologo",
                             "--nofirststartwizard", "--norestore", "--convert-to", "png",
                             "--outdir", str(job_dir), str(pptx_file)],
                            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120
                        )
                    except Exception as e:
                        add_log(job_id, f"Warning: PNG generation failed for {pptx_file.name}: {e}")
                
                # Move PPTX to output folder
                dest_pptx = output_folder / pptx_file.name
                if pptx_file.exists():
                    shutil.move(str(pptx_file), str(dest_pptx))
                
                # Move PNG to output folder  
                png_path = job_dir / png_name  # Re-check after generation
                if png_path.exists():
                    dest_png = output_folder / png_name
                    shutil.move(str(png_path), str(dest_png))
                    # Track if this is the latest
                    if pptx_file.name == latest_pptx.name:
                        latest_png = dest_png
            
            # Find latest PNG if not tracked
            if not latest_png:
                latest_png_path = output_folder / (latest_pptx.stem + ".png")
                if latest_png_path.exists():
                    latest_png = latest_png_path
                else:
                    pngs = list(output_folder.glob("*.png"))
                    if pngs:
                        latest_png = max(pngs, key=os.path.getmtime)
            
            # Update job status with latest version paths
            latest_pptx_final = output_folder / latest_pptx.name
            if not latest_pptx_final.exists():
                pptxs = list(output_folder.glob("*.pptx"))
                if pptxs:
                    latest_pptx_final = max(pptxs, key=os.path.getmtime)
            
            edit_jobs[job_id]["output_pptx"] = str(latest_pptx_final) if latest_pptx_final.exists() else None
            edit_jobs[job_id]["output_png"] = str(latest_png) if latest_png and latest_png.exists() else None
            edit_jobs[job_id]["output_folder"] = str(output_folder)
            
            add_log(job_id, f"Final PPTX: {edit_jobs[job_id]['output_pptx']}")
            add_log(job_id, f"Final PNG: {edit_jobs[job_id]['output_png']}")
            
            edit_jobs[job_id]["status"] = "completed"
            edit_jobs[job_id]["progress"] = 100
            edit_jobs[job_id]["message"] = f"Iteration {iteration} completed"
            add_log(job_id, f"✅ APEX Finished successfully - Iteration {iteration}")
        else:
            raise Exception("No output PPTX generated in the final state")

    except Exception as e:
        edit_jobs[job_id]["status"] = "failed"
        edit_jobs[job_id]["error"] = str(e)
        add_log(job_id, f"❌ System Error: {str(e)}")

@app.get("/edit/status/{job_id}")
async def get_edit_status(job_id: str):
    if job_id not in edit_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return edit_jobs[job_id]

@app.get("/edit/logs/{job_id}")
async def get_edit_logs(job_id: str):
    return {"logs": edit_logs.get(job_id, [])}

@app.get("/edit/preview/{job_id}")
async def get_edited_preview(job_id: str):
    job = edit_jobs.get(job_id)
    if job and job.get("output_png"):
        return FileResponse(job["output_png"])
    raise HTTPException(status_code=404, detail="Preview not ready")

@app.get("/edit/download_edited_pptx/{job_id}")
async def download_edited_pptx(job_id: str):
    job = edit_jobs.get(job_id)
    if job and job.get("output_pptx"):
        return FileResponse(job["output_pptx"], filename=f"edited_{job_id[:8]}.pptx")
    raise HTTPException(status_code=404, detail="File not ready")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APEX backend server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")

    # ✅ Requested knobs
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3-flash-preview",
        help="LLM model name to store into AgentState.model (e.g., gemini-3-flash-preview, qwen..., gpt-...).",
    )

    parser.add_argument(
        "--use-paper-pdf-directly",
        action="store_true",
        default=True,
        help="Set AgentState.use_paper_pdf_directly=True (default).",
    )
    parser.add_argument(
        "--no-use-paper-pdf-directly",
        dest="use_paper_pdf_directly",
        action="store_false",
        help="Set AgentState.use_paper_pdf_directly=False.",
    )

    parser.add_argument(
        "--no-vlm-in-paper-understanding-tool",
        action="store_true",
        default=False,
        help="Set AgentState.no_vlm_in_paper_understanding_tool=True (disable VLM usage in paper tool).",
    )

    args = parser.parse_args()

    # Export parsed values to module-level defaults used by request handlers
    BACKEND_MODEL = args.model
    BACKEND_USE_PAPER_PDF_DIRECTLY = args.use_paper_pdf_directly
    BACKEND_NO_VLM_IN_PAPER_UNDERSTANDING_TOOL = args.no_vlm_in_paper_understanding_tool

    uvicorn.run(app, host=args.host, port=args.port)