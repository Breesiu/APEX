# export LANGSMITH_TRACING=true
mkdir -p logs
# export LANGCHAIN_TRACING_SAMPLING_RATE=0.01
# export LANGSMITH_API_KEY="your key here"
python -m src.evaluation.judge_score_async >> logs/benchmark_qwen3-vl-log.txt 2>&1