# export LANGSMITH_TRACING=true
mkdir -p logs
export LANGCHAIN_TRACING_SAMPLING_RATE=0.01
export LANGSMITH_API_KEY=="your key here"
python -m src.evaluation.benchmark >> logs/benchmark_log.txt 2>&1