from typing import Optional, List, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from ..schema import AgentState, PaperContent, PaperUnderstandingToolInput, PaperUnderstandingToolOutput, PaperContentExtractionResult
from ..prompts.content_prompts import PAPER_UNDERSTANDING_PROMPT_TOOL_GEMINI

# Use Qwen-VL or Qwen-Plus for paper understanding
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from ..config import QWEN3_VL_8B_LOCAL_ENDPOINT, PAPER_UNDERSTANDING_MODEL
import os   
import base64
from pdf2image import convert_from_path
import asyncio
_MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "100"))
_LLM_SEM = asyncio.Semaphore(_MAX_CONCURRENCY)
from ..tools.utils import _invoke_with_retries, _ainvoke_with_retries
from io import BytesIO
from langchain_core.callbacks import UsageMetadataCallbackHandler
from ..tools.pdf_parser import extract_paper_content
from ..tools.image_tools import convert_pptx_to_png, encode_image_to_base64
import json
from PIL import Image
from dotenv import load_dotenv
load_dotenv()


def create_paper_understanding_tool(state: AgentState):
    """
    Factory function to create paper understanding tool with access to state.
    """
    @tool
    async def paper_understanding_tool(query: str) -> str: #target_sections: Optional[List[str]] = None) -> str:
        """
        Extract and organize content from the research paper based on user's edit instruction.
        Use this tool when you need paper content for tasks like:
        - Adding new sections from the paper
        - Expanding existing text with paper content
        - Finding relevant figures/tables from the paper
        
        Args:
            query: Specific contents(text/image) need from the paper
        
        Returns:
            Structured paper content relevant to the query
        """
            # target_sections: Optional list of sections to focus on

        logger = state.logger
        logger.info("\n" + "="*60)
        logger.info("AGENT: Paper Understanding_TOOL")
        logger.info("="*60)
        if not state.no_vlm_in_paper_understanding_tool:
            if 'qwen' in state.model or 'Qwen' in state.model:
                paper_understanding_llm = ChatOpenAI(
                    model=state.model or PAPER_UNDERSTANDING_MODEL,
                    temperature=0.1,    
                    base_url=state.base_url or os.getenv("ALIBABA_BASE_URL", "EMPTY"),
                    api_key=state.api_key or os.getenv("ALIBABA_API_KEY", "EMPTY"),
                    max_tokens=4096,  
                    # frequency_penalty=0.1
                )
            elif state.model.startswith('gemini'):
                from langchain_google_genai import ChatGoogleGenerativeAI
                paper_understanding_llm = ChatGoogleGenerativeAI(
                    model=state.model or PAPER_UNDERSTANDING_MODEL,
                    temperature=0.1,
                    api_key=os.getenv("GOOGLE_API_KEY", state.api_key or "EMPTY"),
                    base_url=state.base_url or os.getenv("GOOGLE_BASE_URL", "EMPTY"),
                    max_output_tokens=4096,
                    thinking_level='low',
                )            
        if not state.pdf_path:
            error_msg = "Paper content required but no PDF path provided"
            logger.error(f"ERROR: {error_msg}")
            return {"error": error_msg}
        # Extract paper content
        _, images_info, tables_info = extract_paper_content(
            state.pdf_path, 
            state.output_dir
        )
        
        # Create extraction result
        paper_content_extract_result = PaperContentExtractionResult(
            images_info={v['image_path']: v['caption'] for k, v in images_info.items()},
            tables_info={v['table_path']: v['caption'] for k, v in tables_info.items()}
        )
        # Prepare tool input # TODO: make it concise
        input = PaperUnderstandingToolInput(
            pdf_path=state.pdf_path,
            user_instruction=state.user_instruction,
            poster_json=(state.poster_json.model_dump() if hasattr(state.poster_json, "dict") else state.poster_json),
            # execution_plan=getattr(state.plan, "plan", None),        
            # target_sections_hint=target_sections,
            query=query
        )

        # Step 2: Prepare prompt with poster + instruction + (optional) plan summary # TODO: remove or replace poster_json, filterout position info? png image?
        png_with_labels_path = convert_pptx_to_png(state.current_pptx_path)
        image_base64 = encode_image_to_base64(png_with_labels_path)            # TODO: message's order? prompt_text first?
        if 'qwen' in state.model or 'Qwen' in state.model:    # TODO: poster_json? image's resolution?
            ocr = True # for qwen-vl-30B
            if not ocr:
                prompt_text = PAPER_UNDERSTANDING_PROMPT_TOOL_GEMINI.format(
                    paper_content=paper_content_extract_result.model_dump_json(indent=2),
                    # user_instruction=input.user_instruction,
                    query=input.query,
                    # target_sections=", ".join(target_sections) if target_sections else "",
                    # poster_json=input.poster_json
                )
                prompt = [
                    HumanMessage(content=[{"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}])
                ]
            else:
                paper_content_extract_result = PaperContentExtractionResult(
                    images_info={v['image_path']: v['caption'] for k, v in images_info.items()},
                    tables_info={v['table_path']: v['caption'] for k, v in tables_info.items()}
                )
                images = convert_from_path(str(state.pdf_path), dpi=80, first_page=1, last_page=30)
                image_list = []
                for i, image in enumerate(images):
                    image = image.convert("RGBA").quantize(colors=256, method=Image.Quantize.FASTOCTREE)
                    buffered = BytesIO()
                    image.save(buffered, format="PNG", optimize=True)
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    image_list.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                    })
                prompt_text = PAPER_UNDERSTANDING_PROMPT_TOOL_GEMINI.format(
                    images_tables_info=paper_content_extract_result.model_dump_json(indent=2),
                    query=input.query,
                )                
                prompt = [HumanMessage(
                        content= image_list + [
                            {"type": "text", "text": prompt_text},
                        ] + [{"type": "text", "text": "Poster image:"}] + 
                        [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}]
                    )
                ]
            if state.no_vlm_in_paper_understanding_tool:
                logger.info("Skipping: Paper understanding tool disabled")
                path_to_info = {}
                for info in images_info.values():
                    if 'image_path' in info:
                        path_to_info[os.path.basename(info['image_path'])] = {
                            "caption": info.get("caption"),
                            "width": info.get("width"),
                            "height": info.get("height"),
                            "figure_aspect": info.get("figure_aspect")
                        }
                for info in tables_info.values():
                    if 'table_path' in info:
                        path_to_info[os.path.basename(info['table_path'])] = {
                            "caption": info.get("caption"),
                            "width": info.get("width"),
                            "height": info.get("height"),
                            "figure_aspect": info.get("figure_aspect")
                        }
                return {"paper_baseline": [
                    {'type': 'text', 'text': 'Paper content:'}] + image_list +
                    [{"type": "text", "text": paper_content_extract_result.model_dump_json(indent=2)}]
                    + [{"type": "text", "text": "visuals details:"}] +
                    [{"type": "text", "text": json.dumps(path_to_info, indent=2)}]
                    }
                                           
                pass
                
        elif state.model.startswith('gemini'):
            paper_content_extract_result = PaperContentExtractionResult(
                images_info={v['image_path']: v['caption'] for k, v in images_info.items()},
                tables_info={v['table_path']: v['caption'] for k, v in tables_info.items()}
            )
            # pdf_bytes = open(state.pdf_path, "rb").read()
            # TODO: resolution of pdf and image
            import PyPDF2
            try:
                if state.use_paper_pdf_directly:
                    with open(state.pdf_path, "rb") as pdf_file:
                        reader = PyPDF2.PdfReader(pdf_file)
                        writer = PyPDF2.PdfWriter()
                        
                        # Add only first 30 pages
                        num_pages = min(30, len(reader.pages))
                        for i in range(num_pages):
                            writer.add_page(reader.pages[i])
                        
                        # Write to bytes buffer
                        pdf_buffer = BytesIO()
                        writer.write(pdf_buffer)
                        pdf_bytes = pdf_buffer.getvalue()
                        
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')        
                    prompt_text = PAPER_UNDERSTANDING_PROMPT_TOOL_GEMINI.format(
                        images_tables_info=paper_content_extract_result.model_dump_json(indent=2),
                        query=input.query,
                    )
                    prompt = [
                        HumanMessage(content=[
                            {"type": "file", "source_type": "base64", "name": os.path.basename(state.pdf_path), "data": pdf_base64},
                            {"type": "text", "text": prompt_text},
                            {"type": "text", "text": "Poster image:"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                            ])
                    ]
                    if state.no_vlm_in_paper_understanding_tool:
                        logger.info("Skipping: Paper understanding tool disabled")
                        path_to_info = {}
                        for info in images_info.values():
                            if 'image_path' in info:
                                path_to_info[os.path.basename(info['image_path'])] = {
                                    "caption": info.get("caption"),
                                    "width": info.get("width"),
                                    "height": info.get("height"),
                                    "figure_aspect": info.get("figure_aspect")
                                }
                        for info in tables_info.values():
                            if 'table_path' in info:
                                path_to_info[os.path.basename(info['table_path'])] = {
                                    "caption": info.get("caption"),
                                    "width": info.get("width"),
                                    "height": info.get("height"),
                                    "figure_aspect": info.get("figure_aspect")
                                }
                        return {"paper_baseline": [
                            {'type': 'text', 'text': 'Paper content:'},
                            {"type": "file", "source_type": "base64", "name": os.path.basename(state.pdf_path), "data": pdf_base64},
                            {"type": "text", "text": paper_content_extract_result.model_dump_json(indent=2)},
                            {"type": "text", "text": "visuals details:"},
                            {"type": "text", "text": json.dumps(path_to_info, indent=2)}
                                                ]}
                else:
                    images = convert_from_path(str(state.pdf_path), dpi=80, first_page=1, last_page=30)
                    image_list = []
                    for i, image in enumerate(images):
                        image = image.convert("RGBA").quantize(colors=256, method=Image.Quantize.FASTOCTREE)

                        buffered = BytesIO()
                        image.save(buffered, format="PNG", optimize=True)
                        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        
                        image_list.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                        })
                    prompt_text = PAPER_UNDERSTANDING_PROMPT_TOOL_GEMINI.format(
                        images_tables_info=paper_content_extract_result.model_dump_json(indent=2),
                        query=input.query,
                    )                
                    prompt = [HumanMessage(
                            content= image_list + [
                                {"type": "text", "text": prompt_text},
                            ] + [{"type": "text", "text": "Poster image:"}] + 
                            [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}]
                        )
                    ]
                    if state.no_vlm_in_paper_understanding_tool:
                        path_to_info = {}
                        for info in images_info.values():
                            if 'image_path' in info:
                                path_to_info[os.path.basename(info['image_path'])] = {
                                    "caption": info.get("caption"),
                                    "width": info.get("width"),
                                    "height": info.get("height"),
                                    "figure_aspect": info.get("figure_aspect")
                                }
                        for info in tables_info.values():
                            if 'table_path' in info:
                                path_to_info[os.path.basename(info['table_path'])] = {
                                    "caption": info.get("caption"),
                                    "width": info.get("width"),
                                    "height": info.get("height"),
                                    "figure_aspect": info.get("figure_aspect")
                                }
                        logger.info("Skipping: Paper understanding tool disabled")
                        return {"paper_baseline": [
                            {'type': 'text', 'text': 'Paper content:'}] + image_list +
                            [{"type": "text", "text": paper_content_extract_result.model_dump_json(indent=2)}] + [{"type": "text", "text": "visuals details:"}] +
                            [{"type": "text", "text": json.dumps(path_to_info, indent=2)}]
                            }
            except Exception as e:
                    images = convert_from_path(str(state.pdf_path), dpi=80, first_page=1, last_page=30)
                    image_list = []
                    for i, image in enumerate(images):
                        image = image.convert("RGBA").quantize(colors=256, method=Image.Quantize.FASTOCTREE)

                        buffered = BytesIO()
                        image.save(buffered, format="PNG", optimize=True)
                        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        
                        image_list.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                        })
                    prompt_text = PAPER_UNDERSTANDING_PROMPT_TOOL_GEMINI.format(
                        images_tables_info=paper_content_extract_result.model_dump_json(indent=2),
                        query=input.query,
                    )                
                    prompt = [HumanMessage(
                            content= image_list + [
                                {"type": "text", "text": prompt_text},
                            ] + [{"type": "text", "text": "Poster image:"}] + 
                            [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}]
                        )
                    ]
                    if state.no_vlm_in_paper_understanding_tool:
                        path_to_info = {}
                        for info in images_info.values():
                            if 'image_path' in info:
                                path_to_info[os.path.basename(info['image_path'])] = {
                                    "caption": info.get("caption"),
                                    "width": info.get("width"),
                                    "height": info.get("height"),
                                    "figure_aspect": info.get("figure_aspect")
                                }
                        for info in tables_info.values():
                            if 'table_path' in info:
                                path_to_info[os.path.basename(info['table_path'])] = {
                                    "caption": info.get("caption"),
                                    "width": info.get("width"),
                                    "height": info.get("height"),
                                    "figure_aspect": info.get("figure_aspect")
                                }
                        logger.info("Skipping: Paper understanding tool disabled")
                        return {"paper_baseline": [
                            {'type': 'text', 'text': 'Paper content:'}] + image_list +
                            [{"type": "text", "text": paper_content_extract_result.model_dump_json(indent=2)}] +  [{"type": "text", "text": "visuals details:"}] +
                            [{"type": "text", "text": json.dumps(path_to_info, indent=2)}]
                            }
                
        
        # Step 3: Ask MLLM to curate and organize content into structured output
        try:
            extracted_visuals_details = {}

            try:
                cb = UsageMetadataCallbackHandler()
                structured = paper_understanding_llm.with_structured_output(PaperUnderstandingToolOutput) # TODO: when structured output, how the model know the detailed meaning of each field??
                async with _LLM_SEM:

                    result: PaperUnderstandingToolOutput = await _ainvoke_with_retries(
                        structured,
                        prompt,
                        logger=logger,
                        max_retries=10,
                        config={"callbacks": [cb]},
                    )
                logger.info(cb.usage_metadata)
            except:
                cb = UsageMetadataCallbackHandler()
                structured = paper_understanding_llm.with_structured_output(PaperUnderstandingToolOutput)
                async with _LLM_SEM:

                    result: PaperUnderstandingToolOutput = await _ainvoke_with_retries(
                        structured,
                        prompt,
                        logger=logger,
                        max_retries=10,
                        config={"callbacks": [cb]},
                    )
                logger.info(cb.usage_metadata)
            # Extract detailed info for selected figures/tables
            if result.extracted_figures_tables:
                # Create lookup maps
                path_to_info = {}
                for info in images_info.values():
                    if 'image_path' in info:
                        path_to_info[info['image_path']] = info
                for info in tables_info.values():
                    if 'table_path' in info:
                        path_to_info[info['table_path']] = info

                for section, path in result.extracted_figures_tables.items():
                    if path in path_to_info:
                        info = path_to_info[path]
                        extracted_visuals_details[os.path.basename(path)] = {
                            "caption": info.get("caption"),
                            "width": info.get("width"),
                            "height": info.get("height"),
                            "figure_aspect": info.get("figure_aspect")
                        }

                # Post-trim long sections
                if input.max_chars_per_section and result.extracted_text_contents:
                    for k, v in list(result.extracted_text_contents.items()):
                        if isinstance(v, str) and len(v) > input.max_chars_per_section:
                            result.extracted_text_contents[k] = v[:input.max_chars_per_section] + "..."
                logger.info(f"Generated curated_payload: {result.model_dump_json(indent=2)}")
                logger.info(f"Selected visuals details: {extracted_visuals_details}")
                logger.info("Paper Understanding Agent_V2 - Completed")
                logger.info("="*60)
                
        except Exception as e:
                # Safe fallback: basic section passthrough (cap length)
            extracted_sections: Dict[str, str] = {}
            result = PaperUnderstandingToolOutput(
                # thought_process="",
                extracted_text_contents=extracted_sections,
                extracted_figures_tables = {},
                integration_suggestions= [],
                # notes=f"MLLM curation failed: {e}. Returned raw truncated sections."
            )
            extracted_visuals_details = {}
            logger.info(f"Generated curated_payload: {result.model_dump_json(indent=2)}")

            logger.info("Paper Understanding Agent_V2 - Exception")
            logger.info("="*60)  
                    

        return {"paper_content_extracted": result,"extracted_visuals_details": extracted_visuals_details}
        
    return paper_understanding_tool

# def paper_understanding_tool