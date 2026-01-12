from typing import Literal
from langgraph.graph import StateGraph, END
from .schema import AgentState
from .agents.planner import planning_code_with_tools
from .agents.code_generator import code_generation_execution_agent_api
from .agents.reviewer import review_adaption_agent
from .tools.pptx_parser import parse_pptx_to_json
from .tools.logger import setup_logger
from .tools.image_tools import convert_pptx_to_png

import os
from pathlib import Path
# --- Graph Construction ---
def create_poster_edit_graph_v3():
    """
    Create the complete LangGraph workflow for poster editing.
    
    Workflow:
    1. Parse PPTX -> Planning
    2. Planning -> Paper Understanding (conditional)
    3. Paper Understanding -> Content Editing (conditional)
    4. Content Editing -> Code Execution
    5. Code Execution -> Review (conditional)
    6. Review -> Layout Optimization (if needed) OR END
    7. Layout Optimization -> Code Execution (iteration)
    """
    
    workflow = StateGraph(AgentState)
    #state = AgentState()
    # --- Define Nodes ---
    
    def parse_pptx_node(state: AgentState) -> dict:
        # if state.output_dir.exists():
        #     print(f"Output directory {state.output_dir} already exists. Please remove or specify a new directory.")
        #     return {"error": "Output directory {state.output_dir} already exists. Please remove or specify a new directory."}
        if state.logger is None:
            # output_dir = Path(state["output_dir"])
            logger = setup_logger(state)
            state.logger = logger
            
        """Initial node: Parse PPTX to JSON"""
        logger.info("\n" + "="*60)
        logger.info("STEP: Parsing PPTX")
        logger.info("="*60)
        
        try:
            poster_json = parse_pptx_to_json(state.pptx_path)
            convert_pptx_to_png(state.pptx_path, rewrite=True)
            logger.info(f"\nParsed {len(poster_json.elements)} elements")
            logger.info(f"Slide dimensions: {poster_json.slide_width} x {poster_json.slide_height} inch")
            
            # Create output directory
            os.makedirs(state.output_dir, exist_ok=True)
            
            return {
                "logger": logger,
                "poster_json": poster_json,
                "current_poster_json": poster_json,
                "current_pptx_path": state.pptx_path if not state.iterate_debug else state.output_dir/f"poster_v1.pptx" # Initialize current path
            }
        except Exception as e:
            return {"error": f"Failed to parse PPTX: {e}"}
    
    workflow.add_node("parse_pptx", parse_pptx_node)
    workflow.add_node("planning_code_paper",planning_code_with_tools)

    workflow.add_node("code_execution_api", code_generation_execution_agent_api)
    workflow.add_node("review_adaption", review_adaption_agent)
    # --- Define Conditional Edges ---
    

    # --- Set Entry Point ---
    workflow.set_entry_point("parse_pptx")
    
    # --- Add Edges ---
    
    # Linear flow from parse to planning
    # workflow.add_edge("parse_pptx", "planning")
    # TODO:lambda?
    def should_iterate_debug(state: AgentState) -> Literal["planning_code_paper", "planning", "review_adaption"]:
        return "planning_code_paper"
            
    
    workflow.add_conditional_edges(
        "parse_pptx",
        # if state.experiment_name=='comparison_api", go to planning_code_paper; if 'comparison', go to planning_paper; else go to planning
        should_iterate_debug,
        {
            "planning_code_paper": "planning_code_paper",
            # "planning_paper": "planning_paper",
            "review_adaption": "review_adaption",
            # "planning": "planning",
            # "planning_paper_python_pptx": "planning_paper_python_pptx"
        }
    )
    workflow.add_edge("planning_code_paper", "code_execution_api")

    
    def should_review_adaption(state: AgentState) -> Literal["review_adaption", "end"]:        
        if (state.iterate_version and state.iterate_debug): #or state.no_vlm_in_paper_understanding_tool: #or not state.multi_modal_input:
            return "end"
        """After code execution: decide if layout review is needed"""
        if state.error or state.iteration_count > state.max_iterations:  # NOTE: after execution, the iteration count will increase by 1
            return "end"
        
        if state.plan_apis: # and state.plan.workflow.needs_layout_review:
            return "review_adaption"
        else:
            return "end"
        
    workflow.add_conditional_edges(
        "code_execution_api",
        should_review_adaption,
        {
            "review_adaption": "review_adaption",
            "end": END
        }
    )
    def should_adapt(state: AgentState) -> Literal["content_editing", "llmcode_generator", "end"]:
        """After Review adaption: decide if we need to execute adaption operations"""
        if state.error:
            return "end"
        
        # Check if adaption is needed
        if (state.review_adaption_result and 
            state.review_adaption_result.needs_adaption and 
            state.review_adaption_result.api_list):
            
            state.logger.info(f"Adaption iteration {state.iteration_count}/{state.max_iterations}")
            if state.mode == "api":
                return "code_execution_api"
            else:
                return "llmcode_generator"                
        else:
            return "end"
    workflow.add_conditional_edges(
        "review_adaption",
        should_adapt, 
        {
            "code_execution_api": "code_execution_api",
            "end": END
        }
    )
        
            
    workflow.add_edge("code_execution_api", END)


        

    #workflow.add_edge("layout_optimization", "code_execution")
    # --- Compile Graph ---
    app = workflow.compile()
    
    return app
