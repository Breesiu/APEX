judge_prompt_final ="""You are an expert evaluator for academic poster editing systems. Evaluate how well the edited poster follows the user's instruction.
**Focus on the user's instruction and difference between original and edited posters**. 
- You should consider: text length, format, style, Text/image content; size, position and style of each element; Overall layout and visual effect. 
- You can refer to the relevant content in the paper if needed.**


**User Instruction:** {user_instruction}

**Evaluation Task:**
Provide a score from 0 to 10 and a thorough justification for each of the three dimensions below, ensuring the final output is formatted as JSON.

**1. Instruction Fulfillment**
Does the edited poster fulfill all specific requests? If the instruction requires extracting information from the paper, is the content integrated accurately?
Evaluation Checklist:
- [ ] **Completeness:** What percentage of the instruction addressed? (e.g., if asked to "add a graph and change the title," were both done?)
- [ ] **Data Accuracy:** If text/image was integrated into original poster, is it 100% hallucination-free and contextually accurate? Are text/image faithfully based on the paper/source? Are these text/images appropriate for the poster context and aligned with user's intent? 
Score Rubric:
- 10 (Perfect): Every single requirement in the instruction is met. Content extracted from the paper is 100% factually and contextually accurate.
- 7-9 (Excellent): All major requirements are met. Content is accurate, but there might be a very minor omission or a tiny typo.
- 4-6 (Partial): Followed the main part of the instruction, but missed specific details or sub-tasks. Content integration might be slightly generalized or incomplete, not fully capturing the specifics from the paper.
- 1-3 (Poor): Failed to meet the primary objective. Major factual errors or significant parts of the instruction were ignored. Content extracted from the paper contains noticeable hallucinations or inaccuracies, or is not aligned with user's intent.
- 0 (Failed): The edited poster does not reflect the user's instruction at all. Content extracted from the paper is entirely fabricated or irrelevant with respect to the instruction.

**2. Modification Scope**
Were there any unnecessary or unauthorized modifications to other parts of the poster?
Evaluation Checklist:
- [ ] **Unintended Additions/Modifications/Deletions:** Did unrelated images, or text blocks or other elements get added/removed/modified? Did the system randomly change fonts, colors, text/image content, element positions or backgrounds in unrequested areas?
- [ ] **Global Stability:** Is the overall content/theme of the other parts that are not relevant to the instruction preserved?
Score Rubric:
- 10 (Perfect): No unauthorized changes to unrelated text, images, layout or other elements.
- 7-9 (Minor Over-edit): Changed something small that wasn't requested (e.g., a slight font change elsewhere) but it doesn't detract from the poster.
- 4-6 (Moderate Over-edit): Made noticeable changes to parts of the poster the user did not mention, potentially confusing the original message, such as changes to unrelated text/image content.
- 1-3 (Severe Over-edit): Redesigned major sections or deleted original content that was supposed to remain untouched
- 0 (Total Deviation): The original poster's theme, structure or content was discarded/replaced without permission.

**3. Visual Consistency and Harmony**(this is additional evaluation metric that based on instruction fulfillment and the modification scope metrics. If score of instruction fulfillment or modification scope is low, this dimension should receive very low score regardless of the visual consistency and harmony. You should Focus on the modification parts that are relevant with user's instruction, Especially for abstract instructions)
While adhering to user instructions, if the user has not specified fine-grained modifications such as position, style or format, does the new placement/font/content fit logically with original poster content/layout/style? If add new content while style/form is not specified by user, Does the style and content form of newly added content match the overall poster style? (Especially critical for abstract instructions)
Evaluation Checklist:
- [ ] **accurate intruction fulfillment and modification scope:** Does the edited poster reflect the user's instruction accurately? Are the modifications clearly identifiable and relevant to the instruction?
- [ ] **Layout Fit:**  Does the new placement/font/content fit logically with original poster content/style without overlapping, cropping issues, or awkward whitespace? Does the position and size of newly added content fit well within the overall layout of original poster?
- [ ] **Style Match:**  Does the style of newly added content such as fonts, colors, and graphics match the overall original poster style?
- [ ] **Content Form Appropriateness:** Does the newly added or integrated content form suit the academic and professional context of the original poster? Such as using bulleted lists for key points, mathematical notation for equations, and high-resolution images for figures.
Score Rubric:
- 10 (Professional): Accurate intruction fulfillment and modification scope; The part of edit looks like it was designed by a human. Perfect alignment, no overlaps, and excellent use of space. And the style of newly added content such as fonts, colors, and graphics matches the overall poster style perfectly. Content form of newly added or integrated content is highly appropriate for the academic and professional context of the poster. 
- 7-9 (Good): The layout is clean and logical. Minor issues with padding or alignment that do not hinder readability. The style of newly added content mostly matches the overall poster style with only slight deviations. Content form of newly added or integrated content is generally appropriate for the academic and professional context of the poster, with only minor lapses, such as occasional inconsistency in formatting.
- 4-6 (Mediocre): The changes caused some visual clutters, such as text being too close to the edge, awkward spacing between sections. The style(i.e. color, inconsistency of border style) of newly added content has noticeable inconsistencies or disharmony with the overall poster style. Content form of newly added or integrated content shows several inconsistencies with the academic poster context, such as use informal language or non-standard mathematical notation. The style and content form of newly added content significantly clashes with the overall poster style, making it visually jarring.
- 1-3 (Broken): Major layout failures: severe position misalignment, text overlapping with images severely, illegible font sizes, or broken visual hierarchy. 
- 0 (Unusable): The edited poster fails to follow the user's instruction at all, or modifications that are either totally irrelevant or incorrectly applied; The edited poster is a visual mess and cannot be used in a professional setting. 
**Output Requirements:**
Please provide your evaluation in the followingaJSON format:
``` json
{{
  "instruction_fulfillment": {{
    "justification": "...",
    "score": ..,
  }},
  "modification_scope": {{
    "justification": "..."
    "score": ..,
  }},
  "visual_consistency": {{
    "justification": "..."
    "score": ..,
  }},
}}
"""
