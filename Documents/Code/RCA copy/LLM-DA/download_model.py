#!/usr/bin/env python3
"""
手动下载SentenceTransformer模型
"""

import os
from sentence_transformers import SentenceTransformer

def download_model():
    """下载BERT模型"""
    print("=" * 50)
    print("手动下载BERT模型")
    print("=" * 50)
    
    try:
        print("正在下载 bert-base-nli-mean-tokens 模型...")
        print("这个模型用于计算关系之间的相似度")
        print("大小约438MB，请耐心等待...")
        
        # 下载模型
        model = SentenceTransformer('bert-base-nli-mean-tokens')
        
        print("✅ 模型下载成功!")
        print(f"模型保存位置: {model._modules['0'].auto_model.config.name_or_path}")
        
        # 测试模型
        print("\n测试模型功能...")
        test_sentences = ["Make_statement", "Consult", "Make_an_appeal_or_request"]
        embeddings = model.encode(test_sentences)
        print(f"✅ 模型测试成功! 生成了 {embeddings.shape} 的嵌入向量")
        
        return True
        
    except Exception as e:
        print(f"❌ 模型下载失败: {e}")
        return False

def check_model_cache():
    """检查模型缓存"""
    print("\n" + "=" * 50)
    print("检查模型缓存")
    print("=" * 50)
    
    # 检查常见的缓存位置
    cache_dirs = [
        os.path.expanduser("~/.cache/huggingface/transformers"),
        os.path.expanduser("~/.cache/torch/sentence_transformers"),
        os.path.expanduser("~/.cache/sentence_transformers"),
    ]
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            print(f"✅ 找到缓存目录: {cache_dir}")
            # 列出文件
            try:
                for root, dirs, files in os.walk(cache_dir):
                    if "bert-base-nli-mean-tokens" in root:
                        print(f"   - 模型文件: {root}")
                        for file in files[:5]:  # 只显示前5个文件
                            print(f"     * {file}")
                        if len(files) > 5:
                            print(f"     ... 还有 {len(files)-5} 个文件")
            except:
                pass
        else:
            print(f"❌ 缓存目录不存在: {cache_dir}")

def main():
    print("🔽 手动下载SentenceTransformer模型")
    print("=" * 60)
    
    # 检查缓存
    check_model_cache()
    
    # 下载模型
    if download_model():
        print("\n" + "=" * 60)
        print("🎉 模型下载完成!")
        print("=" * 60)
        print("现在可以运行规则采样了:")
        print("python3 rule_sampler.py -d icews14_tiny -m 2 -n 3 -p 1 -s 1 --is_relax_time No")
    else:
        print("\n❌ 模型下载失败，请检查网络连接")

if __name__ == "__main__":
    main()


