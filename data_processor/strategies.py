import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Any
from .utils import format_thickness, parse_spec_cell

class ExtractionStrategy:
    """Base class for extraction strategies"""
    def match(self, df: pd.DataFrame) -> Tuple[bool, int, int]:
        """
        Check if strategy matches the dataframe structure.
        Returns: (is_match, header_row_index, data_start_row_index)
        """
        return False, -1, -1

    def extract(self, df: pd.DataFrame, header_row: int, data_start_row: int) -> Tuple[List[Dict], List[str]]:
        """
        Extract data from the dataframe.
        Returns: (records, column_headers)
        """
        return [], []

    def get_column_headers(self, df: pd.DataFrame, header_row: int) -> List[str]:
        """Helper to extract column headers"""
        headers = []
        for col in range(len(df.columns)):
            cell_val = str(df.iloc[header_row, col]) if col < len(df.iloc[header_row]) else ''
            if cell_val.strip():
                headers.append(cell_val.strip())
        return headers

class ZhengdaGalvanizedStrategy(ExtractionStrategy):
    """Strategy for Zhengda Galvanized Pipe format (Spec | Price | Count)"""
    
    def match(self, df: pd.DataFrame) -> Tuple[bool, int, int]:
        for i in range(min(20, len(df))):
            row_str = df.iloc[i].astype(str).str.cat(sep=' ')
            if '正大热镀' in row_str and '规格' in row_str:
                return True, i, i + 1
        return False, -1, -1

    def extract(self, df: pd.DataFrame, header_row: int, data_start_row: int) -> Tuple[List[Dict], List[str]]:
        records = []
        column_headers = self.get_column_headers(df, header_row)
        last_specs = {}
        last_counts = {}

        for row_idx in range(data_start_row, len(df)):
            row = df.iloc[row_idx]
            if row.dropna().empty: continue

            for start_col in range(0, len(row) - 2, 3):
                spec_col, price_col, count_col = start_col, start_col + 1, start_col + 2
                if price_col >= len(row): continue

                spec_val = str(row.iloc[spec_col]).strip() if spec_col < len(row) and pd.notna(row.iloc[spec_col]) else ""
                price = row.iloc[price_col] if price_col < len(row) and pd.notna(row.iloc[price_col]) else None
                
                count_val = row.iloc[count_col] if count_col < len(row) and pd.notna(row.iloc[count_col]) else None
                if count_val is not None and str(count_val).strip():
                     last_counts[start_col] = count_val
                
                current_count = last_counts.get(start_col, '')

                if not spec_val or not price: continue

                if '*' in spec_val:
                    parts = spec_val.split('*')
                    if len(parts) >= 2:
                        current_size = parts[0].strip()
                        thickness = parts[1].strip()
                        last_specs[spec_col] = current_size
                        full_spec = spec_val
                    else:
                        continue
                elif last_specs.get(spec_col):
                    thickness = spec_val
                    current_size = last_specs[spec_col]
                    full_spec = f"{current_size}*{thickness}"
                else:
                    continue

                thickness_range = format_thickness(str(thickness))
                records.append({
                    '规格': full_spec,
                    '厚度': thickness_range,
                    '价格': float(price) if isinstance(price, (int, float, np.integer, np.floating)) else 0,
                    '支数': current_count
                })
        
        return records, column_headers

class FourColumnStrategy(ExtractionStrategy):
    """Strategy for 4-column format (Square | Rect | Thickness | Price)"""
    
    def match(self, df: pd.DataFrame) -> Tuple[bool, int, int]:
        for i in range(min(20, len(df))):
            row_str = df.iloc[i].astype(str).str.cat(sep=' ')
            if '方管' in row_str and '矩管' in row_str and '厚度' in row_str and '价格' in row_str:
                return True, i, i + 1
        return False, -1, -1

    def extract(self, df: pd.DataFrame, header_row: int, data_start_row: int) -> Tuple[List[Dict], List[str]]:
        records = []
        column_headers = self.get_column_headers(df, header_row)
        last_specs = {}

        for row_idx in range(data_start_row, len(df)):
            row = df.iloc[row_idx]
            if row.dropna().empty: continue

            for start_col in range(0, len(row) - 3, 4):
                sq_col, rect_col, thick_col, price_col = start_col, start_col+1, start_col+2, start_col+3
                if price_col >= len(row): continue

                sq_specs = parse_spec_cell(row.iloc[sq_col]) if sq_col < len(row) else []
                if sq_specs: last_specs[sq_col] = sq_specs
                sq_specs_to_use = sq_specs if sq_specs else last_specs.get(sq_col, [])

                rect_specs = parse_spec_cell(row.iloc[rect_col]) if rect_col < len(row) else []
                if rect_specs: last_specs[rect_col] = rect_specs
                rect_specs_to_use = rect_specs if rect_specs else last_specs.get(rect_col, [])

                specs_to_use = sq_specs_to_use + rect_specs_to_use
                
                thickness = row.iloc[thick_col] if thick_col < len(row) and pd.notna(row.iloc[thick_col]) else None
                price = row.iloc[price_col] if price_col < len(row) and pd.notna(row.iloc[price_col]) else None

                if specs_to_use and pd.notna(thickness) and pd.notna(price):
                    for spec in specs_to_use:
                        thickness_range = format_thickness(str(thickness))
                        records.append({
                            '规格': spec,
                            '厚度': thickness_range,
                            '价格': float(price) if isinstance(price, (int, float, np.integer, np.floating)) else 0
                        })
        
        return records, column_headers

class ThreeColumnStrategy(ExtractionStrategy):
    """Strategy for standard 3-column format (Spec | Thickness | Price)"""
    
    def match(self, df: pd.DataFrame) -> Tuple[bool, int, int]:
        for i in range(min(20, len(df))):
            row_str = df.iloc[i].astype(str).str.cat(sep=' ')
            if '规格' in row_str and '厚度' in row_str and '价格' in row_str:
                return True, i, i + 1
        
        for i in range(min(10, len(df))):
            row_str = df.iloc[i].astype(str).str.cat(sep=' ')
            if '规格' in row_str:
                return True, i, i + 1
        
        return True, 6, 7

    def extract(self, df: pd.DataFrame, header_row: int, data_start_row: int) -> Tuple[List[Dict], List[str]]:
        records = []
        column_headers = self.get_column_headers(df, header_row)
        last_specs = {}

        for row_idx in range(data_start_row, len(df)):
            row = df.iloc[row_idx]
            if row.dropna().empty: continue

            for start_col in range(0, len(row) - 2, 3):
                spec_col, thick_col, price_col = start_col, start_col+1, start_col+2
                if price_col >= len(row): continue

                current_specs = parse_spec_cell(row.iloc[spec_col])
                if current_specs: last_specs[spec_col] = current_specs
                specs_to_use = current_specs if current_specs else last_specs.get(spec_col, [])

                thickness = row.iloc[thick_col] if thick_col < len(row) and pd.notna(row.iloc[thick_col]) else None
                price = row.iloc[price_col] if price_col < len(row) and pd.notna(row.iloc[price_col]) else None

                if specs_to_use and pd.notna(thickness) and pd.notna(price):
                    for spec in specs_to_use:
                        thickness_range = format_thickness(str(thickness))
                        records.append({
                            '规格': spec,
                            '厚度': thickness_range,
                            '价格': float(price) if isinstance(price, (int, float, np.integer, np.floating)) else 0
                        })
        
        return records, column_headers

class HengwangPipeStrategy(ExtractionStrategy):
    """Strategy for Hengwang Pipe format (Spec | Thickness | Weighing Price | Theoretical Price)"""
    
    def match(self, df: pd.DataFrame) -> Tuple[bool, int, int]:
        for i in range(min(20, len(df))):
            row_str = df.iloc[i].astype(str).str.cat(sep=' ')
            if '壁厚' in row_str and '过磅' in row_str and '检尺' in row_str:
                return True, i, i + 1
        return False, -1, -1

    def extract(self, df: pd.DataFrame, header_row: int, data_start_row: int) -> Tuple[List[Dict], List[str]]:
        records = []
        column_headers = self.get_column_headers(df, header_row)
        
        brand_row_idx = header_row - 1
        
        
        for start_col in range(0, len(df.columns) - 3, 4):
            if start_col + 1 >= len(df.columns): break
            
            header_val = str(df.iloc[header_row, start_col+1]).strip()
            if '壁厚' not in header_val:
                continue
                
            brand_name = ""
            if brand_row_idx >= 0:
                val = str(df.iloc[brand_row_idx, start_col]).strip()
                if val and val != 'nan':
                    brand_name = val
            
            final_brand = ""
            product_name = ""
            
            if '正大' in brand_name: 
                final_brand = '正大'
                if '镀锌' in brand_name: product_name = '镀锌管'
            elif '友发' in brand_name: 
                final_brand = '友发'
                if '镀锌' in brand_name: product_name = '镀锌管'
            elif '焊管' in brand_name: 
                product_name = '焊管'
            elif brand_name and '管' in brand_name: 
                if '镀锌' in brand_name: product_name = '镀锌管'
                elif '焊' in brand_name: product_name = '焊管'
            
            spec_col = start_col
            thick_col = start_col + 1
            
            for row_idx in range(data_start_row, len(df)):
                row = df.iloc[row_idx]
                
                raw_spec = row.iloc[spec_col]
                if pd.notna(raw_spec) and str(raw_spec).strip() and str(raw_spec).strip() != 'nan':
                    spec_str = str(raw_spec).strip()
                    
                    import re
                    model_match = re.search(r'(\d+\.?\d*[寸分])', spec_str)
                    clean_spec = model_match.group(1) if model_match else None
                    
                    weight_val = None
                    parts = re.split(r'[\s\n]+', spec_str)
                    for part in parts:
                        try:
                            val = float(part)
                            weight_val = val
                        except ValueError:
                            pass
                    
                    if clean_spec:
                        last_specs[start_col] = {'spec': clean_spec, 'weight': weight_val}
                
                current_data = last_specs.get(start_col)
                if not current_data:
                    continue
                
                current_spec = current_data['spec']
                current_weight = current_data['weight']
                
                thickness = row.iloc[thick_col]
                price = row.iloc[price_col]
                theo_price = row.iloc[theo_price_col] if theo_price_col < len(row) else None
                
                if pd.isna(thickness) or (pd.isna(price) and pd.isna(theo_price)):
                    continue
                    
                try:
                    float(thickness)
                except:
                    continue
                    
                p_val = 0
                if pd.notna(price):
                    try:
                        p_val = float(price)
                    except:
                        pass
                
                t_val = 0
                if pd.notna(theo_price):
                    try:
                        t_val = float(theo_price)
                    except:
                        pass
                
                if p_val == 0 and t_val == 0:
                    continue
                
                records.append({
                    '规格': current_spec,
                    '厚度': format_thickness(str(thickness)),
                    '品牌/厂家': final_brand,
                    '品名': product_name,
                    '型号': current_spec,
                    '支重': current_weight
                })

        return records, column_headers

class YihengPlateStrategy(ExtractionStrategy):
    """Strategy for Yiheng Plate format (Merged Mat | Mat | Thickness | Width | Length | Origin | Location | Price | ...)"""
    
    def match(self, df: pd.DataFrame) -> Tuple[bool, int, int]:
        for i in range(min(20, len(df))):
            row_str = df.iloc[i].astype(str).str.cat(sep=' ')
            if '材质' in row_str and '厚度' in row_str and '宽度' in row_str and '长度' in row_str and '产地' in row_str:
                return True, i, i + 1
        return False, -1, -1

    def extract(self, df: pd.DataFrame, header_row: int, data_start_row: int) -> Tuple[List[Dict], List[str]]:
        records = []
        column_headers = self.get_column_headers(df, header_row)
        
        thickness_cols = []
        for col in range(len(df.columns)):
            val = str(df.iloc[header_row, col]).strip()
            if '厚度' in val:
                thickness_cols.append(col)
        
        current_merged_materials = {col: None for col in thickness_cols}
        
        
        for row_idx in range(data_start_row, len(df)):
            row = df.iloc[row_idx]
            if row.dropna(how='all').empty: continue
            
            row_text = row.astype(str).str.cat(sep=' ')
            
            if '低温容器板' in row_text:
                current_product_name = "低温容器板"
                current_merged_materials = {col: None for col in thickness_cols}
                continue
            elif '容器板' in row_text and '低温' not in row_text:
                 pass
            
            if '电话' in row_text:
                continue

            for t_col in thickness_cols:
                
                merged_mat_col = t_col - 2
                specific_mat_col = t_col - 1
                width_col = t_col + 1
                len_col = t_col + 2
                origin_col = t_col + 3
                loc_col = t_col + 4
                price_col = t_col + 5
                unit_wt_col = t_col + 6
                
                if price_col >= len(df.columns): continue
                
                if merged_mat_col >= 0:
                    val = row.iloc[merged_mat_col]
                    if pd.notna(val) and str(val).strip() and str(val).strip() != 'nan':
                        current_merged_materials[t_col] = str(val).strip()
                
                merged_mat = current_merged_materials.get(t_col)
                
                spec_mat_val = row.iloc[specific_mat_col] if specific_mat_col >= 0 else None
                spec_mat = str(spec_mat_val).strip() if pd.notna(spec_mat_val) else ""
                
                final_mat = merged_mat if merged_mat else spec_mat
                
                thickness = row.iloc[t_col]
                width = row.iloc[width_col]
                length = row.iloc[len_col]
                origin = row.iloc[origin_col]
                location = row.iloc[loc_col]
                price = row.iloc[price_col]
                unit_wt = row.iloc[unit_wt_col] if unit_wt_col < len(df.columns) else None
                
                if pd.isna(price) or str(price).strip() == '': continue
                try:
                    p_val = float(price)
                except:
                    continue
                
                if not final_mat: continue
                
                t_str = format_thickness(str(thickness)) if pd.notna(thickness) else ""
                w_str = str(width).strip() if pd.notna(width) else ""
                l_str = str(length).strip() if pd.notna(length) else ""
                uw_str = str(unit_wt).strip() if pd.notna(unit_wt) else ""
                origin_str = str(origin).strip() if pd.notna(origin) else ""
                loc_str = str(location).strip() if pd.notna(location) else ""
                
                records.append({
                    '类型': '板材',
                    '品名': current_product_name,
                    '材质': final_mat,
                    '规格': f"{w_str}*{l_str}",
                    '厚度': t_str,
                    '价格': int(p_val),
                    '规格1': t_str,
                    '规格2': w_str,
                    '规格3': l_str,
                    '规格4': uw_str,
                    '品牌/厂家': origin_str,
                    '提货地/市': loc_str,
                    '默认价格': int(p_val),
                    '过磅价格': int(p_val),
                    '理计价格': 0
                })
                
        return records, column_headers

class FuShunDeStrategy(ExtractionStrategy):
    """Strategy for FuShunDe format (Inventory | Spec | ... | Price)"""
    
    def match(self, df: pd.DataFrame) -> Tuple[bool, int, int]:
        for i in range(min(20, len(df))):
            row_str = df.iloc[i].astype(str).str.cat(sep=' ')
            if '存货' in row_str and '规格型号' in row_str and '销售报价' in row_str:
                return True, i, i + 1
        return False, -1, -1

    def extract(self, df: pd.DataFrame, header_row: int, data_start_row: int) -> Tuple[List[Dict], List[str]]:
        records = []
        column_headers = self.get_column_headers(df, header_row)
        
        try:
            headers = df.iloc[header_row].astype(str).tolist()
            prod_col = -1
            spec_col = -1
            price_col = -1
            
            for idx, h in enumerate(headers):
                if '存货' in h: prod_col = idx
                elif '规格型号' in h: spec_col = idx
                elif '销售报价' in h: price_col = idx
            
            if prod_col == -1 or spec_col == -1 or price_col == -1:
                return [], []
        except:
            return [], []

        last_product = ""

        for row_idx in range(data_start_row, len(df)):
            row = df.iloc[row_idx]
            if row.dropna(how='all').empty: continue
            
            raw_prod = str(row.iloc[prod_col]).strip()
            if raw_prod and raw_prod != 'nan':
                last_product = raw_prod
            
            current_prod = last_product
            if not current_prod: continue
            
            brand_from_prod = ""
            clean_prod_name = current_prod
            if "宝得" in current_prod:
                brand_from_prod = "宝得"
                clean_prod_name = current_prod.replace("宝得", "").strip()
            
            raw_spec = str(row.iloc[spec_col]).strip()
            if not raw_spec or raw_spec == 'nan': continue
            
            raw_price = row.iloc[price_col]
            price_val = 0
            try:
                price_val = float(raw_price)
            except:
                continue

            if pd.isna(price_val) or (isinstance(price_val, float) and np.isnan(price_val)):
                continue
                
            spec_brand = ""
            location = ""
            clean_spec = raw_spec.replace(" ", "")
            
            if "宝得" in clean_spec:
                spec_brand = "宝得"
                clean_spec = clean_spec.replace("宝得", "")
            
            clean_spec = clean_spec.replace("散", "")
            
            import re
            chinese_chars = re.findall(r'[\u4e00-\u9fa5]+', clean_spec)
            for ch in chinese_chars:
                if "锰" in ch:
                    pass
                else:
                    location = ch
                    clean_spec = clean_spec.replace(ch, "")
            
            clean_spec = clean_spec.strip()
            
            
            final_brand = spec_brand if spec_brand else brand_from_prod
            
            p_type = ""
            if any(x in clean_prod_name for x in ['槽钢', '角钢', '工字钢', 'H型钢', '型钢']):
                p_type = '型材'
            elif any(x in clean_prod_name for x in ['板', '卷']):
                p_type = '板材'
            elif any(x in clean_prod_name for x in ['方管', '矩管']):
                p_type = '方矩管'
            elif any(x in clean_prod_name for x in ['管']):
                p_type = '管材'
            elif any(x in clean_prod_name for x in ['圆钢', '螺纹']):
                p_type = '棒材'
            
            thickness_val = ""
            if '*' in clean_spec:
                 parts = clean_spec.split('*')
                 if parts:
                    last_part = parts[-1].strip()
                    if re.match(r'^\d+(\.\d+)?$', last_part):
                        thickness_val = last_part

            records.append({
                '类型': p_type,
                '品名': clean_prod_name,
                '规格': clean_spec,
                '厚度': thickness_val,
                '价格': int(price_val),
                '品牌/厂家': final_brand,
                '提货地/市': location,
                '默认价格': int(price_val),
                '过磅价格': int(price_val),
                '理计价格': 0
            })
            
        return records, column_headers
