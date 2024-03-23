#!/bin/bash

source ~/miniconda3/etc/profile.d/conda.sh
# 激活Conda环境
conda activate tog

cd /Users/czy/Desktop/3月毕设/ToG/ToG

# 运行Python脚本
python main_czy.py --dataset czy-api --max_length 256 --temperature_exploration 0.8 --temperature_reasoning 0 --width 3 --depth 3 --remove_unnecessary_rel True --LLM_type gpt-3.5-turbo --opeani_api_keys sk-xxxxx --num_retain_entity 5 --prune_tools llm

