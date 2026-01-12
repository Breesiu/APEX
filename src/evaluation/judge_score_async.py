
import os
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from ..tools.image_tools import encode_image_to_base64
from ..tools.pptx_parser import parse_pptx_to_json
from ..tools.pdf_parser import extract_paper_content
from ..schema import PaperContentExtractionResult
from ..tools.utils import extract_llm_result, extract_llm_result_judge
import PyPDF2
from pdf2image import convert_from_path

from io import BytesIO
import asyncio
from ..prompts.llm_judge_prompts import judge_prompt_final
from PIL import Image
# version_prefix = "api_final_v1_filterFalse_api_gemini-3-flash-preview_comparison_api_NIPS_2023_subset"
model = "gemini-3-flash-preview" #"gemini-3-pro-preview"

class ResponseSchema(BaseModel):
    justification: Optional[str] = Field(..., description="Detailed justification of the evaluation.")
    score: Optional[int] = Field(..., description="Score from 0 to 10 indicating how well the instructions were followed.")

class PosterEvaluationResult(BaseModel):
    """Evaluation result for a poster version"""
    instruction_fulfillment: ResponseSchema = Field(..., description="justification and score for instruction fulfillment")
    modification_scope: ResponseSchema = Field(..., description="justification and score for modification scope")
    visual_consistency: ResponseSchema = Field(..., description="justification and score for visual integrity")


class PosterJudge:
    """Judge system for evaluating poster edits"""
    
    def __init__(self, model: str = "gemini-3-flash-preview", max_concurrent: int = 5):
        """Initialize the judge with specified model"""
        
        # Configure model based on type
        self.model = model
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        if model == 'gemini-3-flash-preview':
            from langchain_google_genai import ChatGoogleGenerativeAI # TODO: not use langgraph will be better?
            self.llm = ChatGoogleGenerativeAI( 
                model=model,
                temperature=0,
                api_key=os.getenv("GOOGLE_API_KEY", "EMPTY"),
                base_url=os.getenv("GOOGLE_BASE_URL", "EMPTY"),
                max_output_tokens=4096,
                thinking_level='low',
                include_thoughts=False
            )
        elif model == 'gemini-3-pro-preview':
            from langchain_google_genai import ChatGoogleGenerativeAI
            self.llm = ChatGoogleGenerativeAI( 
                model=model,
                temperature=0.1,
                api_key=os.getenv("GOOGLE_API_KEY", "EMPTY"),
                base_url=os.getenv("GOOGLE_BASE_URL", "EMPTY"),
                max_output_tokens=4096,
                thinking_level='low',
                include_thoughts=False
            )
        else:
            raise ValueError(f"Unsupported model: {model}")

    def _load_paper_content(self, pdf_path: Path, output_dir=None) -> str:
        """Load first 30 pages of paper with images/tables metadata"""
        try:
            
            # Also prepare PDF base64 for first 30 pages
            with open(pdf_path, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                writer = PyPDF2.PdfWriter()
                
                num_pages = min(30, len(reader.pages))
                for i in range(num_pages):
                    writer.add_page(reader.pages[i])
                
                pdf_buffer = BytesIO()
                writer.write(pdf_buffer)
                pdf_bytes = pdf_buffer.getvalue()
            
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            # return paper_content.model_dump_json(indent=2), pdf_base64
            return  [{'type': 'text', 'text': f"\n**Paper Content**\n"},{"type": "file", "source_type": "base64", "name": os.path.basename(pdf_path), "data": pdf_base64}]
        
        except Exception as e:
            print(f"Error loading paper content: {e}")
            images = convert_from_path(str(pdf_path), dpi=80, first_page=1, last_page=30)
            
            image_list = []
            for i, image in enumerate(images):
                image = image.convert("RGBA").quantize(colors=256, method=Image.Quantize.FASTOCTREE)

                buffered = BytesIO()
                image.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                image_list.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                })
            return [{'type': 'text', 'text': f"\n**Paper Content**\n"}] + image_list
            
    
    async def evaluate_poster(
        self,
        user_instruction: str,
        original_png_path: Path,
        edited_png_path: Path,
        original_json_path: Path,
        edited_json_path: Path,
        plan_apis_paths: List[Path],
        pdf_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        needs_paper: bool = False
    ) -> PosterEvaluationResult:
        """
        Evaluate a single edited poster version (async)
        
        Args:
            user_instruction: The editing instruction
            original_png_path: Path to original poster image
            edited_png_path: Path to edited poster image
            original_json_path: Path to original poster JSON
            edited_json_path: Path to edited poster JSON
            plan_apis_paths: List of paths to plan_apis.json files
            pdf_path: Path to paper PDF (if needed)
            output_dir: Output directory for paper extraction
            needs_paper: Whether this instruction requires paper content
        """
        
        async with self.semaphore:
            # Encode images
            original_img_b64 = encode_image_to_base64(original_png_path)
            edited_img_b64 = encode_image_to_base64(edited_png_path)
            
            message_parts = [
                {"type": "text", "text": judge_prompt_final.format(
                    user_instruction = user_instruction
                )}]

        
        # Add paper content if needed
        if needs_paper and pdf_path and output_dir:
            try:
                paper_content_messages = self._load_paper_content(pdf_path)
                
                message_parts.extend(paper_content_messages)
            except Exception as e:
                print(f"Error adding paper content: {e}")
        
        # Add images
        message_parts.extend([
            {"type": "text", "text": "\n**Original Poster:**"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{original_img_b64}"}},
            {"type": "text", "text": "\n**Edited Poster:**"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{edited_img_b64}"}},
        ])
        # Get structured response
        structured_output = False

        
        try:
            message = HumanMessage(content=message_parts)

            if structured_output:
                structured_llm = self.llm.with_structured_output(PosterEvaluationResult)
                # Run synchronous invoke in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, structured_llm.invoke, [message])
            else:
                
                message = HumanMessage(content=message_parts)
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    extract_llm_result_judge, 
                    self.model, 
                    [message], 
                    self.llm, 
                    PosterEvaluationResult
                )
                                         
            return result
        except Exception as e:
            print(f"Error during evaluation: {e}")
            return PosterEvaluationResult(
                instruction_fulfillment=ResponseSchema(score=None, justification=None),
                modification_scope=ResponseSchema(score=None, justification=None),
                visual_consistency=ResponseSchema(score=None, justification=None),
            )


async def evaluate_poster_versions(
    poster_folder: Path,
    instruction_idx: int,
    version_prefix: str,
    judge: PosterJudge
) -> Dict[str, float]:
    """
    Evaluate both v1 and debug_v2 versions of a poster (async)
    
    Returns:
        Dict with keys like 'score_v1' and 'score_debug_v2'
    """
    
    # Load instruction
    with open(poster_folder / "instruction.json", 'r', encoding='utf-8') as f:
        instructions = json.load(f)
    
    if instruction_idx >= len(instructions):
        raise ValueError(f"Instruction index {instruction_idx} out of range")
    
    instruction_obj = instructions[instruction_idx]
    user_instruction = instruction_obj.get('operation', '')
    needs_paper = instruction_obj.get('paper_related', False)
    
    # Paths
    # original_png_labeled = poster_folder / "ByPosterGen_labeled.png"
    original_png = poster_folder / "ByPosterGen.png"
    original_json = poster_folder / "poster_json.json"
    pdf_path = poster_folder / "paper.pdf" if needs_paper else None
    
    results = {}
    #     instructions_all = json.load(f)
    # results = instructions_all[instruction_idx].get('score_judge', {})
    # Evaluate v1
    v1_folder = poster_folder / version_prefix / str(instruction_idx)
    try:
        if v1_folder.exists():
            v1_png = v1_folder / "poster_v1.png"
            v1_json = v1_folder / "poster_v1.json"
            v1_plan_apis = [v1_folder / "plan_apis.json"]
            
            if v1_png.exists():
                result_v1 = await judge.evaluate_poster(
                    user_instruction=user_instruction,
                    original_png_path=original_png,
                    edited_png_path=v1_png,
                    original_json_path=original_json,
                    edited_json_path=v1_json,
                    plan_apis_paths=v1_plan_apis,
                    pdf_path=pdf_path,
                    output_dir=v1_folder,
                    needs_paper=needs_paper
                )
                if isinstance(result_v1, BaseModel):
                    results[f'score_{version_prefix}_v1'] = result_v1.instruction_fulfillment.model_dump()
                    results[f'modification_scope_{version_prefix}_v1'] = result_v1.modification_scope.model_dump()
                    results[f'visual_consistency_{version_prefix}_v1'] = result_v1.visual_consistency.model_dump()
                else:
                    results[f'score_{version_prefix}_v1'] = result_v1
                    results[f'modification_scope_{version_prefix}_v1'] = result_v1
                    results[f'visual_consistency_{version_prefix}_v1'] = result_v1

            else:  # TODO:check
                results[f'score_{version_prefix}_v1'] = {'score':0, 'justification': ""}
                results[f'modification_scope_{version_prefix}_v1'] = {'score':10, 'justification': ""}
                results[f'visual_consistency_{version_prefix}_v1'] = {'score':0, 'justification': ""}
            
            # Evaluate debug_v2
            debug_v2_files = list(v1_folder.glob("poster_debug_v2*.png"))
            if debug_v2_files:
                # Use the latest debug_v2 file
                debug_v2_png = sorted(debug_v2_files)[-1]
                debug_v2_json = debug_v2_png.with_suffix('.json')
                
                # Concatenate plan_apis from both v1 and review adaptation
                review_files = list(v1_folder.glob("review_adaption_result_*.json"))
                v2_plan_apis = v1_plan_apis + review_files
                
                if len(review_files) > 0 and debug_v2_png.exists():
                    result_v2 = await judge.evaluate_poster(
                        user_instruction=user_instruction,
                        original_png_path=original_png,
                        edited_png_path=debug_v2_png,
                        original_json_path=original_json,
                        edited_json_path=debug_v2_json,
                        plan_apis_paths=v2_plan_apis,
                        pdf_path=pdf_path,
                        output_dir=v1_folder,
                        needs_paper=needs_paper
                    )
                    suffix = debug_v2_png.stem.split("poster_debug_")[-1]
                    results[f'score_{version_prefix}_debug_v2'] = result_v2.instruction_fulfillment.model_dump()
                    results[f'modification_scope_{version_prefix}_debug_v2'] = result_v2.modification_scope.model_dump()
                    results[f'visual_consistency_{version_prefix}_debug_v2'] = result_v2.visual_consistency.model_dump()
                elif len(review_files) > 0:
                    results[f'score_{version_prefix}_debug_v2'] = results.get(f'score_{version_prefix}_v1', {})
                    results[f'modification_scope_{version_prefix}_debug_v2'] = results.get(f'modification_scope_{version_prefix}_v1', {})
                    results[f'visual_consistency_{version_prefix}_debug_v2'] = results.get(f'visual_consistency_{version_prefix}_v1', {})
                    
                    
            else:
                results[f'score_{version_prefix}_debug_v2'] = results.get(f'score_{version_prefix}_v1', {})
                results[f'modification_scope_{version_prefix}_debug_v2'] = results.get(f'modification_scope_{version_prefix}_v1', {})
                results[f'visual_consistency_{version_prefix}_debug_v2'] = results.get(f'visual_consistency_{version_prefix}_v1', {})
                

            # Evaluate debug_v3
            debug_v3_files = list(v1_folder.glob("poster_debug_v3*.png"))
            if debug_v3_files:
                # Use the latest debug_v2 file
                debug_v3_png = sorted(debug_v3_files)[-1]
                debug_v3_json = debug_v3_png.with_suffix('.json')
                
                if debug_v3_png.exists():
                    result_v3 = await judge.evaluate_poster(
                        user_instruction=user_instruction,
                        original_png_path=original_png,
                        edited_png_path=debug_v3_png,
                        original_json_path=original_json,
                        edited_json_path=debug_v2_json,
                        plan_apis_paths=v2_plan_apis,
                        pdf_path=pdf_path,
                        output_dir=v1_folder,
                        needs_paper=needs_paper
                    )
                    suffix = debug_v2_png.stem.split("poster_debug_")[-1]
                    results[f'score_{version_prefix}_debug_v3'] = result_v3.instruction_fulfillment.model_dump()
                    results[f'modification_scope_{version_prefix}_debug_v3'] = result_v3.modification_scope.model_dump()
                    results[f'visual_consistency_{version_prefix}_debug_v3'] = result_v3.visual_consistency.model_dump()
                elif len(review_files) > 0:
                    results[f'score_{version_prefix}_debug_v3'] = results.get(f'score_{version_prefix}_debug_v2', {})
                    results[f'modification_scope_{version_prefix}_debug_v3'] = results.get(f'modification_scope_{version_prefix}_debug_v2', {})
                    results[f'visual_consistency_{version_prefix}_debug_v3'] = results.get(f'visual_consistency_{version_prefix}_debug_v2', {})
                    
                    
            else:
                results[f'score_{version_prefix}_debug_v3'] = results.get(f'score_{version_prefix}_debug_v2', {})
                results[f'modification_scope_{version_prefix}_debug_v3'] = results.get(f'modification_scope_{version_prefix}_debug_v2', {})
                results[f'visual_consistency_{version_prefix}_debug_v3'] = results.get(f'visual_consistency_{version_prefix}_debug_v2', {})
            debug_v4_files = list(v1_folder.glob("poster_debug_v4*.png"))
            if debug_v4_files:
                # Use the latest debug_v2 file
                debug_v4_png = sorted(debug_v4_files)[-1]
                debug_v4_json = debug_v4_png.with_suffix('.json')
                
                if debug_v4_png.exists():
                    result_v4 = await judge.evaluate_poster(
                        user_instruction=user_instruction,
                        original_png_path=original_png,
                        edited_png_path=debug_v4_png,
                        original_json_path=original_json,
                        edited_json_path=debug_v4_json,
                        plan_apis_paths=v2_plan_apis,
                        pdf_path=pdf_path,
                        output_dir=v1_folder,
                        needs_paper=needs_paper
                    )
                    suffix = debug_v4_png.stem.split("poster_debug_")[-1]
                    results[f'score_{version_prefix}_debug_v4'] = result_v4.instruction_fulfillment.model_dump()
                    results[f'modification_scope_{version_prefix}_debug_v4'] = result_v4.modification_scope.model_dump()
                    results[f'visual_consistency_{version_prefix}_debug_v4'] = result_v4.visual_consistency.model_dump()
                elif len(review_files) > 0:
                    results[f'score_{version_prefix}_debug_v4'] = results.get(f'score_{version_prefix}_debug_v3', {})
                    results[f'modification_scope_{version_prefix}_debug_v4'] = results.get(f'modification_scope_{version_prefix}_debug_v3', {})
                    results[f'visual_consistency_{version_prefix}_debug_v4'] = results.get(f'visual_consistency_{version_prefix}_debug_v3', {})
            else:
                results[f'score_{version_prefix}_debug_v4'] = results.get(f'score_{version_prefix}_debug_v3', {})
                results[f'modification_scope_{version_prefix}_debug_v4'] = results.get(f'modification_scope_{version_prefix}_debug_v3', {})
                results[f'visual_consistency_{version_prefix}_debug_v4'] = results.get(f'visual_consistency_{version_prefix}_debug_v3', {})
                
                
            image_file = v1_folder / "poster_v1_image.png"

            if image_file.exists():
                result_v_image = await judge.evaluate_poster(
                    user_instruction=user_instruction,
                    original_png_path=original_png,
                    edited_png_path=image_file,
                    original_json_path=original_json,
                    edited_json_path=None,
                    plan_apis_paths=None,
                    pdf_path=pdf_path,
                    output_dir=v1_folder,
                    needs_paper=needs_paper
                )
                results[f'score_{version_prefix}_v1_image'] = result_v_image.instruction_fulfillment.model_dump()
                results[f'modification_scope_{version_prefix}_v1_image'] = result_v_image.modification_scope.model_dump()
                results[f'visual_consistency_{version_prefix}_v1_image'] = result_v_image.visual_consistency.model_dump()
            else:
                results[f'score_{version_prefix}_v1_image'] = {}
                results[f'modification_scope_{version_prefix}_v1_image'] = {}
                results[f'visual_consistency_{version_prefix}_v1_image'] = {}
    except Exception as e:
        print(f"Error evaluating poster versions in {poster_folder.name} instruction {instruction_idx}: {e}")
    return results

import random
async def batch_evaluate_benchmark(
    benchmark_dir: str = "./benchmark_withpostergen_flat",
    version_prefixes: List[str] = None,
    model: str = "gemini-3-flash-preview",
    summary_path_suffix: str = "1",
    max_concurrent: int = 100
):
    """
    Batch evaluate all posters in benchmark directory for multiple version_prefixes (async)
    """
    if version_prefixes is None:
        version_prefixes = [version_prefix]  # Use global default
    
    benchmark_path = Path(benchmark_dir)
    judge = PosterJudge(model=model, max_concurrent=max_concurrent)

    # Find all poster folders
    poster_folders = [f for f in sorted(benchmark_path.iterdir()) if f.is_dir() and (f / "instruction.json").exists()]
    # for poster_folder in poster_folders:
    #     print(f"\nPreparing: {poster_folder.name}")
    #         # Load instructions
    #     with open(poster_folder / "instruction.json", 'r', encoding='utf-8') as f:
    #         instructions = json.load(f)
        
    #     # Prepare tasks for each instruction
    #     for idx, instruction_obj in enumerate(instructions):
    #         if random.random() > 0.4:
    #             continue
            # instructions_filter = 
            
    print(f"Found {len(poster_folders)} poster folders")
    print(f"Evaluating {len(version_prefixes)} version prefixes: {version_prefixes}")
    results = []
    # Process each version_prefix sequentially to maintain order
    for version_prefix_item in version_prefixes:
        print(f"\n{'='*80}")
        print(f"Processing version_prefix: {version_prefix_item}")
        print(f"{'='*80}")
        summary_results = []
        summary_path = benchmark_path / f"{version_prefix_item}_v{summary_path_suffix}.json"
        # counter = 1
        # while summary_path.exists():
        #     counter += 1
        #     summary_path = benchmark_path / f"{version_prefix_item}_v{counter}.json"
        
        # Collect all evaluation tasks for this version_prefix in order
        tasks = []
        task_metadata = []
        cnt = 0
        for poster_folder in poster_folders:
            print(f"\nPreparing: {poster_folder.name}")
            # if cnt > 50:
            #     break
            # Load instructions
            with open(poster_folder / "instruction.json", 'r', encoding='utf-8') as f:
                instructions = json.load(f)
            
            # Prepare tasks for each instruction
            for idx, instruction_obj in enumerate(instructions):
                    
                    
                # if not idx == 1 or not poster_folder.name == "ICLR-2025-14-OSDA_AGENT_LEVERAGING_LARGE_LANGUAGE":
                #     continue
                print(f"  Queuing instruction {idx}...")
                cnt += 1

                task = evaluate_poster_versions(
                    poster_folder=poster_folder,
                    instruction_idx=idx,
                    version_prefix=version_prefix_item,
                    judge=judge
                )
                tasks.append(task)
                task_metadata.append({
                    'poster_folder': poster_folder,
                    'instruction_idx': idx,
                    'instruction_obj': instruction_obj
                })
                # results.append({"a":1})
        
        print(f"\nExecuting {len(tasks)} evaluation tasks for {version_prefix_item}...")
        
        # Execute all tasks and maintain order
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results in order
        for (task_meta, scores) in zip(task_metadata, results):
            poster_folder = task_meta['poster_folder']
            idx = task_meta['instruction_idx']
            instruction_obj = task_meta['instruction_obj']
            
            if isinstance(scores, Exception):
                print(f"  Error in {poster_folder.name} instruction {idx}: {scores}")
                continue
            
            if scores != {}:
                summary_results.append({
                    'poster_folder': poster_folder.name,
                    'instruction_idx': idx,
                    'instruction': instruction_obj.get('operation', ''),
                    'paper_related': instruction_obj.get('paper_related', False),
                    'difficulty': instruction_obj.get('difficulty', False),

                    'score_judge': scores
                })
                
                # Save incrementally
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_results, f, indent=2, ensure_ascii=False)

                print(f"  ✓ Completed {poster_folder.name} instruction {idx}")
        print(f"\n✓ Completed evaluation for {version_prefix_item}. Results saved to {summary_path}")
    # print(json.dump(summary_results, f, indent=2, ensure_ascii=False))
    print("\n✓ All version_prefixes evaluated!")


if __name__ == "__main__":
    # Run batch evaluation with multiple version_prefixes
    version_prefixes_to_evaluate = []
    # 定义父目录
    # "./benchmark_withpostergen_flat",
    base_dir = Path("benchmark_withpostergen_flat/ICML-2025-35-Rethink_GraphODE_Generalization_within_Coupled_Dynamical_System/")
    for dir_path in base_dir.glob("**/api_v12_api_qwen3-vl-plus_debug*"):
        
        version_prefixes_to_evaluate += [dir_path.name]
        print(version_prefixes_to_evaluate)

    version_prefixes_to_evaluate = ['benchmark']#,
    asyncio.run(batch_evaluate_benchmark(
        benchmark_dir="./benchmark_withpostergen_flat",
        version_prefixes=version_prefixes_to_evaluate,
        model=model,
        summary_path_suffix="1",
        max_concurrent=1  # Control concurrent API calls
    ))