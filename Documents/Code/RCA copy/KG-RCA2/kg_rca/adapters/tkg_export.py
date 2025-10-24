#!/usr/bin/env python3
"""
TKG Export Module - 导出分钟切片为统一格式
将 KG-RCA2 的分钟级 TKG 导出为 LLM-DA 可用的标准格式

关键修正：
1. 时间戳来源：优先从节点/边属性读取真实时间，而非目录名
2. 服务节点：不设置事件时间，只保留分钟时间用于拼窗
3. 属性类型转换：强制转换 GraphML 字符串属性为正确类型
4. 节点ID唯一性：规范化事件节点ID格式
5. 日期补全：支持多天数据的三层解析
6. 文件格式兼容：支持多种图谱格式
"""
import os
import json
import pandas as pd
import networkx as nx
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import glob
import re

def coerce_attr(value: Any) -> Union[str, int, float, bool, datetime, None]:
    """
    强制转换 GraphML 属性类型
    尝试转换为 float / int / bool / datetime，失败则保留字符串
    """
    if value is None or value == "":
        return None
    
    if isinstance(value, (int, float, bool)):
        return value
    
    if isinstance(value, str):
        # 尝试转换为数值
        try:
            # 整数
            if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                return int(value)
        except:
            pass
        
        try:
            # 浮点数
            return float(value)
        except:
            pass
        
        # 布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 时间戳（多种格式）
        try:
            # ISO 格式
            return pd.to_datetime(value)
        except:
            pass
        
        try:
            # Unix 时间戳
            if value.replace('.', '').replace('-', '').isdigit():
                return pd.to_datetime(float(value), unit='s')
        except:
            pass
        
        # 保留字符串
        return value
    
    return value

def parse_timestamp_from_path(path: Path) -> Tuple[Optional[datetime], Optional[float]]:
    """
    从路径解析时间戳
    支持 dataset/date/time/ 三层结构
    返回 (datetime对象, timestamp秒数)
    """
    try:
        parts = path.parts
        
        # 查找时间相关部分
        date_part = None
        time_part = None
        
        for part in parts:
            # 匹配日期格式 YYYY-MM-DD
            if re.match(r'\d{4}-\d{2}-\d{2}', part):
                date_part = part
            # 匹配时间格式 HH-MM-SS
            elif re.match(r'\d{2}-\d{2}-\d{2}', part):
                time_part = part
        
        if date_part and time_part:
            # 组合日期和时间
            dt_str = f"{date_part}T{time_part.replace('-', ':')}"
            dt = pd.to_datetime(dt_str)
            return dt, dt.timestamp()
        elif time_part:
            # 只有时间，使用今天日期
            today = datetime.now().strftime('%Y-%m-%d')
            dt_str = f"{today}T{time_part.replace('-', ':')}"
            dt = pd.to_datetime(dt_str)
            return dt, dt.timestamp()
        
    except Exception as e:
        print(f"⚠️ 解析路径时间戳失败 {path}: {e}")
    
    return None, None

def normalize_node_id(node_id: str, node_type: str, attrs: Dict[str, Any]) -> str:
    """
    规范化节点ID，确保全局唯一性
    事件节点：{kind}:{svc}:{name}:{iso_ts}
    服务节点：svc:{name}
    """
    if node_type == "Service":
        service = attrs.get('service', 'unknown')
        return f"svc:{service}"
    
    elif node_type in ("MetricEvent", "LogEvent"):
        service = attrs.get('service', 'unknown')
        event_ts = attrs.get('event_ts')
        
        if node_type == "MetricEvent":
            metric = attrs.get('metric', 'unknown')
            name = metric
        else:  # LogEvent
            template_id = attrs.get('template_id', 'unknown')
            name = template_id
        
        if event_ts:
            if isinstance(event_ts, datetime):
                iso_ts = event_ts.isoformat()
            else:
                iso_ts = str(event_ts)
        else:
            iso_ts = "unknown"
        
        kind = "met" if node_type == "MetricEvent" else "log"
        return f"{kind}:{service}:{name}:{iso_ts}"
    
    else:
        # 其他类型保持原样
        return node_id

def load_graph_file(file_path: Path) -> Optional[nx.MultiDiGraph]:
    """
    加载图谱文件，支持多种格式
    """
    try:
        if file_path.suffix == '.graphml':
            return nx.read_graphml(file_path)
        elif file_path.suffix == '.pkl':
            return nx.read_gpickle(file_path)
        elif file_path.suffix == '.gexf':
            return nx.read_gexf(file_path)
        elif file_path.suffix == '.json':
            with open(file_path, 'r') as f:
                data = json.load(f)
            return nx.node_link_graph(data)
        else:
            print(f"⚠️ 不支持的文件格式: {file_path.suffix}")
            return None
    except Exception as e:
        print(f"⚠️ 加载图谱文件失败 {file_path}: {e}")
        return None

def export_tkg_slices(output_dir: str, merged_dir: str) -> dict:
    """
    读取 KG-RCA2/outputs 的每分钟切片(G_t.*)，归一化存为
      nodes: {id,type,service,metric,template_id,event_ts,minute_ts,attrs...}
      edges: {src,dst,type,weight,event_ts,minute_ts}
    生成索引(index.json：时间范围、分钟列表)。
    返回 {'nodes_path':..., 'edges_path':..., 'index_path':...}
    """
    print(f"🔄 导出 TKG 切片从 {output_dir} 到 {merged_dir}")
    
    # 创建输出目录
    os.makedirs(merged_dir, exist_ok=True)
    
    # 收集所有图谱文件
    graph_files = []
    for dataset_dir in Path(output_dir).glob("*"):
        if not dataset_dir.is_dir():
            continue
            
        for date_dir in dataset_dir.glob("*"):
            if not date_dir.is_dir():
                continue
                
            for time_dir in date_dir.glob("*"):
                if not time_dir.is_dir():
                    continue
                
                # 支持多种文件格式
                for ext in ['.graphml', '.pkl', '.gexf', '.json']:
                    files = list(time_dir.glob(f"*{ext}"))
                    if files:
                        graph_files.append((time_dir, files[0]))
                        break
    
    print(f"📊 找到 {len(graph_files)} 个图谱文件")
    
    if not graph_files:
        print("⚠️ 未找到图谱文件")
        return {"nodes_path": None, "edges_path": None, "index_path": None}
    
    # 处理每个图谱文件
    all_nodes = []
    all_edges = []
    time_index = []
    
    for time_dir, graph_file in graph_files:
        try:
            # 读取图谱
            G = load_graph_file(graph_file)
            if G is None:
                continue
                
            print(f"📊 处理图谱: {graph_file} ({G.number_of_nodes()} 节点, {G.number_of_edges()} 边)")
            
            # 从路径解析分钟时间戳
            minute_dt, minute_ts = parse_timestamp_from_path(time_dir)
            if minute_ts is None:
                minute_ts = 0
                minute_dt = datetime.fromtimestamp(0)
            
            # 处理节点
            for node_id, data in G.nodes(data=True):
                # 强制转换属性类型
                attrs = {k: coerce_attr(v) for k, v in data.items()}
                
                # 确定节点类型
                node_type = attrs.get('type', 'unknown')
                
                # 提取事件时间（优先从属性读取）
                event_ts = None
                for ts_key in ['event_ts', 'timestamp', 'ts', 'time']:
                    if ts_key in attrs and attrs[ts_key] is not None:
                        event_ts = attrs[ts_key]
                        break
                
                # 规范化节点ID
                normalized_id = normalize_node_id(node_id, node_type, attrs)
                
                # 构建节点信息
                node_info = {
                    'id': normalized_id,
                    'node_type': node_type,
                    'minute_ts': minute_ts,
                    'event_ts': event_ts.timestamp() if isinstance(event_ts, datetime) else event_ts,
                }
                
                # 添加冗余字段（为后续 walk 加速）
                if 'service' in attrs:
                    node_info['service'] = attrs['service']
                if 'metric' in attrs:
                    node_info['metric'] = attrs['metric']
                if 'template_id' in attrs:
                    node_info['template_id'] = attrs['template_id']
                if 'zscore' in attrs:
                    node_info['zscore'] = attrs['zscore']
                if 'severity' in attrs:
                    node_info['severity'] = attrs['severity']
                
                # 服务节点不设置事件时间
                if node_type == "Service":
                    node_info['event_ts'] = None
                
                all_nodes.append(node_info)
            
            # 处理边
            for src, dst, data in G.edges(data=True):
                # 强制转换属性类型
                attrs = {k: coerce_attr(v) for k, v in data.items()}
                
                # 规范化源和目标节点ID
                src_attrs = G.nodes[src]
                dst_attrs = G.nodes[dst]
                src_type = src_attrs.get('type', 'unknown')
                dst_type = dst_attrs.get('type', 'unknown')
                
                normalized_src = normalize_node_id(src, src_type, src_attrs)
                normalized_dst = normalize_node_id(dst, dst_type, dst_attrs)
                
                # 确定边的事件时间
                edge_event_ts = None
                if attrs.get('type') == 'precedes':
                    # precedes 边使用较早的事件时间
                    src_event_ts = None
                    dst_event_ts = None
                    
                    for ts_key in ['event_ts', 'timestamp', 'ts', 'time']:
                        if ts_key in src_attrs:
                            src_event_ts = coerce_attr(src_attrs[ts_key])
                            break
                        if ts_key in dst_attrs:
                            dst_event_ts = coerce_attr(dst_attrs[ts_key])
                            break
                    
                    if src_event_ts and dst_event_ts:
                        edge_event_ts = min(
                            src_event_ts.timestamp() if isinstance(src_event_ts, datetime) else src_event_ts,
                            dst_event_ts.timestamp() if isinstance(dst_event_ts, datetime) else dst_event_ts
                        )
                
                # 构建边信息
                edge_info = {
                    'src': normalized_src,
                    'dst': normalized_dst,
                    'edge_type': attrs.get('type', 'unknown'),
                    'weight': float(attrs.get('weight', 1.0)),
                    'minute_ts': minute_ts,
                    'event_ts': edge_event_ts,
                }
                
                # 添加冗余字段
                edge_info['src_type'] = src_type
                edge_info['dst_type'] = dst_type
                
                all_edges.append(edge_info)
            
            # 记录时间索引
            time_index.append({
                'time_str': time_dir.name,
                'minute_ts': minute_ts,
                'minute_dt': minute_dt.isoformat(),
                'nodes_count': G.number_of_nodes(),
                'edges_count': G.number_of_edges(),
                'graph_path': str(graph_file)
            })
            
        except Exception as e:
            print(f"⚠️ 处理图谱失败 {graph_file}: {e}")
            continue
    
    # 按时间排序
    time_index.sort(key=lambda x: x['minute_ts'])
    
    # 保存节点数据
    nodes_df = pd.DataFrame(all_nodes)
    nodes_path = os.path.join(merged_dir, "nodes.parquet")
    nodes_df.to_parquet(nodes_path, index=False)
    print(f"📤 保存节点数据: {nodes_path} ({len(all_nodes)} 节点)")
    
    # 保存边数据
    edges_df = pd.DataFrame(all_edges)
    edges_path = os.path.join(merged_dir, "edges.parquet")
    edges_df.to_parquet(edges_path, index=False)
    print(f"📤 保存边数据: {edges_path} ({len(all_edges)} 边)")
    
    # 保存索引
    index_path = os.path.join(merged_dir, "index.json")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({
            'time_range': {
                'start': time_index[0]['minute_ts'] if time_index else 0,
                'end': time_index[-1]['minute_ts'] if time_index else 0
            },
            'minutes': time_index,
            'total_nodes': len(all_nodes),
            'total_edges': len(all_edges)
        }, f, indent=2, ensure_ascii=False)
    
    print(f"📤 保存索引: {index_path}")
    
    # 验证时间约束（使用 event_ts）
    print("🔍 验证时间约束...")
    precedes_edges = [e for e in all_edges if e['edge_type'] == 'precedes']
    valid_precedes = 0
    
    # 构建节点ID到节点的映射
    node_map = {n['id']: n for n in all_nodes}
    
    for edge in precedes_edges:
        src_node = node_map.get(edge['src'])
        dst_node = node_map.get(edge['dst'])
        
        if src_node and dst_node:
            src_ts = src_node.get('event_ts') or src_node.get('minute_ts', 0)
            dst_ts = dst_node.get('event_ts') or dst_node.get('minute_ts', 0)
            
            if src_ts < dst_ts:
                valid_precedes += 1
    
    print(f"✅ 时间约束验证: {valid_precedes}/{len(precedes_edges)} precedes 边满足时间递增")
    
    return {
        'nodes_path': nodes_path,
        'edges_path': edges_path,
        'index_path': index_path
    }

def validate_tkg_export(nodes_path: str, edges_path: str, index_path: str) -> bool:
    """验证导出的 TKG 数据"""
    try:
        # 检查文件存在
        if not all(os.path.exists(p) for p in [nodes_path, edges_path, index_path]):
            print("❌ 文件不存在")
            return False
        
        # 读取数据
        nodes_df = pd.read_parquet(nodes_path)
        edges_df = pd.read_parquet(edges_path)
        
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        print(f"📊 验证结果:")
        print(f"   节点数: {len(nodes_df)}")
        print(f"   边数: {len(edges_df)}")
        print(f"   时间范围: {index_data['time_range']}")
        print(f"   分钟数: {len(index_data['minutes'])}")
        
        # 检查时间戳可解析性
        valid_event_timestamps = 0
        valid_minute_timestamps = 0
        
        for _, row in nodes_df.iterrows():
            if pd.notna(row.get('event_ts')) and row.get('event_ts', 0) > 0:
                valid_event_timestamps += 1
            if pd.notna(row.get('minute_ts')) and row.get('minute_ts', 0) > 0:
                valid_minute_timestamps += 1
        
        print(f"   有效事件时间戳: {valid_event_timestamps}/{len(nodes_df)}")
        print(f"   有效分钟时间戳: {valid_minute_timestamps}/{len(nodes_df)}")
        
        # 检查节点类型分布
        node_types = nodes_df['node_type'].value_counts()
        print(f"   节点类型分布: {dict(node_types)}")
        
        # 检查边类型分布
        edge_types = edges_df['edge_type'].value_counts()
        print(f"   边类型分布: {dict(edge_types)}")
        
        # 检查时间约束
        precedes_edges = edges_df[edges_df['edge_type'] == 'precedes']
        if len(precedes_edges) > 0:
            valid_precedes = 0
            for _, edge in precedes_edges.iterrows():
                src_node = nodes_df[nodes_df['id'] == edge['src']]
                dst_node = nodes_df[nodes_df['id'] == edge['dst']]
                
                if len(src_node) > 0 and len(dst_node) > 0:
                    src_ts = src_node.iloc[0].get('event_ts') or src_node.iloc[0].get('minute_ts', 0)
                    dst_ts = dst_node.iloc[0].get('event_ts') or dst_node.iloc[0].get('minute_ts', 0)
                    
                    if src_ts < dst_ts:
                        valid_precedes += 1
            
            print(f"   时间约束验证: {valid_precedes}/{len(precedes_edges)} precedes 边满足时间递增")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

if __name__ == "__main__":
    # 测试导出
    output_dir = "outputs"
    merged_dir = "LLM-DA/datasets/tkg"
    
    result = export_tkg_slices(output_dir, merged_dir)
    print(f"📋 导出结果: {result}")
    
    if result['nodes_path']:
        validate_tkg_export(result['nodes_path'], result['edges_path'], result['index_path'])
