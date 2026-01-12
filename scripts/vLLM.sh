# export CUDA_VISIBLE_DEVICES=6
# vllm serve /root/shared_planing/LLM_model/Qwen3-VL-8B-Instruct --port 8050 

# export CUDA_VISIBLE_DEVICES=7
# vllm serve /root/shared_planing/LLM_model/Qwen3-8B --port 8040 

# Use GPUs 6 and 7 (adjust device ids if needed)
export CUDA_VISIBLE_DEVICES=0,1

# Disable vLLM P2P transfers (keeps communication on PCIe/NVLink depending on runtime)
export NCCL_P2P_DISABLE=1

# vllm serve /root/shared_planing/LLM_model/Qwen3-VL-32B-Instruct \
#     --port 8050 \
#     --tensor-parallel-size 2 \
#     --max-model-len 163840 \
#     --disable-custom-all-reduce

vllm serve /root/shared_planing/LLM_model/Qwen3-VL-30B-A3B-Instruct \
    --port 8050 \
    --tensor-parallel-size 2 \
    --max-model-len 163840 \
    --disable-custom-all-reduce


# export CUDA_VISIBLE_DEVICES=0,1

# # Disable vLLM P2P transfers (keeps communication on PCIe/NVLink depending on runtime)
# export NCCL_P2P_DISABLE=1

# vllm serve /root/shared_planing/LLM_model/Qwen3-VL-30B-A3B-Instruct \
#     --port 8055 \
#     --tensor-parallel-size 2 \
#     --disable-custom-all-reduce