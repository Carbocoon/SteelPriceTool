import streamlit as st
from typing import List, Dict
from .core import ProductDataProcessor

class BatchProcessor:
    """批量处理器 - 动态识别版本"""
    
    def __init__(self):
        self.processor = ProductDataProcessor()
    
    def process_multiple_files(self, source_files: List, manufacturer=None) -> Dict:
        """处理多个文件"""
        results = {}
        file_infos = {}
        
        for source_file in source_files:
            file_name = source_file.name
            file_content = source_file.getvalue()
            
            st.write(f"处理文件: {file_name}")
            
            # 处理文件
            result_df, file_info = self.processor.process_file(
                file_content, file_name, manufacturer
            )
            
            if not result_df.empty:
                results[file_name] = result_df
                file_infos[file_name] = file_info
                st.success(f"成功处理: {file_name} - 提取了 {len(result_df)} 条记录")
                
                # 显示识别到的关键信息
                info_str = f"识别结果: {file_info.get('product_name', '未识别')} | {file_info.get('product_type', '未识别')} | {file_info.get('brand', '未识别')}"
                st.caption(info_str)
            else:
                st.error(f"处理失败: {file_name}")
        
        return results, file_infos
