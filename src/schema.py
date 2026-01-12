from typing import List, Dict, Optional, Any, Literal, Union
from pydantic import BaseModel, Field
from enum import Enum
import logging
from pathlib import PosixPath
from langgraph.graph import MessagesState
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import add_messages
from langchain_core.messages import AnyMessage
from typing import Annotated


# --- Poster Element Structures ---

class TextRun(BaseModel): # TODO: what about paragraph?
    """Individual text run with formatting"""
    text: Optional[str] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    underline: Optional[bool] = None
    font_name: Optional[str] = None
    font_size: Optional[float] = None  # in points
    font_color: Optional[str] = None   # hex format
    bullet_level: Optional[int] = None  # for bullet points # TODO: it's paragraph property

class PosterElement(BaseModel):
    """Single element in the poster"""
    id: str = Field(description="Unique identifier")
    type: Literal["textbox", "picture", "shape", "table", "chart", "rectangle", "line"]
    left: Optional[float] = Field(None, description="X position in points")
    top: Optional[float] = Field(None, description="Y position in points")
    width: Optional[float] = None
    height: Optional[float] = None
    z_index: Optional[int] = 0
    
    # Text-specific
    text: Optional[str] = None
    runs: Optional[List[TextRun]] = Field(default_factory=list)
    
    main_font_size: Optional[float] = None  # in points
    # Shape-specific # TODO:
    fill_color: Optional[str] = None
    border_color: Optional[str] = None
    border_width: Optional[float] = None
    border_shape: Optional[str] = None  # line, dot-line...
    
    # Image-specific
    image_path: Optional[str] = None # need?
    
    # # Table-specific # TODO: not considered for now
    
    # Additional metadata
    section: Optional[str] = None  # e.g., "Introduction", "Methods" # TODO: how to infer? rule-based? or leave to agent?
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)

class PosterJSON(BaseModel):
    """Complete poster representation"""
    slide_width: float
    slide_height: float
    elements: Optional[List[PosterElement]]
    color_scheme: Optional[List[str]] = None # TODO

# --- Paper Content Structures ---

class PaperSection(BaseModel):
    """Extracted section from research paper"""
    title: str
    content: str
    figures: List[str] = Field(default_factory=list)  # Figure paths
    tables: List[Dict] = Field(default_factory=list)

class PaperContent(BaseModel):
    """Structured paper content"""
    title: str
    abstract: str
    sections: Dict[str, PaperSection] = Field(default_factory=dict)
    all_figures: List[str] = Field(default_factory=list)
    key_findings: Optional[str] = None

class PaperContentExtractionResult(BaseModel):
    """Result of paper content extraction"""#TODO: need to add visual image to avoid overlap between paper image and origional poster image.
    text: Optional[str] = None
    images_info: Dict[str, str]# id->caption #TODO: rename: figures_info
    tables_info: Dict[str, str]# id->caption

class PaperUnderstandingToolInput(BaseModel):
    pdf_path: PosixPath = Field(..., description="Absolute path to the research paper PDF")
    user_instruction: str = Field(..., description="User's editing instruction")
    poster_json: dict = Field(..., description="Current poster JSON (single-slide) for context")
    execution_plan: Optional[str] = Field(None, description="execution plan")
    target_sections_hint: Optional[List[str]] = Field(
        default=None,
        description="Optional hints for sections to extract (e.g., ['Abstract','Methods'])"
    )
    max_chars_per_section: int = Field(default=500, description="Cap extracted text size per section")
    query: Optional[str] = Field(
        default=None,
        description="Optional specific query to guide content extraction"
    )
    
    
class PaperUnderstandingToolOutput(BaseModel):
    # thought_process: str = Field(description="Step-by-step reasoning for content extraction")
    # Structured content ready to integrate
    extracted_text_contents: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of normalized section(target) name -> curated text for poster"
    ) # TODO: integrate with selected_figures, however, it may complicate the json structure 
    extracted_figures_tables: Dict[str, str] = Field(
        default_factory=list,
        description="Mapping of section name -> figure/table path to include"
    ) # TODO: need to input visual content. And add rationale for each figure. 
    # captions: Dict[str, str] = Field(
    #     default_factory=dict,
    #     description="Figure/table captions keyed by figure path/ref"
    # )
    # integration_suggestions: List[str] = Field(
    #     default_factory=list,
    #     description="Suggestions on how to integrate extracted content into the poster"
    # ) # TODO: need it?

# --- Edit Operation Structures ---


# --- Planning Structures ---

class Plan_APIs(BaseModel):
    plan: str = Field(description="think step by step, and output Detailed execution plan") # TODO:step by step(represented as list, include operation_type and element_id(or name))
    # filter_criteria: Optional[FilterCriteria] = Field(description="Criteria for filtering poster JSON) #and APIs")
    # operations: List[EditOperation] = Field(description="List of edit function-callings to perform based on plan.") #Field(default_factory=list)
    api_list: List[str] = Field(description="List of API function-callings to perform based on plan, each str are function(param1=xx, param2=yy, ...)") #Field(default_factory=list)

    
class ReviewAdaptionResultNew(BaseModel):
    """Result from layout adaption agent"""
    # thought_process: str = Field(description="Step-by-step reasoning for review and layout adaption")
    review_and_plan: str = Field(description="Detailed feedback on edit quality, and make a adjustment plan to make edited poster be consistent with user's instruction further.")
    # severity_issues: List[LayoutIssue] = Field(default_factory=list)
    needs_adaption: bool = Field(description="set it true when the edit result is not consistent with user instruction, otherwise false.") 
    # adaption_operations: Optional[ActionPlan] = Field(default=None, description="Operations to adapt the edited poster to be consistent with user instruction and execution plan") # TODO: only need to input layout-related api documents
    api_list: Optional[List[str]] = Field(default=None, description="additional API function-callings to adjust the edited poster to be consistent with user instruction") # TODO: only need to input layout-related api documents
# --- LangGraph State ---

class AgentState(BaseModel):
    """Central state for LangGraph workflow"""
    messages: Annotated[list[AnyMessage], add_messages]= Field(default_factory=list)

    # messages: list[AIMessage | HumanMessage | SystemMessage | ToolMessage] = Field(default_factory=list)

    logger: Optional[logging.Logger] = None

    # Input
    pptx_path : PosixPath
    output_dir: PosixPath
    user_instruction: str
    pdf_path: Optional[PosixPath] = None
    
    mode:str
    experiment_name: Optional[str] = None
    # optional
    incontext: bool = True
    preserve_runs: bool = False
    
    model: Optional[str] = 'gemini-3-flash-preview'  # e.g., 'gpt-4', 'qwen-vl-6b', etc.
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    
    # Parsed data
    poster_json: Optional[PosterJSON] = None
    current_poster_json: Optional[PosterJSON] = None
    
    paper_content: Optional[PaperContent] = None
    paper_content_extracted: Optional[PaperUnderstandingToolOutput] = None
    extracted_visuals_details: Optional[Dict[str, Any]] = None
    
    use_paper_pdf_directly: bool = True
    no_vlm_in_paper_understanding_tool: bool = False
    
    paper_raw_pdfbase64: Optional[str] = None # for baseline
    images_tables_info: Optional[str] = None # for baseline
    
    
    # Planning
    plan_apis: Optional[Plan_APIs] = None
    query_paper: Optional[str] = None
    
    
    current_pptx_path: Optional[PosixPath] = None
    # operations_applied: List[EditOperation] = Field(default_factory=list)
    api_list: Optional[List[str]] = None
    

    review_adaption_result: Union[ReviewAdaptionResultNew, None] = None
    iteration_count: int = 0
    max_iterations: int = 0
    iterate_version: str = ""
    iterate_debug: bool = False
    timestamp: str = ""
    
    # State tracking
    error: Optional[str] = None
    # intermediate_states: List[Dict] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True