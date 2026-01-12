import os
from typing import Optional, Dict, Tuple
import threading
# _MAX_LO_PROCS = int(os.getenv("MAX_LO_PROCS", "100"))
# _LO_PROC_SEM = threading.Semaphore(_MAX_LO_PROCS)
import subprocess
import shutil
from pathlib import Path
import json
import tempfile
import uuid
import time
from ..tools.pptx_parser import parse_pptx_to_json
from io import BytesIO
# use pptx_path only, don't use output_pathv
def convert_pptx_to_png(pptx_path, rewrite: bool = False, output_path: str = None) -> str:
    """
    将单页 PPTX 转换为 PNG 图片（依赖 LibreOffice）。

    Concurrency note (Docker/headless):
    LibreOffice uses a lock in its user profile directory. If multiple soffice
    processes share the same profile, conversions will intermittently fail with
    "returned non-zero exit status 1".
    We avoid this by using a unique UserInstallation directory per call.
    """
    pptx_path = str(pptx_path)
    if not os.path.exists(pptx_path):
        raise FileNotFoundError(f"PPTX 文件不存在: {pptx_path}")

    if not shutil.which("soffice"):
        raise EnvironmentError("未检测到 LibreOffice，请确保命令行可执行 `soffice`")

    # 输出目录
    output_dir = os.path.dirname(os.path.abspath(output_path or pptx_path))
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(pptx_path))[0]
    generated_path = os.path.join(output_dir, f"{base_name}.png")

    
    if os.path.exists(generated_path) and not rewrite:
        # # 如果用户指定了 output_path，则重命名
        # if output_path and output_path != generated_path:
        #     shutil.move(generated_path, output_path)
        #     generated_path = output_path

        print(f"[INFO] PNG 文件已存在，跳过转换: {generated_path}")
        return Path(generated_path)


    # Unique LibreOffice profile per conversion (critical for concurrency)
    profile_dir = Path(tempfile.gettempdir()) / f"lo_profile_{uuid.uuid4().hex}"
    profile_dir.mkdir(parents=True, exist_ok=True)

    # LibreOffice expects a file:// URI. Also, it must be absolute.
    profile_uri = profile_dir.resolve().as_uri()

    cmd = [
        "soffice",
        "--headless",
        f"-env:UserInstallation={profile_uri}",
        "--nologo",
        "--nofirststartwizard",
        "--norestore",
        "--convert-to", "png",
        "--outdir", output_dir,
        pptx_path,
    ]

    print(f"[INFO] 正在调用 LibreOffice 转换: {' '.join(cmd)}")

    # Small retry helps with occasional transient LO failures
    last_err: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            break
        except subprocess.CalledProcessError as e:
            last_err = e
            print(f"[WARN] soffice 转换失败 (attempt {attempt}/3). stderr:\n{e.stderr}")
            time.sleep(0.5 * attempt)
    else:
        # clean profile then raise
        try:
            shutil.rmtree(profile_dir, ignore_errors=True)
        finally:
            raise last_err  # type: ignore[misc]

    # 如果用户指定了 output_path，则重命名
    if output_path and output_path != generated_path:
        shutil.move(generated_path, output_path)
        generated_path = output_path

    # Cleanup profile dir
    shutil.rmtree(profile_dir, ignore_errors=True)

    print(f"[SUCCESS] PPTX 转换完成：{generated_path}")
    return Path(generated_path)


# """
# LaTeX 公式渲染器 - PowerPoint 原生 LaTeX 支持

# 使用 PowerPoint 2016+ 的原生 LaTeX 输入功能
# 通过 COM 接口将 $...$ 格式的 LaTeX 公式转换为 PowerPoint 原生公式对象

# 优点：
# - 不使用图片，避免定位问题
# - 公式是真正的行内对象，可以与文本混排
# - 使用 PowerPoint 原生渲染，显示效果好
# """

# import re
# import os
# import sys
# from pathlib import Path
# import win32com.client
# from win32com.client import constants
# import pythoncom


# class PowerPointLaTeXRenderer:
#     """使用 PowerPoint COM 接口渲染 LaTeX 公式"""
    
#     def __init__(self, pptx_path):
#         self.pptx_path = str(Path(pptx_path).resolve())
#         self.output_path = self.pptx_path.replace('.pptx', '_latex_rendered.pptx')
#         self.ppt_app = None
#         self.presentation = None
        
#     def find_latex_formulas(self, text):
#         """查找文本中的 LaTeX 公式 ($...$)"""
#         pattern = r'\$([^$]+?)\$'
#         return list(re.finditer(pattern, text))
    
#     def convert_latex_to_unicode_math(self, latex):
#         """
#         将 LaTeX 符号转换为 Unicode 数学字符和格式化文本
#         支持常见符号、上下标、括号、分数、根号等
#         """
#         # 预处理：移除 \left, \right, \mathrm 等
#         latex = latex.replace(r'\left', '').replace(r'\right', '')
#         latex = latex.replace(r'\mathrm', '') 
        
#         # 处理 \text{...} -> 保持原样 (去除 \text{})
#         latex = re.sub(r'\\text{([^}]+)}', r'\1', latex)

#         # 扩展的 LaTeX 到 Unicode 映射
#         replacements = {
#             # 希腊字母 (小写)
#             r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
#             r'\epsilon': 'ε', r'\varepsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η',
#             r'\theta': 'θ', r'\vartheta': 'ϑ', r'\iota': 'ι', r'\kappa': 'κ',
#             r'\lambda': 'λ', r'\mu': 'μ', r'\nu': 'ν', r'\xi': 'ξ',
#             r'\pi': 'π', r'\varpi': 'ϖ', r'\rho': 'ρ', r'\varrho': 'ϱ',
#             r'\sigma': 'σ', r'\varsigma': 'ς', r'\tau': 'τ', r'\upsilon': 'υ',
#             r'\phi': 'φ', r'\varphi': 'ϕ', r'\chi': 'χ', r'\psi': 'ψ',
#             r'\omega': 'ω',
#             # 希腊字母 (大写)
#             r'\Gamma': 'Γ', r'\Delta': 'Δ', r'\Theta': 'Θ', r'\Lambda': 'Λ',
#             r'\Xi': 'Ξ', r'\Pi': 'Π', r'\Sigma': 'Σ', r'\Upsilon': 'Υ',
#             r'\Phi': 'Φ', r'\Psi': 'Ψ', r'\Omega': 'Ω',
#             # 运算符
#             r'\pm': '±', r'\mp': '∓', r'\times': '×', r'\cdot': '⋅',
#             r'\div': '÷', r'\ast': '∗', r'\star': '⋆', r'\circ': '∘',
#             r'\bullet': '∙', r'\oplus': '⊕', r'\ominus': '⊖', r'\otimes': '⊗',
#             r'\oslash': '⊘', r'\odot': '⊙',
#             # 关系符
#             r'\leq': '≤', r'\geq': '≥', r'\neq': '≠', r'\approx': '≈',
#             r'\equiv': '≡', r'\sim': '∼', r'\simeq': '≃', r'\cong': '≅',
#             r'\propto': '∝', r'\mid': '|', r'\parallel': '∥',
#             r'\perp': '⊥',
#             # 集合符号
#             r'\in': '∈', r'\notin': '∉', r'\ni': '∋', r'\subset': '⊂',
#             r'\subseteq': '⊆', r'\supset': '⊃', r'\supseteq': '⊇',
#             r'\cap': '∩', r'\cup': '∪', r'\setminus': '∖', r'\emptyset': '∅',
#             r'\forall': '∀', r'\exists': '∃', r'\nexists': '∄',
#             # 箭头
#             r'\leftarrow': '←', r'\rightarrow': '→', r'\leftrightarrow': '↔',
#             r'\Leftarrow': '⇐', r'\Rightarrow': '⇒', r'\Leftrightarrow': '⇔',
#             r'\uparrow': '↑', r'\downarrow': '↓', r'\mapsto': '↦',
#             # 其他
#             r'\infty': '∞', r'\partial': '∂', r'\nabla': '∇', r'\angle': '∠',
#             r'\ell': 'ℓ', r'\hbar': 'ℏ', r'\Re': 'ℜ', r'\Im': 'ℑ',
#             r'\aleph': 'ℵ', r'\wp': '℘',
#             # 大型运算符
#             r'\sum': '∑', r'\prod': '∏', r'\coprod': '∐',
#             r'\int': '∫', r'\oint': '∮',
#             # 常用函数名
#             r'\sin': 'sin', r'\cos': 'cos', r'\tan': 'tan',
#             r'\csc': 'csc', r'\sec': 'sec', r'\cot': 'cot',
#             r'\log': 'log', r'\ln': 'ln', r'\lim': 'lim',
#             r'\max': 'max', r'\min': 'min', r'\sup': 'sup', r'\inf': 'inf',
#             # 空格
#             r'\,': ' ', r'\:': ' ', r'\;': ' ', r'\!': '', r'\quad': '  ', r'\qquad': '    ',
#         }
        
#         result = latex
        
#         # 处理 \frac{a}{b} -> (a)/(b)
#         while r'\frac' in result:
#             result = re.sub(r'\\frac{([^}]+)}{([^}]+)}', r'(\1)/(\2)', result)
            
#         # 处理 \sqrt{x} -> √(x)
#         while r'\sqrt' in result:
#             result = re.sub(r'\\sqrt{([^}]+)}', r'√(\1)', result)
#             result = re.sub(r'\\sqrt\[([^\]]+)\]{([^}]+)}', lambda m: self._to_superscript(m.group(1)) + r'√(' + m.group(2) + ')', result)

#         # 替换 LaTeX 命令
#         sorted_keys = sorted(replacements.keys(), key=len, reverse=True)
#         for latex_sym in sorted_keys:
#             result = result.replace(latex_sym, replacements[latex_sym])
        
#         # 处理上下标
#         result = re.sub(r'\^{([^}]+)}', lambda m: self._to_superscript(m.group(1)), result)
#         result = re.sub(r'_{([^}]+)}', lambda m: self._to_subscript(m.group(1)), result)
#         result = re.sub(r'\^([a-zA-Z0-9\+\-\=])', lambda m: self._to_superscript(m.group(1)), result)
#         result = re.sub(r'_([a-zA-Z0-9\+\-\=])', lambda m: self._to_subscript(m.group(1)), result)
        
#         # 移除剩余的花括号和反斜杠
#         result = result.replace('{', '').replace('}', '')
#         result = result.replace('\\', '')
        
#         return result
    
#     def _to_superscript(self, text):
#         """转换为上标 Unicode"""
#         superscript_map = {
#             '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
#             '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
#             '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
#             'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
#             'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
#             'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
#             'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
#             'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
#             'A': 'ᴬ', 'B': 'ᴮ', 'D': 'ᴰ', 'E': 'ᴱ', 'G': 'ᴳ',
#             'H': 'ᴴ', 'I': 'ᴵ', 'J': 'ᴶ', 'K': 'ᴷ', 'L': 'ᴸ',
#             'M': 'ᴹ', 'N': 'ᴺ', 'O': 'ᴼ', 'P': 'ᴾ', 'R': 'ᴿ',
#             'T': 'ᵀ', 'U': 'ᵁ', 'V': 'ⱽ', 'W': 'ᵂ',
#             'β': 'ᵝ', 'γ': 'ᵞ', 'δ': 'ᵟ', 'φ': 'ᵠ', 'χ': 'ᵡ',
#             "'": '′',
#         }
#         result = ''
#         for c in text:
#             if c in superscript_map:
#                 result += superscript_map[c]
#             else:
#                 result += c
#         return result
    
#     def _to_subscript(self, text):
#         """转换为下标 Unicode"""
#         subscript_map = {
#             '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
#             '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
#             '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
#             'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
#             'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
#             'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
#             'v': 'ᵥ', 'x': 'ₓ',
#             'β': 'ᵦ', 'γ': 'ᵧ', 'ρ': 'ᵨ', 'φ': 'ᵩ', 'χ': 'ᵪ',
#         }
#         result = ''
#         for c in text:
#             if c in subscript_map:
#                 result += subscript_map[c]
#             else:
#                 result += c
#         return result
    
#     def insert_equation_at_position(self, text_range, start_char, end_char, latex_code):
#         """
#         在指定位置插入公式对象
        
#         Args:
#             text_range: TextRange 对象
#             start_char: 开始字符位置（1-based）
#             end_char: 结束字符位置（1-based）
#             latex_code: LaTeX 代码
#         """
#         try:
#             # 方法1: 尝试使用 PowerPoint 的公式功能
#             # 先删除 $...$ 文本
#             formula_range = text_range.Characters(start_char, end_char - start_char + 1)
            
#             # 保存字体信息
#             try:
#                 font_name = formula_range.Font.Name
#                 font_size = formula_range.Font.Size
#             except:
#                 font_name = "Cambria Math"
#                 font_size = 18
            
#             # 尝试转换为 Unicode 数学符号
#             unicode_math = self.convert_latex_to_unicode_math(latex_code)
            
#             # 替换文本
#             formula_range.Text = unicode_math
            
#             # 设置为数学字体
#             formula_range.Font.Name = "Cambria Math"
            
#             return True
            
#         except Exception as e:
#             print(f"      ❌ 插入公式失败: {e}")
#             return False
    
#     def process_text_range(self, text_range, shape_name=""):
#         """处理文本范围中的所有公式"""
#         text = text_range.Text
#         formulas = self.find_latex_formulas(text)
        
#         if not formulas:
#             return 0
        
#         print(f"    {shape_name}: 发现 {len(formulas)} 个公式")
        
#         # 从后向前处理，避免位置偏移
#         processed = 0
#         for match in reversed(formulas):
#             latex_code = match.group(1).strip()
#             # 注意：PowerPoint COM 使用 1-based 索引
#             start_pos = match.start() + 1  # +1 因为 COM 是 1-based
#             end_pos = match.end()  # end() 已经是下一个字符的位置
            
#             print(f"      公式: ${latex_code}$ (位置 {start_pos}-{end_pos})")
            
#             if self.insert_equation_at_position(text_range, start_pos, end_pos, latex_code):
#                 processed += 1
        
#         return processed
    
#     def process_pptx(self):
#         """处理 PPTX 文件"""
#         try:
#             # 初始化 COM
#             pythoncom.CoInitialize()
            
#             print("正在启动 PowerPoint...")
#             self.ppt_app = win32com.client.Dispatch("PowerPoint.Application")
#             self.ppt_app.Visible = 1  # 显示 PowerPoint
            
#             print(f"正在打开文件: {self.pptx_path}")
#             self.presentation = self.ppt_app.Presentations.Open(
#                 self.pptx_path,
#                 ReadOnly=False,
#                 Untitled=False,
#                 WithWindow=True
#             )
            
#             total_formulas = 0
#             total_slides = self.presentation.Slides.Count
            
#             print(f"\n开始处理 {total_slides} 张幻灯片...")
#             print("=" * 60)
            
#             # 遍历所有幻灯片
#             for slide_idx in range(1, total_slides + 1):
#                 slide = self.presentation.Slides(slide_idx)
#                 print(f"\n幻灯片 {slide_idx}/{total_slides}")
                
#                 # 遍历所有形状
#                 shape_count = slide.Shapes.Count
#                 for shape_idx in range(1, shape_count + 1):
#                     try:
#                         shape = slide.Shapes(shape_idx)
                        
#                         # 检查是否有文本框
#                         if not shape.HasTextFrame:
#                             continue
                        
#                         if not shape.TextFrame.HasText:
#                             continue
                        
#                         text_range = shape.TextFrame.TextRange
#                         shape_name = f"形状 {shape_idx}"
                        
#                         count = self.process_text_range(text_range, shape_name)
#                         total_formulas += count
                        
#                     except Exception as e:
#                         print(f"    ⚠ 处理形状 {shape_idx} 时出错: {e}")
#                         continue
            
#             print("\n" + "=" * 60)
#             print(f"✅ 处理完成！共处理 {total_formulas} 个公式")
            
#             # 保存文件
#             print(f"\n正在保存到: {self.output_path}")
#             self.presentation.SaveAs(self.output_path)
#             print("✅ 保存成功！")
            
#             return True
            
#         except Exception as e:
#             print(f"\n❌ 错误: {e}")
#             import traceback
#             traceback.print_exc()
#             return False
            
#         finally:
#             # 清理
#             try:
#                 if self.presentation:
#                     self.presentation.Close()
#                 if self.ppt_app:
#                     self.ppt_app.Quit()
#             except:
#                 pass
            
#             pythoncom.CoUninitialize()


def encode_image_to_base64(image_path: Path) -> str:
    """Encode image to base64 for MLLM input"""
    import base64
    
    # with open(image_path, 'rb') as f:
    #     return base64.b64encode(f.read()).decode('utf-8')
    try:
        # Open the image using PIL
        # with Image.open(image_path) as img:
        #     # Convert to RGBA (to preserve transparency if present)
        #     # and quantize to 256 colors using Fast Octree method
        #     compressed_img = img.convert("RGBA").quantize(
        #         colors=256, 
        #         method=Image.Quantize.FASTOCTREE
        #     )
            
        #     # Save to buffer with optimization
        #     buffered = BytesIO()
        #     compressed_img.save(buffered, format="PNG", optimize=True)
            
        #     # Encode buffer to base64
        #     return base64.b64encode(buffered.getvalue()).decode('utf-8')
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
            
    except Exception as e:
        print(f"Error compressing/encoding image {image_path}: {e}")
        # Fallback to original raw read if compression fails
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

'''
def convert_pptx_to_png(pptx_path: str, output_path: Optional[str] = None) -> str:
    """
    Convert PPTX slide to PNG for visual review.
    
    Note: This requires LibreOffice or a similar tool to be installed.
    For a pure Python solution, you'd need to implement rendering.
    
    Args:
        pptx_path: Path to PPTX file
        output_path: Output PNG path (optional)
    
    Returns:
        Path to generated PNG
    """
    if output_path is None:
        output_path = pptx_path.replace('.pptx', '.png')
    
    # Placeholder implementation
    # In production, use:
    # 1. python-pptx + Pillow for rendering
    # 2. Call LibreOffice: soffice --headless --convert-to png --outdir <dir> <file>
    # 3. Use a cloud service API
    
    print(f"INFO: Converting {pptx_path} to PNG (stub implementation)")
    print(f"      Output will be: {output_path}")
    
    # For now, just return the path
    # In real implementation, actually generate the image
    return output_path

'''


from langchain_openai import ChatOpenAI
from ..config import QWEN3_8B_LOCAL_ENDPOINT, QWEN3_VL_8B_LOCAL_ENDPOINT, PLANNER_MODEL
import os
from langchain_core.messages import SystemMessage, HumanMessage


def main():
#     """主函数"""
#     pptx_file = "ByPosterGen.pptx"
    
#     if not os.path.exists(pptx_file):
#         print(f"❌ 错误: 文件不存在 - {pptx_file}")
#         print(f"当前目录: {os.getcwd()}")
#         return 1
    
#     print("LaTeX 公式渲染器 - PowerPoint COM 方法")
#     print("=" * 60)
#     print(f"输入文件: {pptx_file}")
#     print(f"输出文件: {pptx_file.replace('.pptx', '_latex_rendered.pptx')}")
#     print("=" * 60)
    
#     renderer = PowerPointLaTeXRenderer(pptx_file)
#     success = renderer.process_pptx()
    
#     if success:
#         print("\n🎉 全部完成！")
#         return 0
#     else:
#         print("\n❌ 处理失败")
#         return 1
    # # from .pptx_parser import parse_pptx_to_json
    # # # convert_pptx_to_png("/root/Poster_ppt_edit/Poster-Edit/benchmark_withpostergen_flat/ICLR-2024-4-Butterfly_Effects_of_SGD_Noise_Error_Amplification_in_Behavior_Cloning_and_Autoregression/ByPosterGen.pptx")
    # # poster_json = parse_pptx_to_json("/root/Poster_ppt_edit/Poster-Edit/benchmark_withpostergen_flat/ICLR-2024-4-Butterfly_Effects_of_SGD_Noise_Error_Amplification_in_Behavior_Cloning_and_Autoregression/ByPosterGen.pptx")
    # convert_pptx_to_png("/root/Poster_ppt_edit/Poster-Edit/benchmark_withpostergen_flat/ICLR-2024-54-Transformers_Learn_Nonlinear_Features_In_Context/ByPosterGen.pptx")
    # convert_pptx_to_png("/root/Poster_ppt_edit/Poster-Edit/benchmark_withpostergen_flat/ICML-2023-55-Coin_Sampling_Gradient-Based_Bayesian_Inference_without_Learning_Rates/ByPosterGen.pptx")
    # convert_pptx_to_png("/root/Poster_ppt_edit/Poster-Edit/benchmark_withpostergen_flat/ICML-2024-56-Fault_Tolerant_ML_Efficient_Meta-Aggregation_and_Synchronous_Training/ByPosterGen.pptx")
    # convert_pptx_to_png("/root/Poster_ppt_edit/Poster-Edit/benchmark_withpostergen_flat/ICML-2023-58-Optimizing_the_Collaboration_Structure_in_Cross-Silo_Federated_Learning/ByPosterGen.pptx")

    benchmark_dir =  Path("benchmark")

    if not benchmark_dir.exists():
        # print(f"ERROR: {benchmark_dir} not found. Update benchmark_dir in the script.", file=sys.stderr)
        return 2
    
    
    pptx_files = sorted(benchmark_dir.rglob("poster_v1.pptx"))
    if not pptx_files:
        print(f"No poster_v1.pptx found under: {benchmark_dir}")
        return 0

    print(f"Found {len(pptx_files)} files.")
    failures = 0

    for pptx_path in pptx_files:
        # out_dir = pptx_path.parent / "poster_v1_png"
        # out_dir.mkdir(parents=True, exist_ok=True)
        convert_pptx_to_png(pptx_path)

if __name__ == "__main__":
    # sys.exit(main())
    main()