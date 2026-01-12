# export LANGSMITH_TRACING=true
mkdir -p logs
export LANGCHAIN_TRACING_SAMPLING_RATE=0
# export LANGSMITH_API_KEY="your key here"
# export LANGCHAIN_TRACING_V2=false
# python -m src.evaluation.benchmark_multi >> logs/benchmark_qwen_ite3_log.txt 2>&1
python -m src.evaluation.benchmark_multi 