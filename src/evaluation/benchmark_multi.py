from langsmith import Client, traceable
from langsmith.evaluation import evaluate, LangChainStringEvaluator, aevaluate
from langsmith.schemas import Run, Example
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from ..config import QWEN3_VL_8B_LOCAL_ENDPOINT, REVIEW_MODEL, MAX_ITERATIONS
from ..tools.image_tools import convert_pptx_to_png, encode_image_to_base64
from ..tools.pdf_parser import extract_paper_content

from uuid import uuid4
import os
from pydantic import BaseModel, Field

from typing import Dict, List, Optional
import json
from pathlib import Path
import asyncio
from datetime import datetime

from ..graph import create_poster_edit_graph_v3
from ..schema import AgentState, PaperContentExtractionResult
from langsmith.schemas import ExampleCreate
import random
import time
from ..tools.pptx_execuator import _state_context_var, PosterState

 
# Experiment configuration class
class ExperimentConfig(BaseModel):
    """Configuration for a single experiment run"""
    name: str
    experiment_type: str  # 'baseline' or 'standard'AgentState
    mode: str  # 'api' or 'llmgenerator'
    model: str
    image_model: Optional[str] = None
    dataset_name: str
    is_filter_applied: bool = False
    preserve_runs: bool = False
    iterate_version: str = 'user_instruction_significant_revised_elements'
    iterate_debug: bool = False
    num_repetitions: int = 1
    max_concurrency: int = 5
    
    no_vlm_in_paper_understanding_tool: bool = False 
    max_iteration: int = MAX_ITERATIONS
    incontext: bool = True
    
    def get_version_string(self) -> str:
        """Generate version string based on config"""
        if self.experiment_type == 'baseline':
            return f"baseline_v30_{self.mode}_{self.model}_{self.name}_{self.dataset_name}_fullxml{self.use_full_xml_baseline}"
        elif self.model == '/root/shared_planing/LLM_model/Qwen3-VL-30B-A3B-Instruct':
            return 'ablation_qwen3-vl-30b-a3b-instruct'
        else:
            return f"v31_{self.mode}_{self.model}_{self.dataset_name}_preserve{self.preserve_runs}_{self.incontext}_{self.iterate_version}_maxiter{self.max_iteration}"
        

dataset_name = "FINAL"
EXPERIMENT_CONFIGS = []
BASELINE_CONFIGS = []
# for model in ['qwen3-vl-plus']:    # ['gemini-3-flash-preview']: #'qwen3-vl-plus']:
# model =
if True:
    pass
    for model in ['gemini-3-flash-preview']:    # ['gemini-3-flash-preview']: #'qwen3-vl-plus']:
    # for model in ['qwen3-vl-plus']:    # ['gemini-3-flash-preview']: #'qwen3-vl-plus']:
        EXPERIMENT_CONFIGS += [
            ExperimentConfig(
                name=f"standard_{model}31_12",
                experiment_type="standard",
                mode="api",
                model="/root/shared_planing/LLM_model/Qwen3-VL-30B-A3B-Instruct",
                # image_model="gemini-3-pro-image-preview",
                preserve_runs=False,
                dataset_name=dataset_name,   
                incontext=True,
                no_vlm_in_paper_understanding_tool=False,
                # max_iteration=0,
                # iterate_version='all_revised_field'
            ),

        ]

benchmark_dir = "./benchmark_withpostergen_flat"
benchmark_path = Path(benchmark_dir)

def load_instructions_from_json(json_path: str) -> List[str]:
    """Load user instructions from instruction.json file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"Error loading instructions from {json_path}: {e}")
        return []

class InstructionFollowingEvaluator:
    """Evaluates how well the system followed user instructions"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=REVIEW_MODEL,
            temperature=0.1,    
            base_url=QWEN3_VL_8B_LOCAL_ENDPOINT,
            api_key=os.getenv("ALIBABA_API_KEY", "EMPTY"),
            max_completion_tokens=500,
        )
        # self.prompt = Instruction_Following_Evaluator_PROMPT

    def __call__(self, inputs: dict, outputs: dict) -> Dict:
        class ResponseSchema(BaseModel):
            reason: str = Field(..., description="Detailed explanation of the evaluation.")
            score: int = Field(..., description="Score from 0 to 10 indicating how well the instructions were followed.")
        
        return {
            'key':"instruction_following_score",
            'score': 8,
            'reason':"Placeholder reason for evaluation."
        }


def get_model_api_config(model: str, image_model: Optional[str] = None) -> Dict:
    """Get API configuration based on model name"""
    config = {}
    
    # Text model configuration
    if model in ['qwen3-vl-plus', 'qwen-vl-max', 'qvq-max-latest']:
        config.update({
            'model': model,
            'base_url': "",
            'api_key': ""
        })
    elif model == 'gemini-3-flash-preview':
        config.update({
            'model': model,
            'base_url': "",
            'api_key': ""
        })

    return config

client = Client()

# Create or get dataset
try:
    existing_datasets_list = list(client.list_datasets(dataset_name=dataset_name))
    local = True
    if local:
        dataset = client.clone_public_dataset("")
    else:
        if existing_datasets_list:
            dataset = existing_datasets_list[0]
            print(f"Found existing dataset: {dataset.name}")
        else:
            print(f"Dataset '{dataset_name}' not found. Creating new one.")
            dataset = client.create_dataset(dataset_name=dataset_name)
except Exception as e:
    print(f"Error with dataset: {e}")
    raise e

async def run_single_experiment(config: ExperimentConfig):
    """Run a single experiment with the given configuration"""
    print(f"\n{'='*80}")
    print(f"Starting Experiment: {config.name}")
    print(f"{'='*80}")
    print(f"Config: {config.model_dump_json(indent=2)}")
    
    
    # Create graph based on experiment type

    graph = create_poster_edit_graph_v3()
    
    # Create run function with closure over config and graph
    async def run_graph_configured(inputs: dict) -> dict:
        # graph = create_poster_edit_graph_v3()
        # 为每个并发运行创建一个全新的状态实例
        new_state = PosterState() 
        
        # 注入到当前协程上下文
        token = _state_context_var.set(new_state)
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version = config.get_version_string()
            model_config = get_model_api_config(config.model, config.image_model)
            
            initial_state = AgentState(
                user_instruction=inputs["user_instruction"],
                pptx_path=inputs["pptx_path"],
                pdf_path=inputs["pdf_path"],
                output_dir=benchmark_path/f"{inputs['poster_name']}/{config.mode}_{version}/{inputs['instruction_index']}/",
                max_iterations=config.max_iteration if hasattr(config, 'max_iteration') else MAX_ITERATIONS,
                mode=config.mode,
                is_filter_applied=config.is_filter_applied,
                experiment_name=config.name,
                iterate_version=config.iterate_version,
                iterate_debug=config.iterate_debug,
                timestamp=timestamp,
                iteration_count=0,
                paper_related=inputs.get("paper_related", None),
                preserve_runs=config.preserve_runs,
                **model_config,
                incontext=config.incontext,
                no_vlm_in_paper_understanding_tool=config.no_vlm_in_paper_understanding_tool,
                use_full_xml_baseline=config.use_full_xml_baseline,
                python_pptx_ablation=config.python_pptx_ablation,
            )
            t0 = time.time()
            print(f"[RUN-START pid={os.getpid()}] idx={inputs['instruction_index']} t={t0:.3f}")
            final_state = await graph.ainvoke(initial_state)
            t1 = time.time()
            print(f"[RUN-END   pid={os.getpid()}] idx={inputs['instruction_index']} dt={t1-t0:.2f}s")
            return {
                # "edited_pptx_path": final_state['current_pptx_path'],
            }
        finally:
            _state_context_var.reset(token)
    
    # Run evaluation
    examples = list(client.list_examples(dataset_id=dataset.id))  # optionally add splits=[...]

    result = await client.aevaluate(
        run_graph_configured,
        data=examples,
        evaluators=[
            InstructionFollowingEvaluator(),
        ],
        max_concurrency=config.max_concurrency,
        experiment_prefix=config.name,
        num_repetitions=config.num_repetitions,
        upload_results=False
    )
    
    print(f"\n{'='*80}")
    print(f"Completed Experiment: {config.name}")
    print(f"Result: {result}")
    print(f"{'='*80}\n")
    
    return result


async def main():
    """Run all experiments sequentially"""
    print(f"\n{'#'*80}")
    print(f"# Starting Batch Experiment Run")
    print(f"# Total experiments: {len(EXPERIMENT_CONFIGS)}")
    print(f"{'#'*80}\n")
    
    results = {}
    
    for i, config in enumerate(EXPERIMENT_CONFIGS, 0):
        print(f"\nProgress: [{i}/{len(EXPERIMENT_CONFIGS)}]")
        try:
            result = await run_single_experiment(config)
            results[config.name] = {
                "status": "success",
                "result": result
            }
        except Exception as e:
            print(f"❌ Experiment {config.name} failed: {e}")
            results[config.name] = {
                "status": "failed",
                "error": str(e)
            }
    
    # Print summary
    print(f"\n{'#'*80}")
    print(f"# Batch Experiment Summary")
    print(f"{'#'*80}\n")
    
    for exp_name, result in results.items():
        status_icon = "✓" if result["status"] == "success" else "✗"
        print(f"{status_icon} {exp_name}: {result['status']}")
    
    # Save results to file
    results_file = benchmark_path / f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📊 Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())