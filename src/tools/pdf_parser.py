import os
from typing import Optional, Tuple, Dict, Any
from ..schema import PaperContent, PaperSection
import json
import logging
import time
from pathlib import Path

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem, CodeItem
import PIL

import re

def _safe_save_png(img: "PIL.Image.Image", out_path: Path) -> None:
    """Fast-ish PNG save. Lower compress_level speeds up saving a lot."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # compress_level: 0 (fast, larger) .. 9 (slow, smaller). 1 is a good speed/size tradeoff.
    img.save(out_path, format="PNG") #, compress_level=1)

def gen_image_and_table(
    pdf_path: str,
    conv_res,
    *,
    save_code_blocks: bool = False,
    skip_if_exists: bool = True,
) -> Tuple[int, int, Dict[str, Any], Dict[str, Any]]:
    input_token, output_token = 0, 0

    pdf_path = Path(pdf_path)
    pdf_name = pdf_path.stem
    output_dir = pdf_path.parent / "images_and_tables"
    output_dir.mkdir(parents=True, exist_ok=True)

    doc_filename = pdf_name

    tables: Dict[str, Any] = {}
    images: Dict[str, Any] = {}

    table_counter = 0
    picture_counter = 0
    code_counter = 0

    # Single-pass: save image + compute metadata in-memory (avoid re-open and second loops)
    for element, _level in conv_res.document.iterate_items():
        if isinstance(element, TableItem):
            table_counter += 1
            out_name = f"{doc_filename}-table-{table_counter}.png"
            out_path = output_dir / out_name

            if (not skip_if_exists) or (not out_path.exists()):
                img = element.get_image(conv_res.document)
                _safe_save_png(img, out_path)
            else:
                # If skipping save, still need metadata. Re-open only in this rare branch.
                img = PIL.Image.open(out_path)

            caption = element.caption_text(conv_res.document)
            w, h = img.width, img.height
            tables[f"table_{table_counter}"] = {
                "caption": caption,
                "table_path": out_path.name,
                "width": w,
                "height": h,
                "figure_size": w * h,
                "figure_aspect": round(w / h, 4) if h else None,
            }

        elif isinstance(element, PictureItem):
            picture_counter += 1
            out_name = f"{doc_filename}-picture-{picture_counter}.png"
            out_path = output_dir / out_name

            if (not skip_if_exists) or (not out_path.exists()):
                img = element.get_image(conv_res.document)
                _safe_save_png(img, out_path)
            else:
                img = PIL.Image.open(out_path)

            caption = element.caption_text(conv_res.document)
            w, h = img.width, img.height
            images[f"image_{picture_counter}"] = {
                "caption": caption,
                "image_path": out_path.name,
                "width": w,
                "height": h,
                "figure_size": w * h,
                "figure_aspect": round(w / h, 4) if h else None,
            }

        elif save_code_blocks and isinstance(element, CodeItem):
            code_counter += 1
            out_name = f"{doc_filename}-code-{code_counter}.png"
            out_path = output_dir / out_name
            if (not skip_if_exists) or (not out_path.exists()):
                try:
                    img = element.get_image(conv_res.document)
                    _safe_save_png(img, out_path)
                except Exception:
                    # CodeItem image extraction may fail; ignore for speed/stability
                    pass

    with open(output_dir / f"{doc_filename}_images.json", "w", encoding="utf-8") as fp:
        json.dump(images, fp, indent=4, ensure_ascii=False)

    with open(output_dir / f"{doc_filename}_tables.json", "w", encoding="utf-8") as fp:
        json.dump(tables, fp, indent=4, ensure_ascii=False)

    return input_token, output_token, images, tables

def extract_paper_content(
    pdf_path: str,
    ocr_lang: Optional[list] = None,
    *,
    images_scale: float = 3.0,
    num_threads: Optional[int] = None,
    save_code_blocks: bool = False,
) -> Tuple[None, Dict[str, Any], Dict[str, Any]]:
    """
    Extract images/tables metadata from a research paper PDF.

    Performance knobs:
      - images_scale: lower = faster, less detailed images (default 3.0; was 5.0)
      - num_threads: default uses min(8, cpu_count) to reduce overhead
      - save_code_blocks: off by default (saves time)

    Returns:
        (None, images_info, tables_info)
    """
    pdf_path = Path(pdf_path)
    pdf_name = pdf_path.stem
    output_dir = pdf_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    images_json_path = output_dir / "images_and_tables" / f"{pdf_name}_images.json"
    tables_json_path = output_dir / "images_and_tables" / f"{pdf_name}_tables.json"

    # Cache hit
    if images_json_path.exists() and tables_json_path.exists():
        with open(images_json_path, "r", encoding="utf-8") as fp:
            images_info = json.load(fp)
        with open(tables_json_path, "r", encoding="utf-8") as fp:
            tables_info = json.load(fp)
        return None, images_info, tables_info

    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = float(images_scale)
    pipeline_options.generate_picture_images = True
    pipeline_options.generate_page_images = True

    if num_threads is None:
        # Too many threads can increase overhead on some machines.
        cpu = os.cpu_count() or 8
        num_threads = min(8, cpu)

    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=int(num_threads),
        device=AcceleratorDevice.AUTO,
    )

    doc_converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    raw_result = doc_converter.convert(pdf_path)

    _, _, images_info, tables_info = gen_image_and_table(
        pdf_path,
        raw_result,
        save_code_blocks=save_code_blocks,
        skip_if_exists=True,
    )

    return None, images_info, tables_info

if __name__ == "__main__":
    pdf_path = "/root/Poster-Edit/benchmark-v1-202511062200/Inner Classifier-Free Guidance and Its Taylor Expansion for Diffusion Models/paper.pdf"
    extract_paper_content(pdf_path)


# import os
# from typing import Optional
# from ..schema import PaperContent, PaperSection
# import json
# import logging
# import time
# from pathlib import Path

# from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
# from docling.datamodel.base_models import InputFormat
# from docling.datamodel.pipeline_options import (
#     PdfPipelineOptions,
# )
# from docling.document_converter import DocumentConverter, PdfFormatOption
# from docling_core.types.doc import ImageRefMode, PictureItem, TableItem, CodeItem
# import PIL


# import re
# # try:
# #     import fitz  # PyMuPDF
# #     PYMUPDF_AVAILABLE = True
# # except ImportError:
# #     PYMUPDF_AVAILABLE = False
# #     logging.warning("PyMuPDF not installed. PDF parsing will be limited.")
# def gen_image_and_table(pdf_path, conv_res):
#     input_token, output_token = 0, 0

#     # === 安全文件名 & 输出路径 ===
#     pdf_path = Path(pdf_path)
#     pdf_name = pdf_path.stem  # "paper"
#     output_dir = pdf_path.parent / "images_and_tables"
#     output_dir.mkdir(parents=True, exist_ok=True)

#     # 仅文件名部分，用于命名
#     doc_filename = pdf_name

#     # === 保存表格 / 图片 / 代码块 ===
#     table_counter = picture_counter = code_counter = 0

#     for element, _level in conv_res.document.iterate_items():
#         if isinstance(element, TableItem):
#             table_counter += 1
#             element_image_filename = output_dir / f"{doc_filename}-table-{table_counter}.png"
#             with element_image_filename.open("wb") as fp:
#                 element.get_image(conv_res.document).save(fp, "PNG")

#         elif isinstance(element, PictureItem):
#             picture_counter += 1
#             element_image_filename = output_dir / f"{doc_filename}-picture-{picture_counter}.png"
#             with element_image_filename.open("wb") as fp:
#                 element.get_image(conv_res.document).save(fp, "PNG")

#         elif isinstance(element, CodeItem): # TODO: not work.
#             code_counter += 1
#             element_image_filename = output_dir / f"{doc_filename}-code-{code_counter}.png"
#             with element_image_filename.open("wb") as fp:
#                 element.get_image(conv_res.document).save(fp, "PNG")


#     # === 收集表格信息 ===
#     tables = {}
#     for table_index, table in enumerate(conv_res.document.tables, start=1):
#         caption = table.caption_text(conv_res.document)
#         table_filename = f"{doc_filename}-table-{table_index}.png"
#         table_img_path = output_dir / table_filename
#         print(f"Looking for table image at {type(table_img_path)}")
#         if table_img_path.exists():
#             table_img = PIL.Image.open(table_img_path)
#             tables[f"table_{table_index}"] = {
#                 "caption": caption,
#                 "table_path": table_img_path.name,
#                 "width": table_img.width,
#                 "height": table_img.height,
#                 "figure_size": table_img.width * table_img.height,
#                 "figure_aspect": round(table_img.width / table_img.height, 4),
#             }

#     # === 收集图片信息 ===
#     images = {}
#     for image_index, image in enumerate(conv_res.document.pictures, start=1):
#         caption = image.caption_text(conv_res.document)
#         image_filename = f"{doc_filename}-picture-{image_index}.png"
#         image_img_path = output_dir / image_filename
        
#         if image_img_path.exists():
#             # print(f"Found image at {image_img_path}")
#             image_img = PIL.Image.open(image_img_path)
#             images[f"image_{image_index}"] = {
#                 "caption": caption,
#                 "image_path": image_img_path.name,
#                 "width": image_img.width,
#                 "height": image_img.height,
#                 "figure_size": image_img.width * image_img.height,
#                 "figure_aspect": round(image_img.width / image_img.height, 4),
#             }
            
#     # === 保存 JSON ===
#     with open(output_dir / f"{doc_filename}_images.json", "w", encoding="utf-8") as fp:
#         json.dump(images, fp, indent=4, ensure_ascii=False)

#     with open(output_dir / f"{doc_filename}_tables.json", "w", encoding="utf-8") as fp:
#         json.dump(tables, fp, indent=4, ensure_ascii=False)

#     return input_token, output_token, images, tables

# def extract_paper_content(pdf_path: str, ocr_lang: Optional[list] = None):
#     """
#     Extract structured content from a research paper PDF.

#     Args:
#         pdf_path: Path to PDF file.
#         ocr_lang: List of language codes for OCR (e.g., ["es"] for Spanish). Defaults to ["es"].

#     Returns:
#         None
#     """
#     pdf_path = Path(pdf_path)
    
#     pdf_name = pdf_path.stem # i.e. "paper"
#     # output_dir = Path("contents_debug") / 
#     output_dir = pdf_path.parent # refer to the path management of benchmark.py
#     output_dir.mkdir(parents=True, exist_ok=True)

#     # === 修正后的 cache 路径 ===
#     images_json_path = output_dir / "images_and_tables" / f"{pdf_name}_images.json"
#     tables_json_path = output_dir / "images_and_tables" / f"{pdf_name}_tables.json"

#     # === 如果都存在则直接使用缓存 ===
#     if images_json_path.exists() and tables_json_path.exists():

#         with open(images_json_path, "r", encoding="utf-8") as fp:
#             images_info = json.load(fp)

#         with open(tables_json_path, "r", encoding="utf-8") as fp:
#             tables_info = json.load(fp)

#         return _, images_info, tables_info


#     pipeline_options = PdfPipelineOptions()
#     # pipeline_options.do_ocr = True
#     IMAGE_RESOLUTION_SCALE = 5.0

#     pipeline_options.images_scale = IMAGE_RESOLUTION_SCALE # TOR
#     pipeline_options.generate_picture_images = True
    
#     pipeline_options.accelerator_options = AcceleratorOptions(
#         num_threads=30, device=AcceleratorDevice.AUTO
#     )
    
#     # pipeline_options.do_formula_enrichment = True  # <-- ENABLED
#     # pipeline_options.do_code_enrichment = True
    
#     doc_converter = DocumentConverter(
#         format_options={
#             InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
#         }
#     )

    
#     # === 转换 PDF ===
#     raw_result = doc_converter.convert(pdf_path)


#     # === 输出文件路径 ===
#     # raw_result_path = output_dir / f"{pdf_name}_raw_result.json"

#     # # === 安全保存 JSON（防止 AnyUrl 报错）===
#     # def safe_json_dump(obj, path):
#     #     if hasattr(obj, "model_dump"):
#     #         data = obj.model_dump(mode="json")
#     #     elif hasattr(obj, "__dict__"):
#     #         data = obj.__dict__
#     #     else:
#     #         data = obj
#     #     with open(path, "w", encoding="utf-8") as fp:
#     #         json.dump(data, fp, indent=4, ensure_ascii=False, default=str)

#     # safe_json_dump(raw_result.document, raw_result_path)


#     # === 保存图片与表格信息 ===
#     _, _, images_info, tables_info = gen_image_and_table(pdf_path, raw_result)

#     return _, images_info, tables_info
# if __name__ == "__main__": 
#     pdf_path = "/root/Poster-Edit/benchmark-v1-202511062200/Inner Classifier-Free Guidance and Its Taylor Expansion for Diffusion Models/paper.pdf"
#     extract_paper_content(pdf_path) 
    
    