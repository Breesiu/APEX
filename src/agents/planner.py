from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from ..schema import AgentState, Plan_APIs
from ..prompts.planner_toolcall_prompts import (
    PLANNER_APICODE_WITH_TOOL_USER_PROMPT_WITHOUT_FILTER_WITHOUT_ID_POSTION,
)
from ..tools.image_tools import convert_pptx_to_png, encode_image_to_base64
from ..tools.utils import _invoke_with_retries, _ainvoke_with_retries

# Initialize Qwen model for planning
# Note: You can also use vllm or other Qwen deployment methods
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatZhipuAI
from ..config import QWEN3_8B_LOCAL_ENDPOINT, QWEN3_VL_8B_LOCAL_ENDPOINT, PLANNER_MODEL
import os
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI, Modality
import asyncio
_MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "100"))
_LLM_SEM = asyncio.Semaphore(_MAX_CONCURRENCY)
import base64

from dotenv import load_dotenv
#load_dotenv()
import re
import re
import json
from ..tools.pptx_parser import PosterFilter
from ..tools.api_doc import generate_api_documentation
from .paper_understanding import create_paper_understanding_tool
from pydantic import parse_obj_as
from dotenv import load_dotenv
load_dotenv()


async def planning_code_with_tools(state: AgentState) -> dict:
    """
    Planning Agent with Paper Understanding Tool.
    Can call paper_understanding_tool when paper content is required.
    """
    logger = state.logger
    if logger:
        logger.info("\n" + "="*60)
        logger.info("AGENT: Planning_Code Agent with Tools")
        # logger.info(f"Filtering: {'ENABLED' if state.is_filter_applied else 'DISABLED'}")
        logger.info("="*60)
    
    # Create LLM with tool binding
    if 'qwen' in state.model or 'Qwen' in state.model:
        planner_llm = ChatOpenAI(
            model=state.model or PLANNER_MODEL,
            temperature=0.1, # 0.1
            base_url=state.base_url or os.getenv("ALIBABA_BASE_URL", "EMPTY"),
            api_key=state.api_key or os.getenv("ALIBABA_API_KEY", "EMPTY"),
            max_tokens=4096,
        )
    elif state.model.startswith('gemini'):
        planner_llm = ChatGoogleGenerativeAI(
            model=state.model or PLANNER_MODEL,
            temperature=0.1,
            max_output_tokens=4096,
            api_key=os.getenv("GOOGLE_API_KEY", state.api_key or "EMPTY"),
            base_url=state.base_url or os.getenv("GOOGLE_BASE_URL", "EMPTY"),
            thinking_level="low",
            include_thoughts=False,
            # max_retries=3
        )
        
    
    # Create paper understanding tool with state access
    paper_tool = create_paper_understanding_tool(state)
    query_paper = None
    # Prepare image
    png_with_labeled_path = convert_pptx_to_png(
        state.current_pptx_path
    )    
    image_base64 = encode_image_to_base64(png_with_labeled_path)

    # Bind tool to LLM
    if 'qwen' in state.model or 'Qwen' in state.model:
        llm_with_tools = planner_llm.bind_tools([paper_tool, Plan_APIs],parallel_tool_calls=False, tool_choice='any')
    elif state.model.startswith('gemini'):
        llm_with_tools = planner_llm.bind_tools([paper_tool, Plan_APIs], tool_choice='any')


    # PLANNER_APICODE_WITH_TOOL_USER_PROMPT_WITHOUT_FILTER_concise
    #PLANNER_APICODE_WITH_TOOL_USER_PROMPT_WITHOUT_FILTER_OPTIMIZED
    user_msg = PLANNER_APICODE_WITH_TOOL_USER_PROMPT_WITHOUT_FILTER_WITHOUT_ID_POSTION.substitute(
        poster_json=state.poster_json.model_dump_json(indent=2, exclude_unset=True, exclude={'elements': {'__all__': {'runs': True}}}) if not state.preserve_runs else state.poster_json.model_dump_json(indent=2, exclude_unset=True),
        # has_paper="Yes" if state.pdf_path else "No",
        user_instruction=state.user_instruction,
        python_functions_api = generate_api_documentation()
    )                  
    example_image_base64 =  encode_image_to_base64("./benchmark_withpostergen_flat_final/ICLR-2024-4-Butterfly_Effects_of_SGD_Noise_Error_Amplification_in_Behavior_Cloning_and_Autoregression/ByPosterGen.png")
    text_image_description = ""

    
    messages = [
        # SystemMessage(content=PLANNER_WITH_TOOL_SYSTEM_PROMPT),
        HumanMessage(content=[
                {"type":"text","text":user_msg},
                {
                    "type": "text", "text": f"Image #1: Poster before editing{text_image_description}:"
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                },
                {
                    "type": "text", "text": f"Image #2: Example poster format{text_image_description}:"
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{example_image_base64}"}
                }
        ])
    ]

    # Save prompt for debugging
    with open(state.output_dir / "planner_code_with_tools_prompt.txt", "w", encoding="utf-8") as f:
        f.write(user_msg)

    # Track paper understanding results
    paper_understanding_result = None
    
    try:
        # First call - may include tool calls
        try:
            async with _LLM_SEM:

                response = await _ainvoke_with_retries(
                    llm_with_tools,
                    messages,
                    logger=logger,
                    max_retries=10,
                )
        except:
            async with _LLM_SEM:

                response = await _ainvoke_with_retries(
                    llm_with_tools,
                    messages,
                    logger=logger,
                    max_retries=10,
                )
            logger.info(f"Initial planner response received after retry.")
        logger.info(f"Initial planner response received. {response}")
        # Check if tool was called
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"Tool calls detected: {len(response.tool_calls)}")
            
            # Process tool calls
            tool_call = response.tool_calls[0]
            if 'qwen' in state.model or 'Qwen' in state.model or state.model.startswith('gemini'):
                if tool_call['name'] == 'paper_understanding_tool':
                    if 'query' in tool_call['args']:
                        query_paper = tool_call['args']['query']
                    logger.info(f"Calling paper_understanding_tool with: {tool_call['args']}")
                    with open(state.output_dir / "tool_call_args.json", "w", encoding="utf-8") as f:
                        f.write(json.dumps(tool_call['args'], ensure_ascii=False, indent=2))
                    # Execute tool
                    tool_result = await paper_tool.ainvoke(tool_call['args'])
                    paper_understanding_result = tool_result
                    if paper_understanding_result:
                        try:
                            # TODO
                            # paper_data = json.loads(paper_understanding_result)
                            # result["paper_content_extracted"] = PaperUnderstandingToolOutput(
                            #     extracted_sections=paper_data.get("relevant_text", ""),
                            #     relevant_images=paper_data.get("relevant_images", []),
                            #     relevant_tables=paper_data.get("relevant_tables", []),
                            #     notes=paper_data.get("summary", "")
                            # )
                            if 'paper_baseline' not in paper_understanding_result:
                                
                                with open(state.output_dir / "paper_content_extracted.json", "w", encoding="utf-8") as f:
                                    # f.write(json.dumps(paper_understanding_result, ensure_ascii=False, indent=2))
                                    f.write(paper_understanding_result["paper_content_extracted"].model_dump_json(indent=2))
                                with open(state.output_dir / "extracted_visuals_details.json", "w", encoding="utf-8") as f:
                                    f.write(json.dumps(paper_understanding_result['extracted_visuals_details'], ensure_ascii=False, indent=2))
                            else:
                                with open(state.output_dir / "paper_baseline_query.txt", "w", encoding="utf-8") as f:
                                    f.write(query_paper)
                        except:
                            pass
                    # create_image(state)
                    # Add tool result to messages
                    if 'paper_baseline' not in tool_result:
                        messages.append(response)
                        messages.append(ToolMessage(
                            content=tool_result,
                            tool_call_id=tool_call['id']
                        ))
                    else:
                        # query_paper = tool_call['args']['query']
                        messages.append(response)
                        # messages.append(ToolMessage(
                        #     content=tool_result['paper_baseline'],
                        #     tool_call_id=tool_call['id']
                        # ))
                        messages.append(HumanMessage(
                            content=tool_result['paper_baseline']
                        ))
                    # logger.info("Tool result for LLM:\n", tool_content_for_llm)
                    # logger.info("Messages after tool call:\n", messages)    
                    logger.info("Paper understanding tool completed")
                    
                    
                    llm_with_tools = planner_llm.bind_tools([Plan_APIs], tool_choice='Plan_APIs')
                    try:
                        async with _LLM_SEM:

                            response = await _ainvoke_with_retries(
                                llm_with_tools,
                                messages,
                                logger=logger,
                                max_retries=10,
                            )
                    except:
                        with open(state.output_dir / "planner_code_with_tools_prompt_for_GeminiChat_error.txt", "w", encoding="utf-8") as f:
                            for msg in messages:
                                f.write(msg.model_dump_json() + "\n")
                        async with _LLM_SEM:
                            response = await _ainvoke_with_retries(
                                llm_with_tools,
                                messages,
                                logger=logger,
                                max_retries=10,
                            )
                    logger.info(f"Second planner response received after paper understanding tool.{response}")
                if not (state.output_dir/ "poster_v1_image.png").exists():
                    # os.remove(state.output_dir/ "poster_v1_image.png")
                    # create_image(state)
                    pass
                    
                    
                tool_call = response.tool_calls[0]
                if tool_call['name'] == 'Plan_APIs':
                    logger.info("Plan tool called - this should be handled in final response parsing.")
                    response = Plan_APIs(**tool_call['args'])
                    tool_message = ToolMessage(
                        content="Here is your structured response: "+str(tool_call['args']),
                        tool_call_id=tool_call['id']
                    )
                    messages.append(tool_message)
                    # with open(state.output_dir / "planner_code_with_tools_prompt_for_GeminiChat.txt", "w", encoding="utf-8") as f:
                    #     # f.write(str(messages))
                    #     for msg in messages:
                    #         f.write(msg.model_dump_json() + "\n")
                # # Get final response after tool execution
                # response = llm_with_tools.invoke(messages)
        else:
            response = response
            messages.append(response)
        
        plan = response

        
        logger.info(f"Plan_code created: {plan.model_dump_json(indent=2)}")
        logger.info("Planning_Code Agent with Tools - Completed")
        
        # Build result
        # query = '1'
        result = {
            "plan_apis": plan,
            # "action_plan": ActionPlan(operations=plan.operations),
            "api_list": plan.api_list,
            "query_paper": query_paper,
            "messages": messages
            }
        with open(state.output_dir / "plan_apis.json", "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))
        # If paper was processed, store the results
        if paper_understanding_result:
            try:
                # TODO
                if 'paper_baseline' not in paper_understanding_result:
                    result["paper_content_extracted"] = paper_understanding_result["paper_content_extracted"]
                    result["extracted_visuals_details"] = paper_understanding_result['extracted_visuals_details']
                else:
                    result['paper_baseline'] = paper_understanding_result['paper_baseline']
            except:
                pass
        

        return result
        
    except Exception as e:
        logger.error(f"Planning with tools failed: {e}")
        return {"error": str(e)}