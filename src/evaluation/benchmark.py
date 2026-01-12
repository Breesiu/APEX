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
# from .dataset_schema import EvaluationDataset, EvaluationExample
from langsmith.schemas import ExampleCreate
import random

# TODO: need to add parse for user to choose version
# graph = create_poster_edit_graph()
experiment_name = "comparison_api"

graph_v2 = create_poster_edit_graph_v3()
mode = 'api'
model='gemini-3-flash-preview'
preserve_runs = False

dataset_name = "FINAL_paper_correction"
version = f"final_v100(nochatgpt_nochatgpt)_{mode}_{model}_{experiment_name}_{dataset_name}_revise_prompt"
# version = f"final_v1_filter{is_filter_applied}_{mode}_{model}_{experiment_name}_NIPS_2023_subset"

iterate_version = ''
iterate_version='user_instruction_significant_revised_elements'
iterate_debug = False

# benchmark_dir = "./benchmark-v1-202511062200"  # relative path
benchmark_dir = "./benchmark_withpostergen_flat" # relative path
benchmark_path = Path(benchmark_dir)

num_repetitions = 1
    
def load_instructions_from_json(json_path: str) -> List[str]:
    """Load user instructions from instruction.json file"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both list and dict formats
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"Error loading instructions from {json_path}: {e}")
        return []

# TODO: make it to class
# async def instruction_following_evaluator(inputs: dict, outputs: dict) -> Dict:
#     pass
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

    def __call__(self, inputs: dict, outputs: dict) -> Dict:
        class ResponseSchema(BaseModel):
            reason: str = Field(..., description="Detailed explanation of the evaluation.")
            score: int = Field(..., description="Score from 0 to 10 indicating how well the instructions were followed.")
            
    
        return {
            'key':"instruction_following_score",
            'score': 8,
            'reason':"Placeholder reason for evaluation."
        }
async def run_graph_v2(inputs: dict) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_api_url = {}
    if model=='qwen3-vl-plus' or model=='qwen-vl-max' or model=='qvq-max-latest':
        model_api_url = {
            'model': model,
            'base_url': "",
            'api_key': ""
        }
    elif model=='gemini-3-flash-preview':
        model_api_url = {
            'model': model,
            'base_url': "", 
            'api_key': "" 
        }

    initial_state = AgentState(
        user_instruction=inputs["user_instruction"],
        pptx_path=inputs["pptx_path"],
        pdf_path=inputs["pdf_path"],
        # output_dir is pdf's name+'_'+user_instruction_no, like Can_LLMs_Really_Learn_to_Translate_a_Low-Resource_Language_from_One_Grammar_Book_0, 
        # output_dir=benchmark_path/f"{inputs['poster_name']}/{mode}_{version}/{inputs['instruction_index']}_{timestamp}/", # output_dir=f"./src/temp/{inputs['poster_name']}_{timestamp}_{inputs['instruction_index']}/",
        output_dir=benchmark_path/f"{inputs['poster_name']}/{mode}_{version}/{inputs['instruction_index']}/", # output_dir=f"./src/temp/{inputs['poster_name']}_{timestamp}_{inputs['instruction_index']}/",
        # output_dir=benchmark_path/f"{inputs['poster_name']}/{mode}_{version}/{inputs['instruction_index']}/", # output_dir=f"./src/temp/{inputs['poster_name']}_{timestamp}_{inputs['instruction_index']}/",

        max_iterations=MAX_ITERATIONS,
        mode=mode,
        experiment_name=experiment_name,
        **model_api_url,
        iterate_version=iterate_version,
        iterate_debug=iterate_debug,
        timestamp=timestamp,
        iteration_count=0, # why should init to 0 rather than default 0?
        paper_related=inputs.get("paper_related", None),
        preserve_runs = preserve_runs

    )
    final_state = graph_v2.invoke(initial_state) # TOR await
    
    # edited_png_path = 
    return {
        # "success": not bool(final_state.error),
        "edited_pptx_path": final_state['current_pptx_path'],

    }

async def main():
    client = Client()
    
    # create dataset with minimal required args (remove invalid empty inputs/outputs)
    
    # Check if dataset already exists
    try:
        # list_datasets returns a generator. We must convert it to a list.
        existing_datasets_list = list(client.list_datasets(dataset_name=dataset_name))
        local = False
        if local:
            dataset = client.clone_public_dataset("")
        else:
            if existing_datasets_list:
                # If the list is not empty, a dataset exists. Use the first one.
                dataset = existing_datasets_list[0]
                print(f"Found existing dataset: {dataset.name}")
            else:
                # If the list is empty, no dataset was found. Create it.
                print(f"Dataset '{dataset_name}' not found. Creating new one.")
                dataset = client.create_dataset(dataset_name=dataset_name)
        
            
    except Exception as e:
        print(f"An unexpected error occurred while trying to get or create the dataset: {e}")
        # Re-raise the exception to stop the script if something truly unexpected goes wrong
        raise e
        
    # Find all poster folders (those containing instruction.json)
    poster_folders = []
    for item in benchmark_path.iterdir():
        if item.is_dir() and (item / "instruction.json").exists():
            poster_folders.append(item)
    
    print(f"Found {len(poster_folders)} poster folders with instruction.json")
    all_examples = []
    
    for poster_folder in poster_folders:
        poster_name = poster_folder.stem
        
        # Load instructions
        instruction_json = poster_folder / "instruction.json"
        instructions = load_instructions_from_json(str(instruction_json))
        
        if not instructions:
            print(f"⚠️  No instructions found in {poster_name}/instruction.json")
            continue
        
        # Find PPTX and PDF files
        pptx_path = poster_folder / "ByPosterGen.pptx"
        pdf_path = poster_folder / "paper.pdf"
        
        # Create examples for each instruction
        for idx, instruction in enumerate(instructions, start=0):
            # if instruction['debug_baseline'] == False:
            #     continue
            # if instruction['new'] == False:
            #     continue
            
            # if not instruction['debug_gemini']:
            #     continue
            example = ExampleCreate(
                id=str(uuid4()),
                inputs={
                    "user_instruction": instruction['operation'].strip() if isinstance(instruction, dict) and 'operation' in instruction else str(instruction).strip(),
                    "pptx_path": pptx_path,
                    "pdf_path": pdf_path,
                    "poster_name": poster_name,
                    "instruction_index": idx,
                    "paper_related": instruction.get('paper_related', None) 
                },
            )
            all_examples.append(example)
    
    print(f"\nCreating {len(all_examples)} examples across {len(poster_folders)} posters...")
    
    # Upload examples in batches
    #NOTE: when you need to add examples, uncomment the following code
    client.create_examples(
        dataset_id=dataset.id,
        examples=all_examples # limit to 2 for debugging
    )
    
    print(f"✓ Successfully created {len(all_examples)} examples")
    print(f"✓ Dataset ID: {dataset.id}")
    print(f"✓ Dataset name: {dataset_name}")
    
    # Print summary statistics
    print("\n" + "="*80)
    print("DATASET SUMMARY")
    print("="*80)
    print(f"Total posters: {len(poster_folders)}")
    print(f"Total examples: {len(all_examples)}")
    print(f"Avg instructions per poster: {len(all_examples)/len(poster_folders):.1f}")
    
    # Show sample poster statistics
    print("\nSample poster details:")
    for poster_folder in poster_folders[:3]:
        instruction_json = poster_folder / "instruction.json"
        instructions = load_instructions_from_json(str(instruction_json))
        print(f"  - {poster_folder.stem}: {len(instructions)} instructions")
    
    result = await client.aevaluate(
        run_graph_v2,
        data=dataset_name,
        evaluators=[
            InstructionFollowingEvaluator(),
            # DynamicLayoutAdaptationEvaluator(),
        ],
        max_concurrency=5,
        experiment_prefix=experiment_name,
        num_repetitions=num_repetitions
    )
    
    print("Evaluation result:", result)
    

if __name__ == "__main__":
    asyncio.run(main())
    # for test
    # benchmark_dir = "./benchmark-v1-202511062200"  # convert it to relative path 

    # poster_folder = Path(benchmark_dir) / "Can_LLMs_Really_Learn_to_Translate_a_Low-Resource_Language_from_One_Grammar_Book/poster_v1.png"
    # print(poster_folder.stem)   
    # print(poster_folder)   
        
    # print(f"Processing poster folder: {poster_folder.absolute}")
    # data = load_instructions_from_json(str(poster_folder / "instruction.json"))
    # print(data)
