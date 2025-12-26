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

            # Zhengda format: Spec(0), Price(1), Count(2) - repeated
            for start_col in range(0, len(row) - 2, 3):
                spec_col, price_col, count_col = start_col, start_col + 1, start_col + 2
                if price_col >= len(row): continue

                spec_val = str(row.iloc[spec_col]).strip() if spec_col < len(row) and pd.notna(row.iloc[spec_col]) else ""
                price = row.iloc[price_col] if price_col < len(row) and pd.notna(row.iloc[price_col]) else None
                
                # Extract count
                count_val = row.iloc[count_col] if count_col < len(row) and pd.notna(row.iloc[count_col]) else None
                if count_val is not None and str(count_val).strip():
                     last_counts[start_col] = count_val
                
                current_count = last_counts.get(start_col, '')

                if not spec_val or not price: continue

                # Spec inheritance logic
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

            # 4-col format: Square(0), Rect(1), Thickness(2), Price(3)
            for start_col in range(0, len(row) - 3, 4):
                sq_col, rect_col, thick_col, price_col = start_col, start_col+1, start_col+2, start_col+3
                if price_col >= len(row): continue

                # Square specs
                sq_specs = parse_spec_cell(row.iloc[sq_col]) if sq_col < len(row) else []
                if sq_specs: last_specs[sq_col] = sq_specs
                sq_specs_to_use = sq_specs if sq_specs else last_specs.get(sq_col, [])

                # Rect specs
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
        # Try to find standard header
        for i in range(min(20, len(df))):
            row_str = df.iloc[i].astype(str).str.cat(sep=' ')
            if '规格' in row_str and '厚度' in row_str and '价格' in row_str:
                return True, i, i + 1
        
        # Fallback: just look for '规格'
        for i in range(min(10, len(df))):
            row_str = df.iloc[i].astype(str).str.cat(sep=' ')
            if '规格' in row_str:
                return True, i, i + 1
        
        # Last resort fallback
        return True, 6, 7

    def extract(self, df: pd.DataFrame, header_row: int, data_start_row: int) -> Tuple[List[Dict], List[str]]:
        records = []
        column_headers = self.get_column_headers(df, header_row)
        last_specs = {}

        for row_idx in range(data_start_row, len(df)):
            row = df.iloc[row_idx]
            if row.dropna().empty: continue

            # 3-col format: Spec(0), Thickness(1), Price(2)
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
            # Check for key headers
            if '壁厚' in row_str and '过磅' in row_str and '检尺' in row_str:
                return True, i, i + 1
        return False, -1, -1

    def extract(self, df: pd.DataFrame, header_row: int, data_start_row: int) -> Tuple[List[Dict], List[str]]:
        records = []
        column_headers = self.get_column_headers(df, header_row)
        
        # We need to get the brand from the row above the header row.
        brand_row_idx = header_row - 1
        
        last_specs = {} # Map col_idx -> {'spec': str, 'weight': float}
        
        # Iterate columns in steps of 4 (Spec, Thickness, Weighing, Theoretical)
        for start_col in range(0, len(df.columns) - 3, 4):
            # Check if this block looks valid (has "壁厚" in header row)
            if start_col + 1 >= len(df.columns): break
            
            header_val = str(df.iloc[header_row, start_col+1]).strip()
            if '壁厚' not in header_val:
                continue
                
            # Get Brand from the row above
            brand_name = ""
            if brand_row_idx >= 0:
                val = str(df.iloc[brand_row_idx, start_col]).strip()
                if val and val != 'nan':
                    brand_name = val
            
            # Clean brand name and determine product name
            final_brand = ""
            product_name = ""
            
            if '正大' in brand_name: 
                final_brand = '正大'
                if '镀锌' in brand_name: product_name = '镀锌管'
            elif '友发' in brand_name: 
                final_brand = '友发'
                if '镀锌' in brand_name: product_name = '镀锌管'
            elif '焊管' in brand_name: 
                final_brand = '亨旺' # Default for generic pipe
                product_name = '焊管'
            elif brand_name and '管' in brand_name: 
                final_brand = brand_name # Fallback
                if '镀锌' in brand_name: product_name = '镀锌管'
                elif '焊' in brand_name: product_name = '焊管'
            
            spec_col = start_col
            thick_col = start_col + 1
            price_col = start_col + 2 # 过磅
            theo_price_col = start_col + 3 # 检尺/理计
            
            # Iterate rows
            for row_idx in range(data_start_row, len(df)):
                row = df.iloc[row_idx]
                
                # Extract Spec
                raw_spec = row.iloc[spec_col]
                if pd.notna(raw_spec) and str(raw_spec).strip() and str(raw_spec).strip() != 'nan':
                    spec_str = str(raw_spec).strip()
                    
                    # Extract "xx分" or "xx寸"
                    import re
                    model_match = re.search(r'(\d+\.?\d*[寸分])', spec_str)
                    clean_spec = model_match.group(1) if model_match else None
                    
                    # Extract Weight (look for standalone number)
                    weight_val = None
                    # Split by whitespace or newline to find numbers
                    parts = re.split(r'[\s\n]+', spec_str)
                    for part in parts:
                        try:
                            # Check if it is a number
                            val = float(part)
                            # Heuristic: Weight is usually a small float (e.g. 7.56), not 2025 (year) or 15 (DN15)
                            # But DN15 is 15. 
                            # If we have "DN15", part is "DN15" (not float) or "DN" and "15".
                            # If "DN15" is one token, float("DN15") fails.
                            # If "DN 15", float("15") works.
                            # However, the image shows "DN15" on one line, "4分" on next, "7.56" on next.
                            # If they are in one cell, they are separated by newline.
                            # "DN15" -> fail float.
                            # "4分" -> fail float.
                            # "7.56" -> success float.
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
                
                # Extract Thickness and Price
                thickness = row.iloc[thick_col]
                price = row.iloc[price_col]
                theo_price = row.iloc[theo_price_col] if theo_price_col < len(row) else None
                
                if pd.isna(thickness) or (pd.isna(price) and pd.isna(theo_price)):
                    continue
                    
                # Validate thickness (should be number)
                try:
                    float(thickness)
                except:
                    continue
                    
                # Validate prices
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
                    '价格': p_val, # 过磅价格
                    '理计价格': t_val, # 理计价格
                    '品牌/厂家': final_brand,
                    '品名': product_name,
                    '型号': current_spec,
                    '支重': current_weight
                })

        return records, column_headers
