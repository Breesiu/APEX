# import os
# import sys
# import argparse
# from datetime import datetime
# from pathlib import Path
# from .schema import AgentState
# from .graph import create_poster_edit_graph
# from .config import OUTPUT_DIR, MAX_ITERATIONS

# def run_poster_edit_system(
#     pptx_path: str,
#     instruction: str,
#     pdf_path: str = None,
#     output_dir: str = None,
#     max_iterations: int = MAX_ITERATIONS,
#     mode = "api"
# ):
#     """
#     Main entry point for the poster editing system.
    
#     Args:
#         pptx_path: Path to input PPTX file
#         instruction: User instruction for editing
#         pdf_path: Optional path to research paper PDF
#         output_dir: Output directory for results
#         max_iterations: Maximum review-optimize iterations
    
#     Returns:
#         Final state dictionary
#     """
    
#     # Validate inputs
#     if not os.path.exists(pptx_path):
#         raise FileNotFoundError(f"PPTX file not found: {pptx_path}")
    
#     if pdf_path and not os.path.exists(pdf_path):
#         raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
#     # Setup output directory
#     if output_dir is None:
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         output_dir = OUTPUT_DIR / f"edit_{instruction[:10]}_{mode}_{timestamp}"
    
#     os.makedirs(output_dir, exist_ok=True)
#     pptx_path = Path(pptx_path)
#     output_dir = Path(output_dir) # path use Pathlib for consistency
    
#     # Create initial state
#     initial_state = AgentState(
#         pptx_path=pptx_path,
#         output_dir=output_dir,
#         user_instruction=instruction,
#         pdf_path=pdf_path,
#         max_iterations=max_iterations,
#         mode = mode
#     )
    
#     # Create and run graph
#     print("\n" + "="*80)
#     print("POSTER EDITING SYSTEM - Starting")
#     print("="*80)
#     print(f"\nInput PPTX: {pptx_path}")
#     print(f"Output Directory: {output_dir}")
#     print(f"Instruction: {instruction}")
#     if pdf_path:
#         print(f"Paper PDF: {pdf_path}")
#     print(f"Max Iterations: {max_iterations}")
#     print("\n" + "="*80 + "\n")
    
#     app = create_poster_edit_graph()
    
#     try:
#         # Execute workflow
        
#         final_state = app.invoke(initial_state)
        
#         # Print summary
#         print("\n" + "="*80)
#         print("EXECUTION COMPLETE")
#         print("="*80)
        
#         if final_state.get("error"):
#             print(f"\n❌ Error: {final_state['error']}")
#             return final_state
        
#         print(f"\n✓ Final Output: {final_state.get('current_pptx_path', 'N/A')}")
#         print(f"✓ Iterations: {final_state.get('iteration_count', 0)}")
        
#         if final_state.get("review_result"):
#             review = final_state["review_result"]
#             print(f"✓ Final Score: {review.overall_score}/100")
#             print(f"✓ Acceptable: {review.is_acceptable}")
        
#         print(f"\nAll outputs saved to: {output_dir}")
        
#         return final_state
    
#     except Exception as e:
#         print(f"\n❌ System Error: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         return {"error": str(e)}

# def main():
#     """Command-line interface"""
#     parser = argparse.ArgumentParser(
#         description="Multi-Agent Poster Editing System",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog="""
# Examples:
#   # Simple formatting change
#   python -m src.main --input poster.pptx --instruction "Increase font size in Introduction section to 24pt"
  
#   # Paper-dependent editing
#   python -m src.main --input poster.pptx --paper paper.pdf --instruction "Add a Methods section summarizing the approach from the paper"
  
#   # High-level aesthetic command
#   python -m src.main --input poster.pptx --instruction "Make the poster more modern and visually appealing"
#         """
#     )
    
#     parser.add_argument(
#         "--input", "-i",
#         required=True,
#         help="Path to input PPTX file"
#     )
    
#     parser.add_argument(
#         "--instruction", "-inst",
#         required=True,
#         help="User instruction for editing"
#     )
    
#     parser.add_argument(
#         "--paper", "-p",
#         default=None,
#         help="Path to research paper PDF (optional)"
#     )
    
#     parser.add_argument(
#         "--output", "-o",
#         default=None,
#         help="Output directory (default: auto-generated)"
#     )
    
#     parser.add_argument(
#         "--max-iterations",
#         type=int,
#         default=MAX_ITERATIONS,
#         help=f"Maximum review-optimize iterations (default: {MAX_ITERATIONS})"
#     )
    
#     parser.add_argument(
#         "--debug",
#         action="store_true",
#         help="Enable debug logging"
#     )

#     parser.add_argument(
#         "--mode",
#         default="api",
#         required=True,
#         help="Mode of code generation"
#     )
    
#     args = parser.parse_args()
    
#     # Setup logging
#     if args.debug:
#         import logging
#         logging.basicConfig(
#             level=logging.DEBUG,
#             format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#         )


# #NOTE: directory should be same with that in benchmark.py
#     # Run system
#     run_poster_edit_system(
#         pptx_path=args.input,
#         instruction=args.instruction,
#         pdf_path=args.paper,
#         output_dir=args.output,
#         max_iterations=args.max_iterations,
#         mode = args.mode
#     )

# if __name__ == "__main__":
#     main()