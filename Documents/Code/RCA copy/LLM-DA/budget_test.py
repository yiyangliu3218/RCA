#!/usr/bin/env python3

import os
import json
import shutil
from utils import load_json_data, save_json_data

def create_tiny_dataset():

    try:
        # 读取原始数据
        with open("datasets/icews14/train.txt", "r") as f:
            lines = f.readlines()
        
        # 只取前50行
        tiny_lines = lines[:50]
        
        # 创建tiny数据集目录
        os.makedirs("datasets/icews14_tiny", exist_ok=True)
        
        # 保存tiny训练数据
        with open("datasets/icews14_tiny/train.txt", "w") as f:
            f.writelines(tiny_lines)
        
        # 复制必要文件
        for file in ["relation2id.json", "entity2id.json", "ts2id.json"]:
            shutil.copy(f"datasets/icews14/{file}", f"datasets/icews14_tiny/{file}")
        
        # 创建tiny的验证和测试集 (各10条)
        with open("datasets/icews14_tiny/valid.txt", "w") as f:
            f.writelines(lines[50:60])
        
        with open("datasets/icews14_tiny/test.txt", "w") as f:
            f.writelines(lines[60:70])
        
        print(f"超小型数据集创建成功!")
        print(f"   - 训练数据: {len(tiny_lines)} 条")
        print(f"   - 验证数据: 10 条")
        print(f"   - 测试数据: 10 条")
        print(f"   - 总数据量: {len(tiny_lines) + 20} 条")
        
        return True
        
    except Exception as e:
        print(f"{e}")
        return False

def test_llm_with_limit():
    
    try:
        from llms import get_registed_model
        
        class Args:
            def __init__(self):
                self.model_name = "gpt-4o-mini"  # 最便宜的模型
                self.retry = 1  # 只重试1次
        
        args = Args()
        llm = get_registed_model(args.model_name)
        llm = llm(args)
        llm.prepare_for_inference()
        
        # 极简测试prompt
        test_prompt = "生成一个时序规则: Make_statement(X0,X1,T1)<-Consult(X0,X1,T0)"
        result = llm.generate_sentence(test_prompt)
        
        print("LLM连接成功!")
        print(f"模型: {args.model_name}")
        print(f"结果: {result[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"LLM测试失败: {e}")
        return False

def create_budget_config():
    
    config = {
        "model_name": "gpt-4o-mini",
        "max_rules_per_relation": 2,  # 每个关系最多生成2个规则
        "max_relations": 5,  # 只处理5个关系
        "max_iterations": 1,  # 只迭代1次
        "max_samples": 3,  # 最多采样3次
        "timeout": 30,  # 30秒超时
        "retry": 1  # 只重试1次
    }
    
    with open("budget_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    for key, value in config.items():
        print(f"   - {key}: {value}")
    
    return config

def estimate_cost():
    """估算成本"""
    print("\n" + "=" * 50)
    print("成本估算")
    print("=" * 50)
    
    # GPT-4o-mini 价格 (2024年)
    input_cost_per_1k = 0.00015  # $0.15 per 1M tokens
    output_cost_per_1k = 0.0006  # $0.60 per 1M tokens
    
    # 估算token使用量
    estimated_input_tokens = 1000  # 每次调用约1000 tokens
    estimated_output_tokens = 200  # 每次输出约200 tokens
    
    # 调用次数
    max_calls = 10 
    
    total_input_cost = (estimated_input_tokens / 1000) * input_cost_per_1k * max_calls
    total_output_cost = (estimated_output_tokens / 1000) * output_cost_per_1k * max_calls
    total_cost = total_input_cost + total_output_cost
    
    print(f"   - 最大API调用次数: {max_calls}")
    print(f"   - 预估输入tokens: {estimated_input_tokens * max_calls:,}")
    print(f"   - 预估输出tokens: {estimated_output_tokens * max_calls:,}")
    print(f"   - 预估总成本: ${total_cost:.4f} (约¥{total_cost * 7:.2f})")

def create_budget_commands():
    
    commands = [
        "# 1. 规则采样 (极简参数)",
        "python3 rule_sampler.py -d icews14_tiny -m 2 -n 3 -p 1 -s 1 --is_relax_time No",
        "",
        "# 2. 规则生成 (限制参数)",
        "python3 Iteration_reasoning.py -d icews14_tiny --model_name gpt-4o-mini -f 2 -l 1 --is_rel_name Yes",
        "",
        "# 3. 规则排序",
        "python3 rank_rule.py -p copy_gpt-4o-mini-top-0-f-2-l-1 -d icews14_tiny",
        "",
        "# 4. 推理测试",
        "python3 reasoning.py -p copy_gpt-4o-mini-top-0-f-2-l-1 -d icews14_tiny",
        "",
        "# 5. 评估",
        "python3 evaluate.py -d icews14_tiny -c 'llm_test_apply_all_conf_cands_r[1,2,3]_w0_score_12[0.1,0.5,\\'TLogic\\',0.0,0.01,0]_top_20_et_origin.json' --graph_reasoning_type TiRGN --rule_weight 0.9"
    ]
    
    print("💡 建议的运行顺序:")
    for cmd in commands:
        print(cmd)
    
    # 保存到文件
    with open("budget_commands.sh", "w") as f:
        f.write("#!/bin/bash\n")
        for cmd in commands:
            if not cmd.startswith("#") and cmd.strip():
                f.write(cmd + "\n")

def main():

    # 1. 创建超小型数据集
    if not create_tiny_dataset():
        return
    
    # 2. 测试LLM连接
    if not test_llm_with_limit():
        print("LLM连接失败，请检查API配置")
        return
    
    # 3. 创建省钱配置
    create_budget_config()
    
    # 4. 估算成本
    estimate_cost()
    
    # 5. 生成运行命令
    create_budget_commands()

if __name__ == "__main__":
    main()
