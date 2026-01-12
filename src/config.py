import os
from pathlib import Path

# --- API Configuration ---

# Qwen API (Alibaba Cloud DashScope)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "") # TODO:

# Alternative: Local Qwen deployment
QWEN3_8B_LOCAL_ENDPOINT = os.getenv("QWEN3_8B_LOCAL_ENDPOINT", "http://localhost:8050/v1")
QWEN3_VL_8B_LOCAL_ENDPOINT = os.getenv("QWEN3_VL_8B_LOCAL_ENDPOINT", "http://localhost:8050/v1")
# QWEN3_VL_8B_LOCAL_ENDPOINT = os.getenv("QWEN3_VL_8B_LOCAL_ENDPOINT", "http://localhost:8055/v1")

# Model Selection
PLANNER_MODEL = os.getenv("PLANNER_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-30B-A3B-Instruct")         # For planning and reasoning
CONTENT_EDITOR_MODEL = os.getenv("CONTENT_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-30B-A3B-Instruct")           # For content generation
REVIEW_MODEL = os.getenv("REVIEW_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-30B-A3B-Instruct")        # For visual review (multimodal)
LAYOUT_MODEL = os.getenv("LAYOUT_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-30B-A3B-Instruct")            # For layout optimization
# PAPER_UNDERSTANDING_MODEL = os.getenv("PAPER_UNDERSTANDING_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-32B-Instruct")  # For paper understanding# --- System Configuration ---
PAPER_UNDERSTANDING_MODEL = os.getenv("PAPER_UNDERSTANDING_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-30B-A3B-Instruct")

# PAPER_UNDERSTANDING_MODEL = os.getenv("PAPER_UNDERSTANDING_MODEL", "/root/shared_planing/LLM_model/Qwen3-14B")  # For paper understanding# --- System Configuration ---


# # Model Selection
# PLANNER_MODEL = os.getenv("PLANNER_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-8B-Instruct")         # For planning and reasoning
# CONTENT_EDITOR_MODEL = os.getenv("CONTENT_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-8B-Instruct")           # For content generation
# REVIEW_MODEL = os.getenv("REVIEW_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-8B-Instruct")        # For visual review (multimodal)
# LAYOUT_MODEL = os.getenv("LAYOUT_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-8B-Instruct")            # For layout optimization
# PAPER_UNDERSTANDING_MODEL = os.getenv("PAPER_UNDERSTANDING_MODEL", "/root/shared_planing/LLM_model/Qwen3-VL-8B-Instruct")  # For paper understanding# --- System Configuration ---



# Maximum iterations for review-optimize loop
MAX_ITERATIONS = 1
# Review score threshold (0-100)
ACCEPTABLE_SCORE_THRESHOLD = 75.0

# Layout analysis parameters
OVERLAP_IOU_THRESHOLD = 0.05         # Elements with IoU > this are considered overlapping
MARGIN_POINTS = 20.0                 # Minimum margin from slide edges

# --- Paths ---

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"
TEMP_DIR = PROJECT_ROOT / "temp"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create directories
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# --- Logging ---

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" 