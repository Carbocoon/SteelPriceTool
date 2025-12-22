import pandas as pd
import numpy as np
import re
import streamlit as st
from io import BytesIO
from typing import Dict, List, Tuple, Optional, Any
from .utils import normalize_length
from .strategies import ZhengdaGalvanizedStrategy, FourColumnStrategy, ThreeColumnStrategy

class ProductDataProcessor:
    """产品数据处理核心类 - 动态识别版本"""
    
    def __init__(self):
        self.strategies = [
            ZhengdaGalvanizedStrategy(),
            FourColumnStrategy(),
            ThreeColumnStrategy() # Default fallback
        ]

    def extract_all_info_from_file(self, df: pd.DataFrame, filename: str) -> Dict[str, Any]:
        """从整个文件内容中提取所有相关信息"""
        file_info = {
            'product_type': '',      # 产品类型
            'product_name': '',      # 品名
            'length': '',           # 长度
            'price_type': '',       # 计价方式（过磅/理计）
            'brand': '',            # 品牌/厂家
            'contact': '',          # 联系方式
            'unit': '',             # 单位
            'material': '',         # 材质
            'standard': '',         # 执行标准
            'location_province': '', # 提货地/省
            'location_city': '',    # 提货地/市
            'location_area': '',    # 提货地/区
            'notes': []             # 备注信息
        }
        
        # 将整个DataFrame转换为字符串进行搜索
        df_str = df.astype(str).to_string()
        # 创建无空格版本用于搜索（解决"方 矩 管"这种带空格的情况）
        df_str_nospaces = df_str.replace(" ", "")
        
        # 1. 识别产品类型
        product_types = ['方矩管', '板材', '型材', '管材', '矿用品', '棒材', '彩涂卷', '不锈钢']
        for p_type in product_types:
            if p_type in df_str or p_type in df_str_nospaces:
                file_info['product_type'] = p_type
                break
        
        # 补充识别：热镀管/镀锌管 -> 管材
        if not file_info['product_type']:
            if '热镀管' in df_str or '镀锌管' in df_str:
                file_info['product_type'] = '管材'

        # 2. 识别品名（从文件名和内容中提取）
        # 先尝试从文件名提取
        product_keywords = ['热镀锌', '冷轧', '热轧', '镀锌', '不锈钢', '彩涂', '黑退', '热镀']
        for keyword in product_keywords:
            if keyword in filename:
                file_info['product_name'] = keyword
                break
        
        # 如果文件名中没有，尝试从内容中提取
        if not file_info['product_name']:
            for keyword in product_keywords:
                if keyword in df_str:
                    file_info['product_name'] = keyword
                    break
        
        # 特殊处理：如果是正大热镀管，直接修正品名
        if '正大热镀管' in df_str or '正大热镀管' in filename:
            file_info['product_name'] = '镀锌管'
            if not file_info['product_type']:
                file_info['product_type'] = '管材'
        
        # 如果还是没有，且是方矩管，默认为"黑"
        if not file_info['product_name'] and '方矩管' in file_info['product_type']:
            file_info['product_name'] = '黑'
        
        # 3. 识别长度信息
        length_pattern = r'长度\s*([\d\.]+)\s*(米|mm|毫米|m)'
        length_matches = re.findall(length_pattern, df_str)
        if length_matches:
            raw_length = f"{length_matches[0][0]}{length_matches[0][1]}"
            file_info['length'] = normalize_length(raw_length)
        
        # 4. 识别计价方式
        if '检斤价' in df_str or '过磅' in df_str:
            file_info['price_type'] = '过磅'
        elif '理计' in df_str or '理论' in df_str:
            file_info['price_type'] = '理计'
        
        # 5. 识别品牌/厂家
        # 优先识别正大制管
        if "正大" in df_str or "正大" in filename:
            file_info['brand'] = "正大制管"
        else:
            brand_patterns = [
                r'品牌[：:]\s*([^\s]+)',
                r'厂家[：:]\s*([^\s]+)',
                r'([^\s]+制管)',
                r'([^\s]+钢铁)',
                r'([^\s]+公司)'
            ]
            
            for pattern in brand_patterns:
                matches = re.findall(pattern, df_str)
                if matches:
                    # 过滤掉过长的匹配（防止匹配到长句免责声明）
                    if len(matches[0]) < 10:
                        file_info['brand'] = matches[0]
                        break
        
        # 6. 识别联系方式
        phone_pattern = r'[电话：:]\s*(\d{3,4}-\d{7,8}|\d{11}|400-\d{3,4}-\d{3,4})'
        phone_matches = re.findall(phone_pattern, df_str)
        if phone_matches:
            file_info['contact'] = phone_matches[0]
        
        # 7. 识别材质
        material_patterns = [
            r'材质[：:]\s*([^\s]+)',
            r'([Qq]\d+[A-Fa-f]?)',
            r'(不锈钢\d{3,4})',
            r'(SPCC|SPHC|SS400)'
        ]
        
        for pattern in material_patterns:
            matches = re.findall(pattern, df_str)
            if matches:
                file_info['material'] = matches[0]
                break
        
        # 8. 识别执行标准
        standard_pattern = r'(GB/T?\s*\d+|YB/T?\s*\d+|Q/BQB|ASTM|JIS|DIN)'
        standard_matches = re.findall(standard_pattern, df_str)
        if standard_matches:
            file_info['standard'] = standard_matches[0]
        
        # 9. 识别备注信息
        # 收集所有可能包含备注信息的行
        note_keywords = ['说明', '备注', '注意', '提示', '要求']
        for i in range(min(20, len(df))):
            row_str = df.iloc[i].astype(str).str.cat(sep=' ')
            for keyword in note_keywords:
                if keyword in row_str:
                    file_info['notes'].append(row_str.strip())
        
        # 10. 设置单位
        # 统一默认为件，不再从文件中提取，避免误识别为价格单位
        file_info['unit'] = '件'
        
        return file_info
    
    def extract_price_data(self, df: pd.DataFrame) -> Tuple[List[Dict], List[str]]:
        """从源数据表格中提取价格信息，返回价格数据和列头信息"""
        for strategy in self.strategies:
            is_match, header_row, data_start_row = strategy.match(df)
            if is_match:
                return strategy.extract(df, header_row, data_start_row)
        return [], []
    
    def analyze_spec_format(self, specs_data: List[Dict]) -> Dict[str, str]:
        """分析规格数据的格式，确定如何填写规格字段"""
        spec_analysis = {
            'spec1_type': '',  # 规格1应该是什么（壁厚/厚度/宽度等）
            'spec2_type': '',  # 规格2应该是什么
            'spec3_type': '',  # 规格3应该是什么
            'spec4_type': '',  # 规格4应该是什么
            'dimension_pattern': ''  # 尺寸模式（如"长*宽"）
        }
        
        if not specs_data:
            return spec_analysis
        
        # 分析第一个规格
        first_spec = specs_data[0]['规格']
        
        # 检查是否是"长*宽"格式
        if '*' in first_spec:
            spec_analysis['dimension_pattern'] = '长*宽'
            # 对于方矩管，规格1通常是壁厚
            spec_analysis['spec1_type'] = '壁厚'
            
            # 尝试从规格字符串提取长宽
            match = re.match(r'(\d+)\s*\*\s*(\d+)', first_spec)
            if match:
                length, width = match.groups()
                spec_analysis['spec2_type'] = f'长{length}*宽{width}'
            else:
                spec_analysis['spec2_type'] = '尺寸'
        
        # 检查厚度是否包含范围
        first_thickness = specs_data[0]['厚度']
        if '-' in first_thickness:
            spec_analysis['spec1_type'] = '厚度范围'
        elif 'mm' in first_thickness or '毫米' in first_thickness:
            spec_analysis['spec1_type'] = '厚度'
        else:
            spec_analysis['spec1_type'] = '厚度'
        
        return spec_analysis
    
    def create_template_dataframe(self, source_data: List[Dict], 
                                 file_info: Dict[str, Any],
                                 specs_analysis: Dict[str, str]) -> pd.DataFrame:
        """创建符合模板格式的DataFrame - 完全动态"""
        
        # 构建模板记录
        template_records = []
        
        for item in source_data:
            spec_str = item['规格']
            thickness = item['厚度']
            price = item['价格']
            
            # 解析规格字符串，提取可能的尺寸信息
            dimension_match = re.match(r'(\d+)\s*\*\s*(\d+)', spec_str)
            
            # 确定品名后缀（方管/矩管）
            shape_suffix = ""
            if dimension_match:
                dim1, dim2 = map(int, dimension_match.groups())
                if dim1 == dim2:
                    shape_suffix = "方管"
                else:
                    shape_suffix = "矩管"
            elif "方" in spec_str:
                shape_suffix = "方管"
            elif "矩" in spec_str:
                shape_suffix = "矩管"
            
            # 构建完整品名
            base_name = file_info['product_name'] or ''
            
            full_product_name = base_name
            if shape_suffix:
                if base_name == '黑':
                    full_product_name = f"黑{shape_suffix}"
                elif shape_suffix not in base_name:
                    if '方矩管' in base_name:
                        full_product_name = base_name.replace('方矩管', shape_suffix)
                    else:
                        full_product_name = f"{base_name}{shape_suffix}"
            
            # 特殊处理：如果是正大热镀管模式，品名强制为"镀锌管"
            if '热镀' in file_info.get('product_name', '') or '镀锌' in file_info.get('product_name', ''):
                if file_info.get('product_type') == '管材':
                    full_product_name = "镀锌管"

            if dimension_match:
                dim1, dim2 = dimension_match.groups()
            
            # Initialize specs
            spec1 = spec2 = spec3 = spec4 = ''
            unit = file_info.get('unit', '件')
            
            p_type = file_info.get('product_type', '')
            
            # Extract dimensions for potential use
            dims = re.findall(r'(\d+)', spec_str)
            
            if p_type == '方矩管':
                # 规格1: 壁厚, 规格2: 长度, 规格3: 支重, 规格4: 支/件, 单位: 件
                spec1 = thickness
                spec2 = file_info.get('length', '')
                unit = '件'
                
            elif p_type == '板材':
                # 规格1: 厚度, 规格2: 宽度, 规格3: 长度, 规格4: kg/块, 单位: 块
                spec1 = thickness
                if len(dims) >= 2:
                    # Assume Width * Length, sort so smaller is width
                    try:
                        d1, d2 = int(dims[0]), int(dims[1])
                        spec2 = str(min(d1, d2)) # 宽度
                        spec3 = str(max(d1, d2)) # 长度
                    except:
                        spec2 = dims[0]
                        spec3 = dims[1]
                elif len(dims) == 1:
                    spec2 = dims[0] # 宽度
                    spec3 = file_info.get('length', '')
                else:
                    spec3 = file_info.get('length', '')
                unit = '块'
                
            elif p_type == '型材':
                # 规格1: 支重, 规格2: 长度, 规格3: 负差, 规格4: 支/件, 单位: 件
                spec2 = file_info.get('length', '')
                unit = '件'
                
            elif p_type == '管材':
                # 规格1: 壁厚, 规格2: 长度, 规格3: 支重, 规格4: 支/件, 单位: 件
                spec1 = thickness
                spec2 = file_info.get('length', '')
                spec4 = item.get('支数', '')
                unit = '件'
                
            elif p_type == '矿用品':
                # 规格1: 米重, 规格2: 长度, 规格3: 支/件, 规格4: Empty, 单位: 件
                spec2 = file_info.get('length', '')
                unit = '件'
                
            elif p_type == '棒材':
                # 规格1: 长度, 规格2: 米重, 规格3: 支/件, 规格4: Empty, 单位: 件
                spec1 = file_info.get('length', '')
                unit = '件'
                
            elif p_type == '彩涂卷':
                # 规格1: 厚度, 规格2: 宽度, 规格3: 长度, 规格4: kg/块
                spec1 = thickness
                if len(dims) >= 1:
                    spec2 = dims[0] # 宽度
                spec3 = file_info.get('length', '')
                unit = '块'
                
            else:
                # Default / 不锈钢 / Others
                spec1 = thickness
                spec2 = spec_str
            
            # 处理管材型号：只保留xx寸/xx分
            model_val = spec_str
            # 判定是否为圆形管材（排除方矩管）
            is_round_pipe = p_type == '管材' or (
                '管' in full_product_name and 
                p_type != '方矩管' and 
                '方' not in full_product_name and 
                '矩' not in full_product_name
            )
            
            if is_round_pipe and '*' in spec_str:
                 parts = spec_str.split('*')
                 # 对于圆管，格式通常为 口径*壁厚
                 # 用户要求保留xx寸/xx分，即保留口径部分
                 model_val = parts[0].strip()

            # 构建完整的模板记录
            record = {
                '类型': file_info['product_type'] or '',
                '品名': full_product_name,
                '型号': model_val,  # 型号使用处理后的值
                '规格1': spec1,
                '规格2': spec2,
                '规格3': spec3,
                '规格4': spec4,
                '规格5': '',
                '单位': unit,
                '材质': file_info['material'] or '',
                '执行标准': file_info['standard'] or '',
                '品牌/厂家': file_info['brand'] or '',
                '提货地/省': file_info['location_province'] or '',
                '提货地/市': file_info['location_city'] or '',
                '提货地/区': file_info['location_area'] or '',
                '默认价格/元/吨': price,
                '二等价格/元/吨': '',
                '三等价格/元/吨': '',
                '四等价格/元/吨': '',
                '五等价格/元/吨': '',
                '过磅/理计': file_info['price_type'] or '',
                '备注': '; '.join(file_info['notes']) if file_info['notes'] else f"规格: {model_val}",
                '库存': '',
                '供应商/联系方式': file_info['contact'] or '',
                '供货价/元': price,
                '差价/元': '',
                '是否显示': ''
            }
            
            template_records.append(record)
        
        # 创建DataFrame
        if template_records:
            template_df = pd.DataFrame(template_records)
        else:
            template_df = pd.DataFrame()
        
        return template_df
    
    def _get_spec1_value(self, spec1_str: str) -> float:
        """Extract numeric value from spec1 for sorting"""
        if not spec1_str:
            return 0.0
        try:
            # Handle ranges like "2.0-2.5", take the first one
            # Also handle "3.0" or 3.0
            s = str(spec1_str).strip()
            first_part = re.split(r'[-－]', s)[0].strip()
            return float(first_part)
        except:
            return 0.0

    def process_file(self, source_file_content, source_filename, manufacturer=None) -> pd.DataFrame:
        """处理单个文件的主函数 - 完全动态识别"""
        
        try:
            # 读取源数据
            source_df = pd.read_excel(BytesIO(source_file_content), header=None)
        except Exception as e:
            st.error(f"读取源文件失败: {str(e)}")
            return pd.DataFrame()
        
        # 第一步：从整个文件中提取所有相关信息
        file_info = self.extract_all_info_from_file(source_df, source_filename)
        
        # 如果指定了厂家，强制覆盖
        if manufacturer and manufacturer != "自动识别":
            file_info['brand'] = manufacturer
        
        # 第二步：提取价格数据
        price_data, column_headers = self.extract_price_data(source_df)
        
        if not price_data:
            st.warning("未提取到价格数据")
            return pd.DataFrame()
        
        # 第三步：分析规格格式
        specs_analysis = self.analyze_spec_format(price_data)
        
        # 第四步：创建模板数据
        template_df = self.create_template_dataframe(
            price_data, file_info, specs_analysis
        )
        
        # 第五步：排序
        if not template_df.empty and '型号' in template_df.columns:
            # 1. Generate Product Name Rank (Appearance Order)
            if '品名' in template_df.columns:
                product_ranks = {}
                next_p_rank = 0
                p_rank_list = []
                for p_name in template_df['品名']:
                    # Ensure we use a string key and handle NaN
                    p_name_key = str(p_name).strip() if pd.notna(p_name) else ""
                    if p_name_key not in product_ranks:
                        product_ranks[p_name_key] = next_p_rank
                        next_p_rank += 1
                    p_rank_list.append(product_ranks[p_name_key])
                template_df['p_rank'] = p_rank_list
            else:
                template_df['p_rank'] = 0

            # 2. Generate Model Rank (Appearance Order)
            model_ranks = {}
            next_m_rank = 0
            m_rank_list = []
            for model in template_df['型号']:
                # Ensure we use a string key and handle NaN
                model_key = str(model).strip() if pd.notna(model) else ""
                if model_key not in model_ranks:
                    model_ranks[model_key] = next_m_rank
                    next_m_rank += 1
                m_rank_list.append(model_ranks[model_key])
            template_df['m_rank'] = m_rank_list
            
            # 3. Generate Spec1 Value
            template_df['s1_val'] = template_df['规格1'].apply(self._get_spec1_value)
            
            # Sort
            # Sort by Product Rank (group products), then Model Rank (original order), then Spec1 (thickness)
            template_df.sort_values(by=['p_rank', 'm_rank', 's1_val'], inplace=True)
            
            # Drop helper columns
            template_df.drop(columns=['p_rank', 'm_rank', 's1_val'], inplace=True)
            
            # Debug info
            if st.session_state.get('debug_mode', False):
                st.write("排序完成。前5行数据:")
                st.write(template_df[['品名', '型号', '规格1']].head())
        
        # 记录识别到的信息（用于调试）
        if st.session_state.get('debug_mode', False):
            st.write("识别到的文件信息:", file_info)
            st.write("规格分析:", specs_analysis)
            st.write(f"提取了 {len(price_data)} 条价格记录")
        
        return template_df, file_info
