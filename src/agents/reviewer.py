from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from ..schema import AgentState, PosterJSON, ReviewAdaptionResultNew
from ..prompts.review_layout_prompts import REVIEW_ADAPTION_PROMPT_ITERATIVE_SIGNIFICANTLY_new
from ..tools.image_tools import convert_pptx_to_png, encode_image_to_base64
from ..tools.pptx_parser import parse_pptx_to_json, PosterFilter, parse_pptx_to_json_for_review
from ..tools.utils import extract_llm_result
# Use Qwen-VL for visual review
from langchain_openai import ChatOpenAI
from ..config import QWEN3_VL_8B_LOCAL_ENDPOINT, REVIEW_MODEL, PLANNER_MODEL
import os   
from dotenv import load_dotenv
load_dotenv()
import json
import re
from ..tools.utils import _invoke_with_retries
import asyncio

# Global limiter for all LLM calls in this module
_MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "100"))
_LLM_SEM = asyncio.Semaphore(_MAX_CONCURRENCY)
    
async def review_adaption_agent(state: AgentState) -> dict:
    """
    Combined Review and Optimization Agent.
    Reviews edited poster and dynamically adapts if needed.
    """
    logger = state.logger
    logger.info("\n" + "="*60)
    logger.info("AGENT: Review Adaption Agent")
    logger.info("="*60)
    
    from ..agents.content_editor import get_api_details
    
    # Initialize LLM
    if 'qwen' in state.model or 'Qwen' in state.model:
        adaption_llm = ChatOpenAI(
            model=state.model or PLANNER_MODEL,
            temperature=0.1, # 0.1
            base_url=state.base_url or os.getenv("ALIBABA_BASE_URL", "EMPTY"),
            api_key=state.api_key or os.getenv("ALIBABA_API_KEY", "EMPTY"),
            max_tokens=4096,
        )
    elif state.model.startswith('gemini'):
        from langchain_google_genai import ChatGoogleGenerativeAI
        adaption_llm = ChatGoogleGenerativeAI(
            model=state.model or PLANNER_MODEL,
            temperature=0.1,
            api_key=os.getenv("GOOGLE_API_KEY", state.api_key or "EMPTY"),
            base_url=state.base_url or os.getenv("GOOGLE_BASE_URL", "EMPTY"),
            max_output_tokens=4096,
            thinking_level='low',   #'low',
            include_thoughts=False,  # Include reasoning steps
        )
    # Parse current poster state
    try:
        current_poster_json = state.current_poster_json = parse_pptx_to_json_for_review(state.current_pptx_path)
        # logger.info(f"Parsed current poster JSON for review with {current_poster_json.model_dump_json(indent=2, exclude_unset=True)} elements.")
    except Exception as e:
        logger.error(f"Failed to parse PPTX for review: {e}")
        return {"error": f"Failed to parse PPTX for review: {e}"}
    
    # Convert posters to PNG 
    original_png_path_with_labels = convert_pptx_to_png(state.pptx_path)
    edited_png_path_with_labels = convert_pptx_to_png(state.current_pptx_path)
    
    # Encode images
    original_base64 = encode_image_to_base64(original_png_path_with_labels)
    edited_base64 = encode_image_to_base64(edited_png_path_with_labels)
    
    # Prepare prompt # TODO: need filter? if filter, when the surrounding element are not included, may constrain the adaption 
    continue_messages = False
    ablation = ""
    if not continue_messages:
        revised_json_increment = PosterJSON(**PosterFilter.filter_revised_json(
            original_json=state.poster_json,
            revised_json=current_poster_json,
            all_revised_field=True if state.iterate_version == 'all_revised_field' else False,
        ))
        
        plan_apis, paper_content_extracted = None, None
        with open(state.output_dir / "plan_apis.json", "r") as f:
            plan_apis = json.load(f)
        if (state.output_dir / "paper_content_extracted.json").exists():
            with open(state.output_dir / "paper_content_extracted.json", "r") as f:
                paper_content_extracted = f.read()
        if (state.output_dir/ "extracted_visuals_details.json").exists():
            with open(state.output_dir / "extracted_visuals_details.json", "r") as f:
                state.extracted_visuals_details = json.load(f)
        prompt_text = REVIEW_ADAPTION_PROMPT_ITERATIVE_SIGNIFICANTLY_new.substitute(
            user_instruction=state.user_instruction,
            ablation = ablation, 
            plan = json.dumps(plan_apis, indent=2) if plan_apis else "Not available",
            poster_json = state.poster_json.model_dump_json(indent=2, exclude_unset=True, exclude_defaults=True, exclude={'elements': {'__all__': {'runs': True}}}) if not state.preserve_runs else state.poster_json.model_dump_json(indent=2, exclude_unset=True, exclude_defaults=True,),
            revised_json_increment=revised_json_increment.model_dump_json(indent=2, exclude_none=True,exclude_defaults=True, exclude={'elements': {'__all__': {'runs': True}}}),
            paper_content_extracted=paper_content_extracted if paper_content_extracted else "Not available",
            extracted_visuals_details=json.dumps(state.extracted_visuals_details, indent=2) if state.extracted_visuals_details else "Not available",
            python_functions_api=get_api_details(),
        )
    
    # Create message with both images
    with open(state.output_dir / f"revised_json_increment_{continue_messages}_{state.timestamp}.json", "w") as f:
        f.write(prompt_text)
    if not continue_messages:
        message_content = [
            {"type": "text", "text": prompt_text},
            {"type": "text", "text": f"Image #1: Original Poster before editing {ablation}:"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{original_base64}"}
            },
            {"type": "text", "text": f"Image #2: Edited Poster after executing api list provided above {ablation}:"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{edited_base64}"}
            },
        ]
    
        messages = messages_this_agent = [HumanMessage(content=message_content)]
        if state.iterate_debug:
            state.iteration_count += 2

        
        messages_this_agent = [HumanMessage(content=message_content)]

        messages = state.messages + messages_this_agent
    
    # # Get structured output
    # structured_llm = adaption_llm.with_structured_output(ReviewAdaptionResult)
    
    try:
        # with open(state.output_dir / f"review_prompt_{continue_messages}_{state.timestamp}.jsonl", "w") as f:
        #     for msg in messages:
        #         f.write(msg.model_dump_json() + "\n")
        if 'qwen' in state.model or 'Qwen' in state.model or state.model.startswith('gemini'):
            try:
                # result = await extract_llm_result(state.model, messages, adaption_llm, ReviewAdaptionResultNew, state.logger)  #ReviewAdaptionResultNew\
                async with _LLM_SEM:

                    result = await asyncio.to_thread(
                        extract_llm_result,
                        state.model,
                        messages,
                        adaption_llm,
                        ReviewAdaptionResultNew,
                        state.logger
                    )
                
            except Exception as e:
                logger.error(f"First extraction attempt failed: {e}")
                with open(state.output_dir / f"review_prompt_fallback_{continue_messages}_{state.timestamp}.jsonl", "w") as f:
                    for msg in messages:
                        f.write(msg.model_dump_json() + "\n")
                # Retry extraction
                # result = await extract_llm_result(state.model, messages, adaption_llm, ReviewAdaptionResultNew, state.logger)  # ReviewAdaptionResult
                async with _LLM_SEM:

                    result = await asyncio.to_thread(
                        extract_llm_result,
                        state.model,
                        messages,
                        adaption_llm,
                        ReviewAdaptionResultNew,
                        state.logger
                    )
            
        messages_this_agent.append(AIMessage(content=result.model_dump_json(indent=2)))
        
        logger.info(f"\n✓ REVIEW_ADAPTION_PROMPT_ITERATIVE Completed. Result:\n{result.model_dump_json(indent=2)}\n")
        logger.info("="*60)
        
        with open(state.output_dir / f"review_adaption_result_{continue_messages}_{state.timestamp}.json", "w") as f:
            f.write(result.model_dump_json(indent=2))
            
        # If adaption is needed, set action_plan for execution
        if result.needs_adaption:
            return {
                "review_adaption_result": result,
                "api_list": result.api_list,
                "iteration_count": state.iteration_count,
                "current_poster_json": current_poster_json,
            }
        else:
            return {"review_adaption_result": result, "messages": messages_this_agent, "api_list": []}
            
    except Exception as e:
        error_msg = f"Review adaption failed: {str(e)}"
        logger.error(f"\nERROR: {error_msg}")
        return {"error": error_msg}