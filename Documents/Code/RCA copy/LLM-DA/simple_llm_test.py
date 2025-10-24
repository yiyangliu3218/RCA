#!/usr/bin/env python3
"""
最简单的LLM测试 - 直接测试LLM功能，跳过复杂的规则采样
"""

import os
import json
from llms import get_registed_model

def test_llm_directly():
    """直接测试LLM功能"""
    print("=" * 50)
    print("直接测试LLM功能 (GPT-4o-mini)")
    print("=" * 50)
    
    try:
        # 创建参数
        class Args:
            def __init__(self):
                self.model_name = "gpt-4o-mini"
                self.retry = 1
        
        args = Args()
        
        # 获取LLM模型
        llm = get_registed_model(args.model_name)
        llm = llm(args)
        llm.prepare_for_inference()
        
        # 测试1: 简单规则生成
        print("测试1: 生成简单时序规则")
        prompt1 = """请为关系"Make_statement"生成一个时序逻辑规则。
格式：Make_statement(X0,X1,T1)<-other_relation(X0,X1,T0)
可选关系：Consult, Make_an_appeal_or_request, Express_intent_to_cooperate
只返回规则，不要解释。"""
        
        result1 = llm.generate_sentence(prompt1)
        print(f"✅ 规则生成成功: {result1}")
        
        # 测试2: 规则解释
        print("\n测试2: 解释时序规则")
        prompt2 = """请简单解释这个时序规则的含义：
Make_statement(X0,X1,T1)<-Consult(X0,X1,T0)
用一句话解释即可。"""
        
        result2 = llm.generate_sentence(prompt2)
        print(f"✅ 规则解释成功: {result2}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_loading():
    """测试数据加载"""
    print("\n" + "=" * 50)
    print("测试数据加载")
    print("=" * 50)
    
    try:
        from utils import load_json_data
        
        # 加载关系数据
        relation2id = load_json_data("datasets/icews14_tiny/relation2id.json")
        entity2id = load_json_data("datasets/icews14_tiny/entity2id.json")
        
        print(f"✅ 数据加载成功!")
        print(f"   - 关系数量: {len(relation2id)}")
        print(f"   - 实体数量: {len(entity2id)}")
        
        # 显示前5个关系
        print("\n前5个关系:")
        for i, (rel, rel_id) in enumerate(list(relation2id.items())[:5]):
            print(f"   {i+1}. {rel} -> {rel_id}")
        
        return relation2id
        
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        return None

def test_rule_generation_with_data(relations):
    """使用实际数据测试规则生成"""
    print("\n" + "=" * 50)
    print("使用实际数据测试规则生成")
    print("=" * 50)
    
    try:
        class Args:
            def __init__(self):
                self.model_name = "gpt-4o-mini"
                self.retry = 1
        
        args = Args()
        llm = get_registed_model(args.model_name)
        llm = llm(args)
        llm.prepare_for_inference()
        
        # 选择前3个关系进行测试
        test_relations = list(relations.keys())[:3]
        
        for i, relation in enumerate(test_relations):
            print(f"\n测试关系 {i+1}: {relation}")
            
            prompt = f"""为关系"{relation}"生成一个时序逻辑规则。
格式：{relation}(X0,X1,T1)<-other_relation(X0,X1,T0)
可选关系：{test_relations}
只返回规则，不要解释。"""
            
            result = llm.generate_sentence(prompt)
            print(f"生成的规则: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ 规则生成测试失败: {e}")
        return False

def main():
    print("🚀 简单LLM功能测试")
    print("=" * 60)
    
    # 测试1: 直接LLM功能
    if not test_llm_directly():
        print("LLM测试失败，请检查API配置")
        return
    
    # 测试2: 数据加载
    relations = test_data_loading()
    if not relations:
        print("数据加载失败")
        return
    
    # 测试3: 使用实际数据生成规则
    if test_rule_generation_with_data(relations):
        print("\n" + "=" * 60)
        print("🎉 所有测试通过!")
        print("=" * 60)
        print("✅ LLM连接正常")
        print("✅ 数据加载正常") 
        print("✅ 规则生成正常")
        print("\n💡 代码功能验证成功!")
        print("现在可以运行完整的LLM-DA流程了")

if __name__ == "__main__":
    main()


