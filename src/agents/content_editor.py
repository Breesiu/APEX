
from ..tools.api_doc import generate_api_documentation
'''
def get_api_details() -> str: # TODO:
    """Returns a string including description of  the available python functions for content editing. it should include type of function, function name, parameters, and brief description...."""
    api_details = """
Available Python Functions for Content Editing:
1. insert_textbox(element_id: str, text: str, position: dict) -> None
   - Inserts a new textbox with specified text at the given position.
2. insert_section(section_name: str, text: str, position: dict) -> None
   - Inserts a new section with the given name and text at the specified position...."""
    pass
'''
from dotenv import load_dotenv
load_dotenv()
import json
def get_api_details() -> str:
    return generate_api_documentation()

