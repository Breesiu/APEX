class API(object):
    def __init__(self, name, parameters, description,
                 parameter_description="", example="", api_desc="", composition_instructions=""):
        self.name = name
        self.parameters = parameters
        self.description = description
        self.parameter_description = parameter_description
        self.composition_instructions = composition_instructions
        self.example = example
        self.api_desc = api_desc

    def __str__(self):
        infos = [f"API: {self.name}{self.parameters}: {self.description}"]
        if self.parameter_description:
            infos.append(f"  - Parameters: {self.parameter_description}")
        if self.example:
            infos.append(f"  - Example:\n{self.example}")
        if self.composition_instructions:
            infos.append(f"  - Composition Instructions:\n{self.composition_instructions}")
        infos = [item for item in infos if item != ""]
        return '\n'.join(infos)


# ============================================================================
# 1. Text Formatting APIs - 文本格式控制
# ============================================================================

text_format_APIs = [
    # API(name="set_text_font_size",
    #     parameters="(element_id, font_size)",
    #     description="Sets the font size for text in an element.",
    #     parameter_description="'element_id' (str), 'size' (float, in points).",
    #     example="set_text_font_size(element_id = '10', size=24)\nset_text_font_size(element_id = '10', size=18)",
    #     api_desc="font size, text size"),

    # API(name="set_text_color",
    #     parameters="(element_id, color)",
    #     description="Sets the text color. Accepts names (e.g., 'red', 'dark_blue') or hex codes.",
    #     parameter_description="'element_id' (str), 'color' (str).",
    #     composition_instructions="Color names available: black, white, gray, red, blue, green, yellow, orange, purple, pink, brown, cyan, teal, navy, and their variants (light_*, dark_*).",
    #     example="set_text_color(element_id = '10', color='dark_blue')\nset_text_color(element_id = '10', color='#FF0000')",
    #     api_desc="text color, font color"),

    # API(name="set_text_bold",
    #     parameters="(element_id, bold=True)",
    #     description="Makes text bold or removes bolding.",
    #     parameter_description="'element_id' (str), 'bold' (bool)",
    #     example="set_text_bold(element_id = '10', bold=True)\nset_text_bold(element_id = '10', bold=False)",
    #     api_desc="bold text, font weight"),

    # API(name="set_text_italic",
    #     parameters="(element_id, italic=True)",
    #     description="Makes text italic or removes italics.",
    #     parameter_description="'element_id' (str), 'italic' (bool)",
    #     example="set_text_italic(element_id = '10', italic=True)",
    #     api_desc="italic text, font style"),

    # API(name="set_text_underline",
    #     parameters="(element_id, underline=True)",
    #     description="Adds or removes an underline from text.",
    #     parameter_description="'element_id' (str), 'underline' (bool).",
    #     example="set_text_underline(element_id = '10', underline=True)",
    #     api_desc="underline text, text decoration"),

    # API(name="highlight_keywords",
    #     parameters="(element_id, keywords, color='black', bold=True)",
    #     description="Highlights specific case-insensitive keywords by changing their color and/or making them bold.",
    #     parameter_description="'element_id' (str), 'keywords' (list of strings), 'color' (str), 'bold' (bool).",
    #     example="highlight_keywords(element_id = '10', keywords=['AI', 'deep learning'], color='red', bold=True)",
    #     api_desc="highlight, emphasize keywords"),

    # API(name="set_font_name",
    #     parameters="(element_id, font_name)",
    #     description="Sets the font family (e.g., 'Arial', 'Times New Roman').",
    #     parameter_description="'element_id' (str), 'font_name' (str).",
    #     example="set_font_name(element_id = '10', font_name='Arial')",
    #     api_desc="font family, typeface, font name"),

    API(name="text_format_brush",
        parameters="(element_id, font_size=None, color=None, bold=None, italic=None, underline=None, font_name=None, words=None)",
        description="A comprehensive text styling tool. It applies multiple formatting attributes (font size, color, bold, italic, underline, font family) to a specific text element simultaneously in a single API call. If 'text' is provided, it applies formatting ONLY to specific words within the element.",
        parameter_description=(
            "element_id: The unique ID of the target element.\n"
            "font_size: (Optional) Float, text size in points (e.g., 24.0).\n"
            "color: (Optional) String, Please use CSS standard color names like color name(black, white, gray, red, blue, green, yellow, orange, purple, pink, brown, cyan, teal, navy), and their variants (light*, dark*) or hex code (e.g., '#FF0000').\n"
            "bold, italic, underline: (Optional) Boolean. True to enable, False to disable.\n"
            "font_name: (Optional) String, the font family name (e.g., 'Arial', 'Times New Roman').\n"
            "words: (Optional) List[String], specific substring to format. If provided, formatting is applied only to these words."
        ),
        example="text_format_brush('10', font_size=36, color='darkblue', bold=True, font_name='Arial', text=['Target', 'Substring'])",
        composition_instructions=(
            "when you need to update one multiple attributes such as color, bold for the same element. Use 'words' parameter to highlight specific words."
        ),
        api_desc="Batch update text styles (size, color, bold, italic, underline, font) for an element or specific substring."
    )
]

# ============================================================================
# 2. 通用的位置和大小API
# ============================================================================

position_APIs = [
    API(name="set_element_size",
        parameters="(element_id, width=None, height=None)",
        description="Sets the size of an element.",
        parameter_description="'element_id' (str), 'width' (optional float), 'height' (optional float).",
        example="set_element_size('10', width=12, height=8)",
        api_desc="element size, resize, width, height"),

    API(name="set_element_position",
        parameters="(element_id, left, top)",
        description="Sets the absolute position of an element from the top-left corner.",
        parameter_description="'element_id' (str), 'left' (optional float), 'top' (optional float).",
        example="set_element_position('10', left=5, top=10)",
        api_desc="position, move, place, left, top"),

    # API(name="resize_element_proportionally",
    #     parameters="(element_id, scale, fixed_center=False)",
    #     description="This API resizes an element while maintaining its aspect ratio.",
    #     parameter_description="It takes parameters: 'element_id' (string), 'scale' (float, scaling factor), 'fixed_center' (Optional bool, True to scale from center, False for top-left).",
    #     example="resize_element_proportionally('10', scale=1.5, fixed_center=True)\nresize_element_proportionally('10', scale=0.8)",
    #     api_desc="scale image, proportional resize, maintain aspect ratio"),

    # API(name="move_element_relative",
    #     parameters="(element_id, delta_x=0, delta_y=0)",
    #     description="Moves an element relative to its current position.",
    #     parameter_description="'element_id' (str), 'delta_x' (optional float), 'delta_y' (optional float).",
    #     example="move_element_relative('10', delta_x=2, delta_y=-1)",
    #     api_desc="move, shift, relative position")

    API(name="move_group",
        parameters="(element_ids, dx=0, dy=0)",
        description="Moves one or multiple elements together by the specified offsets.",
        parameter_description="'element_ids' (list of str), 'dx'/'dy' (optional floats, relative movement in Inches).",
        example="move_group(['10','20'], dx=1.5, dy=-0.8)",
        composition_instructions="When moving, upward movement (dy is negative), downward movement (dy is positive); leftward movement (dx is negative), rightward movement (dx is positive).",
        api_desc="group move, move multiple"),
]

# ============================================================================
# 3. Shape Manipulation APIs - 形状操作
# ============================================================================

shape_APIs = [
    API(name="insert_line",
        parameters="(start_x, start_y, end_x, end_y, color='black', width=1.0, dash_style='solid', element_id=None)",
        description="Draw a straight line between two points.",
        parameter_description=(
            "start_x, start_y: Start coordinates (Inches).\n"
            "end_x, end_y: End coordinates (Inches).\n"
            "color: line color,(Optional) String, color name (e.g., 'red') or hex code (e.g., '#FF0000').Please use CSS standard color names without spaces, e.g., 'lightgray'.\n"
            "dash_style: 'solid', 'dash', 'dash_dot','long_dash'.\n"
            "element_id(str) is a number assigned by LLM for tracing,starting from 80"
        ),
        example="insert_line(1, 1, 5, 1, color='darkblue',1.0, dash_style='dash',element_id = '80') # A dashed red horizontal line"),

    API(name="insert_shape",
        parameters="(left, top, width, height, shape_type, fill_color=None, line_color=None, line_width=0.0, line_dash=None, element_id=None)",
        description="Insert a geometric shape (Rectangle, Rounded Rectangle, Arrow) with optional fill and border styles.",
        parameter_description=(
            "shape_type: ('rectangle', 'rounded_rectangle', 'arrow','diamond','oval','star')\n"
            "line_color: Border color. If None, no border is drawn.It can be color name (e.g., 'red') or hex code (e.g., '#FF0000').Please use CSS standard color names.\n"
            "line_dash: Border style ('solid', 'dash', 'dash_dot','long_dash')."
            "element_id(str) is a number assigned by LLM for tracing,starting from 85"
        ),
        example="insert_shape(2, 2, 4, 3, 'rounded_rectangle', fill_color='blue', line_color='black', line_dash='dash_dot',element_id = '85') # Blue rect with dotted border"),

    API(name="set_shape_style",
        parameters="(element_id, fill_color=None, shape_type=None, line_color=None, line_width=None, line_dash=None)",
        description="The 'Master Styler' for shapes. Modify fill, geometry, AND border settings in one go.",
        parameter_description=(
            "element_id: The ID of the target element.\n"
            "fill_color: (Optional) Hex string(e.g., '#FF0000') or color name(e.g., 'red') for the background fill. Please use CSS standard color names without spaces'.\n"
            "shape_type: (Optional) 'rounded_rectangle' only. change 'rectangle' to 'rounded_rectangle' \n"
            "line_color: (Optional) Border color. Please use CSS standard color names without spaces'.\n"
            "line_width: (Optional) Border thickness in points.\n"
            "line_dash: (Optional) Border style ('solid', 'dash', 'dash_dot','long_dash')."
        ),
        example="set_shape_style('10', fill_color='white', shape_type='rounded_rectangle', line_color='blue', line_dash='dash')",
        api_desc="Allow simultaneous or separate updates to fill, geometry_shape, and border styles.."),

    # API(name="set_line_style",
    #     parameters="(element_id, color=None, width=None, dash_style=None)",
    #     description="Modify the border of a shape OR the style of a line/connector. Allows changing color, thickness, and dash pattern independently.",
    #     parameter_description=(
    #         "element_id: The ID of the existing element.\n"
    #         "color: (Optional) Border/Line color.\n"
    #         "width: (Optional) Thickness in points.\n"
    #         "dash_style: (Optional) 'solid', 'dash', 'dash_dot','long_dash'."
    #     ),
    #     example="set_line_style('10', width=3.0, dash_style='dash') # Changes style without changing color",
    #     composition_instructions="Use this to post-process borders or lines. For example, to make a separator line dashed or to thicken a box border.",
    #     api_desc="Update line/border color, width, and dash style."
    #     )
    ]

# ============================================================================
# 4. Layout and Alignment APIs - 排版对齐
# ============================================================================

layout_APIs = [
    # API(
    #     name="align_elements_x_axis",
    #     parameters="(element_ids, alignment='left', reference_id)",
    #     description="Aligns elements by adjusting their X-axis position to be identical with reference_id's position(e.g., Making all elements share the same Left edge).",
    #     parameter_description=(
    #         "- element_ids (list[str]): The IDs of elements to move.\n"
    #         "- alignment (str): 'left' (align left edges), 'center' (align horizontal centers), or 'right' (align right edges).\n"
    #         "- reference_id (str, optional): The ID of the anchor element to align others to. "
    #         "If omitted, the first element in element_ids is used as the anchor."
    #     ),
    #     example="align_elements_x_axis(['10', '15'], alignment='center', reference_id='10')",
    #     composition_instructions="Use this to stack items vertically in a column (e.g. align all titles to the left), and align them to a specific object's left/right edge.",
    #     api_desc="Horizontal alignment: Left, Center, Right"
    # ),

    # API(
    #     name="align_elements_y_axis",
    #     parameters="(element_ids, alignment='top', reference_id)",
    #     description="Aligns elements by adjusting their Y-axis position to be identical with reference_id's position(e.g., Making all elements share the same Top edge).",
    #     parameter_description=(
    #         "- element_ids (list[str]): The IDs of elements to move.\n"
    #         "- alignment (str): 'top' (align top edges), 'middle' (align vertical centers), or 'bottom' (align bottom edges).\n"
    #         "- reference_id (str, optional): The ID of the anchor element to align others to. "
    #         "If omitted, the first element in element_ids is used as the anchor."
    #     ),
    #     example="align_elements_y_axis(['10', '15, '18'], alignment='top', reference_id='10')",
    #     composition_instructions="Use this to place items in a row, and align them to a specific object's top/bottom edge.",
    #     api_desc="Vertical alignment: Top, Middle, Bottom"
    # ),

    API(name="set_text_alignment",
        parameters="(element_id, alignment='left')",
        description="Sets the text alignment within a text box.",
        parameter_description="'element_id' (str), 'alignment' (str: 'left', 'center', 'right', 'justify').",
        example="set_text_alignment('10', alignment='center')",
        api_desc="text align, center text, justify"),
]

# ============================================================================
# 5. Content Editing APIs - 内容编辑
# ============================================================================

content_APIs = [
    API(name="set_text_content",
        parameters="(element_id, text, font_size=44, font_name='Arial', color='black', bold=False, italic=False, underline=False)",
        description="Set text content (complete replacement)",
        parameter_description="'element_id' (str), 'text' (str), 'font_size' (optional float), 'font_name' (optional str),'color'(optional str)(color_name or hex code),'bold'(optional bool),'italic'(optional bool),'underline(optional bool)'.",
        composition_instructions="When set text, you should simutaneously set text format by assigning parameters like font_size,font_name etc",
        example="set_text_content('10', text='New **important** abstract with $E=mc^2$.', font_size=44, font_name='Arial,color='red')",
        api_desc="replace text, set text, change text"),

    API(name="append_text",
        parameters="(element_id, text)",
        description="Appends text to an element.The format will automatically match the text preceding the addition.",
        parameter_description="'element_id' (str), 'text' (str).",
        example="append_text('10', text='\\nAdditional **findings** with $x^2$.')",
        api_desc="add text, append text"),

    # API(name="add_bullet_point",
    #     parameters="(element_id, level=0)",
    #     description="Adding bullet points to existing text to achieve greater clarity.",
    #     parameter_description="'element_id' (str), 'level' (• for level 0 and ◦  for level 1).",
    #     example="add_bullet_point('10', level=0)",
    #     api_desc="bullet point, add list item"),

    API(name="insert_textbox",
        parameters="(left, top, width, height, text='', font_size=44, font_name='Arial', color='black', bold=False, italic=False, underline=False, element_id=None)",
        description="Creates a new text box, and insert text into it. Supports LaTeX formulas.",
        parameter_description="'left'/'top'/'width'/'height' (floats, in Inches), 'text', 'font_size', 'font_name','element_id'(str) is a number assigned by LLM for tracing,starting from 60.",
        composition_instructions="You should set suitable position and assign font_size and font_name accroding to the given prompts.",
        example="insert_textbox(left=1, top=1, width=5, height=2, text='Initial **content** with $y=ax+b$.', font_size=44, font_name='Arial',bold = True element_id = '60')",
        api_desc="add textbox, create textbox,insert new text"),

    # API(name="delete_element",
    #     parameters="(element_id)",
    #     description="Removes an element from the slide.",
    #     parameter_description="'element_id' (str).",
    #     example="delete_element('10')",
    #     api_desc="delete element, remove shape"),
    API(name="batch_delete_elements",
        parameters="(element_ids)",
        description="Deletes one or multiple elements at once.",
        parameter_description="'element_ids' (list of str).",
        example="batch_delete_elements(['10', '11'])",
        api_desc="batch delete, remove multiple"),
]

# 6.图片

image_APIs = [
    API(name="insert_image",
        parameters="(image_path, left, top, width=None, height=None, element_id=None)",
        description="Inserts a new image into the slide.",
        parameter_description="'image_path' (str), 'left' (float), 'top' (float), 'width' (optional float), 'height' (optional float). All units in inch.element_id(str) is a number assigned by LLM for tracing,starting from 70",
        example="insert_image(image_path='paper-page-1.png', left=5, top=10, width=10,element_id = '70')",
        api_desc="add image, insert picture, add figure"),

# # TODO: delete? seems redundant
#     API(name="replace_image",
#         parameters="(element_id, new_image_path, new_image_element_id)",
#         description="Replaces an existing image with a image in original poster or from paper, if it is in original poster, you should set new_image_element_id with element_id, otherwise, set new_image_path with image path, keeping its position and size.",
#         parameter_description="'element_id' (str), 'new_image_path' (Optional str), 'new_image_element_id' (Optional str).",
#         example="replace_image('10', new_image_path='paper-page-1.png'), replace_image('10', new_image_element_id='51') ",
#         api_desc="replace image, update image, change image"),

]

# ============================================================================
# 7. Legend and Annotation APIs - 图例标注
# ============================================================================

# legend_APIs = [
#     API(name="add_callout",
#         parameters="(target_element_id, text, position='right', offset=1.5, element_id=None)",
#         description="Adds an annotated callout pointing to an element.",
#         parameter_description="'target_element_id' (str), 'text' (str), 'position' (str: 'left'/'right'/'top'/'bottom'), 'offset' (float, in Inches),element_id(optional str) is a number assigned by LLM for tracing,starting from 90",
#         example="add_callout('figure_1', text='Peak accuracy', position='top',offset = 1.0,element_id = '90')",
#         api_desc="callout, annotation, label"),

# ]

# ============================================================================
# 8. Batch Operation APIs - 批量操作
# ============================================================================

batch_APIs = [
    # API(name="batch_set_font_size",
    #     parameters="(element_ids, size)",
    #     description="Sets the same font size for multiple elements.",
    #     parameter_description="'element_ids' (list of str), 'size' (float, in points).",
    #     example="batch_set_font_size(['10', '11'], size=18)",
    #     api_desc="batch font size, bulk format"),

    # API(name="batch_set_color",
    #     parameters="(element_ids, color)",
    #     description="Sets the same text color for multiple elements.",
    #     parameter_description="'element_ids' (list of str), 'color' (str).",
    #     example="batch_set_color(['10', '11'], color='dark_blue')",
    #     api_desc="batch color, bulk color"),

    API(name="batch_delete_elements",
        parameters="(element_ids)",
        description="Deletes one or multiple elements at once.",
        parameter_description="'element_ids' (list of str).",
        example="batch_delete_elements(['10', '11'])",
        api_desc="batch delete, remove multiple"),

    # API(name="clone_element",
    #     parameters="(source_id, new_left, new_top)",
    #     description="Duplicates an element to a new position.",
    #     parameter_description="'source_id' (str), 'new_left'/'new_top' (floats, in Inches).",
    #     example="clone_element('10', new_left=15, new_top=10)",
    #     api_desc="clone, duplicate, copy element"),

    API(name="move_group",
        parameters="(element_ids, dx=0, dy=0)",
        description="Moves one or multiple elements together by the specified offsets.",
        parameter_description="'element_ids' (list of str), 'dx'/'dy' (optional floats, relative movement in Inches).",
        example="move_group(['10','20'], dx=1.5, dy=-0.8)",
        composition_instructions="When moving, upward movement (dy is negative), downward movement (dy is positive); leftward movement (dx is negative), rightward movement (dx is positive).",
        api_desc="group move, move multiple"),
]

# ============================================================================
# 9. Utility APIs - 工具函数
# ============================================================================

utility_APIs = [
    # API(name="get_element_info",
    #     parameters="(element_id)",
    #     description="Retrieves detailed properties of an element (type, position, size, text).",
    #     parameter_description="'element_id' (str). Returns a dictionary.",
    #     example="info = get_element_info('10')",
    #     api_desc="get info, inspect element, element properties"),

    # API(name="get_element_bounds",
    #     parameters="(element_id)",
    #     description="Returns the bounding box coordinates of an element.",
    #     parameter_description="'element_id' (str). Returns tuple (left, top, right, bottom) in Inches.",
    #     example="bounds = get_element_bounds('10')",
    #     api_desc="element bounds, bounding box, coordinates"),

    API(name="send_to_back_by_id",
        parameters="(element_id)",
        description="Moves the element to the back of the z-order (behind other elements).",
        parameter_description="'element_id' (str).",
        example="send_to_back_by_id('10')",
        composition_instructions="When you insert new shape and set fill color for emphasis,you should use this api to Place the layer at the bottom to prevent covering.",
        api_desc="send backward, send to back, z-order"),

]

# ============================================================================
# Aggregate all APIs by category
# ============================================================================

ALL_APIS = {
    "Text Formatting": text_format_APIs,
    "Position Settings": position_APIs,
    "Image Operations": image_APIs,
    "Shape Operations": shape_APIs,
    "Layout and Alignment": layout_APIs,
    "Content Editing": content_APIs,
    # "Legends and Annotations": legend_APIs,
    # "Batch Operations": batch_APIs,
    "Utilities": utility_APIs,
}



def generate_api_documentation(output_format="text"):
    """Generate complete API documentation"""
    if output_format == "text":
        doc = "=" * 5 + "\n"
        doc += "SCIENTIFIC POSTER EDITING API DOCUMENTATION\n"
        doc += "=" * 5 + "\n\n"

        for category, apis in ALL_APIS.items():
            doc += f"\n{'=' * 5}\n"
            doc += f"{category.upper()}\n"
            doc += f"{'=' * 5}\n\n"

            for api in apis:
                doc += str(api) + "\n\n"
                doc += "-" * 5 + "\n\n"

        return doc

    elif output_format == "markdown":
        doc = "# Scientific Poster Editing API Documentation\n\n"

        for category, apis in ALL_APIS.items():
            doc += f"## {category}\n\n"

            for api in apis:
                doc += f"### `{api.name}{api.parameters}`\n\n"
                doc += f"**Description:** {api.description}\n\n"

                if api.parameter_description:
                    doc += f"**Parameters:** {api.parameter_description}\n\n"

                if api.composition_instruction:
                    doc += f"**Usage Notes:** {api.composition_instruction}\n\n"
                
                if api.example:
                    doc += f"**Example:**\n```python\n{api.example}\n```\n\n"

                doc += "---\n\n"

        return doc
def get_categories():
    """Get all API categories"""
    return list(ALL_APIS.keys()).__str__()


# print(get_categories())
def generate_api_category_names_descs(output_format="text"):
    """Generate complete API documentation"""
    if output_format == "text":
        doc = ""
        for category, apis in ALL_APIS.items():
            doc += f"{category} includes:\n"            
            for api in apis:
                doc += str(api.name) + ": "+ api.description + "\n"
            doc += "\n"
    return doc
# print(generate_api_category_names_descs())

def filter_apis(keep_categories, output_format="text"):
    """Filter APIs by specified categories"""
    filtered_apis = {}
    for category in keep_categories:
        if category in ALL_APIS:
            filtered_apis[category] = ALL_APIS[category]
    if 'all' in keep_categories:
        filtered_apis = ALL_APIS
    if output_format == "text":
        doc = "=" * 5 + "\n"
        doc += "SCIENTIFIC POSTER EDITING filted API DOCUMENTATION\n"
        doc += "=" * 5 + "\n\n"
        
        for category, apis in filtered_apis.items():
            doc += f"\n{'=' * 10}\n"
            doc += f"{category.upper()}\n"
            
            for api in apis:
                doc += str(api) + "\n\n"
            doc += "=" * 10      
        return doc

# print(filter_apis(['Text Formatting','Position Settings'],output_format="text"))
