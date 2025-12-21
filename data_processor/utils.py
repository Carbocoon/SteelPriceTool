import re
import pandas as pd

def format_thickness(thickness_str: str) -> str:
    """格式化厚度/负差字符串，防止Excel将其识别为日期"""
    if not thickness_str:
        return ""
        
    # 处理范围格式 (如 "3-4")
    parts = re.split(r'[-－]', str(thickness_str))
    formatted_parts = []
    
    for part in parts:
        part = part.strip()
        try:
            # 尝试转换为浮点数
            val = float(part)
            # 如果是整数（如3.0），确保显示为3.0
            # 如果是小数（如2.5），保持原样
            # 关键是：如果是整数，必须带小数点
            if val.is_integer():
                formatted_parts.append(f"{int(val)}.0")
            else:
                formatted_parts.append(str(val))
        except ValueError:
            # 如果无法转换（可能是非数字字符），保持原样
            formatted_parts.append(part)
            
    return "-".join(formatted_parts)

def normalize_length(length_str: str) -> str:
    """将长度统一转换为mm单位"""
    if not length_str:
        return ""
        
    # 提取数字和单位
    match = re.match(r'([\d\.]+)\s*(米|m|mm|毫米)', length_str.lower())
    if match:
        value = float(match.group(1))
        unit = match.group(2)
        
        if unit in ['米', 'm']:
            return str(int(value * 1000))
        else:
            return str(int(value))
    
    # 如果只有数字，默认假设是mm? 或者保持原样
    # 这里假设如果只有数字，可能是米也可能是毫米，比较危险，暂时尝试提取纯数字
    try:
        val = float(length_str)
        # 如果小于20，通常是米
        if val < 20:
            return str(int(val * 1000))
        else:
            return str(int(val))
    except:
        return length_str

def parse_spec_cell(cell_content: str) -> list[str]:
    """解析包含多种分隔符的规格单元格"""
    if pd.isna(cell_content):
        return []
    
    content = str(cell_content)
    # 使用正则表达式分割：支持 <br>, 换行符 \n, 中文逗号，英文逗号，以及空格
    # 注意：空格可能会误伤（例如 "30 * 30"），但通常规格是紧凑的 "30*30"
    # 如果规格中有空格（如 "30 * 30"），需要先标准化
    
    # 1. 先统一替换常见的非分隔符空格（如 * 号周围的空格）
    content = re.sub(r'\s*\*\s*', '*', content)
    
    # 2. 使用多种分隔符进行分割
    # 分隔符包括：<br>, \n, ,, ，, 以及空格
    parts = re.split(r'<br>|[\n,，\s]+', content)
    
    # 3. 过滤空字符串并去重
    specs = []
    seen = set()
    for p in parts:
        s = p.strip()
        if s and s not in seen:
            specs.append(s)
            seen.add(s)
            
    return specs
