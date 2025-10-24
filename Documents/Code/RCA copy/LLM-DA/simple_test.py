#!/usr/bin/env python3
"""
简单测试脚本 - 使用GPT-4o-mini测试LLM-DA功能
只处理少量数据，验证代码是否能正常运行
"""

import os
import sys
import json
from utils import load_json_data, save_json_data
from llms import get_registed_model
import argparse

def test_llm_connection():
    """测试LLM连接"""
    print("=" * 50)
    print("测试LLM连接 (GPT-4o-mini)")
    print("=" * 50)
    
    try:
        # 创建简单的参数对象
        class Args:
            def __init__(self):
                self.model_name = "gpt-4o-mini"
                self.retry = 3
        
        args = Args()
        
        # 获取LLM模型
        llm = get_registed_model(args.model_name)
        llm = llm(args)
        llm.prepare_for_inference()
        
        # 测试简单生成
        test_prompt = "请生成一个简单的时序逻辑规则，格式如：relation(X0,X1,T1)<-other_relation(X0,X1,T0)"
        result = llm.generate_sentence(test_prompt)
        
        print("✅ LLM连接成功!")
        print(f"模型: {args.model_name}")
        print(f"测试生成结果: {result[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM连接失败: {e}")
        return False

def test_data_loading():
    """测试数据加载"""
    print("\n" + "=" * 50)
    print("测试数据加载")
    print("=" * 50)
    
    try:
        # 加载小量数据
        relation2id = load_json_data("datasets/icews14/relation2id.json")
        entity2id = load_json_data("datasets/icews14/entity2id.json")
        
        print(f"✅ 数据加载成功!")
        print(f"   - 关系数量: {len(relation2id)}")
        print(f"   - 实体数量: {len(entity2id)}")
        
        # 只取前5个关系进行测试
        test_relations = dict(list(relation2id.items())[:5])
        print(f"   - 测试关系: {list(test_relations.keys())}")
        
        return test_relations
        
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        return None

def test_rule_generation(test_relations):
    """测试规则生成"""
    print("\n" + "=" * 50)
    print("测试规则生成")
    print("=" * 50)
    
    try:
        # 创建参数
        class Args:
            def __init__(self):
                self.model_name = "gpt-4o-mini"
                self.retry = 3
        
        args = Args()
        
        # 获取LLM模型
        llm = get_registed_model(args.model_name)
        llm = llm(args)
        llm.prepare_for_inference()
        
        # 构建简单的prompt
        test_relation = list(test_relations.keys())[0]
        candidate_rels = list(test_relations.keys())
        
        prompt = f"""你是一个时序知识图谱推理专家。请为关系"{test_relation}"生成一个简单的时序逻辑规则。

规则格式应该是：{test_relation}(X0,X1,T1)<-other_relation(X0,X1,T0)

可选的关系包括：{candidate_rels}

请只返回一个规则，不要解释。"""
        
        print(f"正在为关系 '{test_relation}' 生成规则...")
        result = llm.generate_sentence(prompt)
        
        print("✅ 规则生成成功!")
        print(f"生成的规则: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ 规则生成失败: {e}")
        return None

def create_mini_dataset():
    """创建一个小型测试数据集"""
    print("\n" + "=" * 50)
    print("创建小型测试数据集")
    print("=" * 50)
    
    try:
        # 读取原始训练数据
        with open("datasets/icews14/train.txt", "r") as f:
            lines = f.readlines()
        
        # 只取前100行作为测试数据
        mini_lines = lines[:100]
        
        # 创建mini数据集目录
        os.makedirs("datasets/icews14_mini", exist_ok=True)
        
        # 保存mini训练数据
        with open("datasets/icews14_mini/train.txt", "w") as f:
            f.writelines(mini_lines)
        
        # 复制其他必要文件
        import shutil
        for file in ["relation2id.json", "entity2id.json", "ts2id.json"]:
            shutil.copy(f"datasets/icews14/{file}", f"datasets/icews14_mini/{file}")
        
        print("✅ 小型测试数据集创建成功!")
        print(f"   - 训练数据: {len(mini_lines)} 条")
        print(f"   - 数据集路径: datasets/icews14_mini/")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建测试数据集失败: {e}")
        return False

def main():
    print("🚀 开始LLM-DA简单测试 (使用GPT-4o-mini)")
    print("=" * 60)
    
    # 测试1: LLM连接
    if not test_llm_connection():
        print("LLM连接失败，请检查API配置")
        return
    
    # 测试2: 数据加载
    test_relations = test_data_loading()
    if not test_relations:
        print("数据加载失败")
        return
    
    # 测试3: 规则生成
    rule = test_rule_generation(test_relations)
    if not rule:
        print("规则生成失败")
        return
    
    # 测试4: 创建小型数据集
    if create_mini_dataset():
        print("\n" + "=" * 60)
        print("🎉 所有测试通过!")
        print("=" * 60)
        print("现在你可以运行完整的LLM-DA流程:")
        print("1. python3 rule_sampler.py -d icews14_mini -m 2 -n 5 -p 1 -s 1")
        print("2. python3 Iteration_reasoning.py -d icews14_mini --model_name gpt-4o-mini -f 5 -l 2")
        print("\n注意: 使用gpt-4o-mini模型成本更低!")

if __name__ == "__main__":
    main()
