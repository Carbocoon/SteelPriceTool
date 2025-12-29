import streamlit as st
import pandas as pd
from io import BytesIO
from data_processor import ProductDataProcessor, BatchProcessor
from toolbox_ui import render_toolbox

def render_extraction_tool():
    st.title("🤖 产品数据智能提取工具")
    
    # 初始化处理器
    if 'processor' not in st.session_state:
        st.session_state.processor = ProductDataProcessor()
    if 'results' not in st.session_state:
        st.session_state.results = {}
    if 'file_infos' not in st.session_state:
        st.session_state.file_infos = {}
    if 'step' not in st.session_state:
        st.session_state.step = 1
    
    # 侧边栏配置
    with st.sidebar:
        st.header("🛠️ 提取设置")
        
        # 厂家选择
        manufacturer = st.selectbox(
            "🏭 选择厂家",
            ["请选择厂家", "正大制管", "亨旺", "屹恒", "其他厂家(待添加)"],
            help="必须选择一个厂家以进行准确匹配"
        )
        
        # 重置按钮
        if st.button("🔄 重置所有数据", use_container_width=True):
            st.session_state.results = {}
            st.session_state.file_infos = {}
            st.session_state.step = 1
            st.rerun()
            
        st.markdown("---")
        
        # 公告栏
        with st.expander("📢 公告", expanded=True):
            st.markdown("""
            **v1.4更新(2025-12-29)**
            - 增加“屹恒”板材厂家匹配
            - 优化多栏表格识别逻辑
            
            **v1.3更新(2025-12-26)**
            - 增加“亨旺物流”厂家匹配
            - 增加强制型选择厂家功能
            - 修复已知问题
            """)

        # 使用说明
        with st.expander("📖 简易指南", expanded=True):
            st.markdown("""
            1. **上传**: 拖拽上传Excel价格表
            2. **预览**: 检查数据，可批量填充空缺规格
            3. **下载**: 导出标准格式Excel/CSV
            """)
    
    # 主界面 - 分步向导布局
    
    # 步骤指示器
    steps = ["1. 上传文件", "2. 结果预览", "3. 下载结果"]
    current_step_idx = st.session_state.step - 1
    
    # 简单的进度条显示
    progress_cols = st.columns(3)
    for i, step_name in enumerate(steps):
        if i == current_step_idx:
            progress_cols[i].markdown(f"### 🔵 {step_name}")
        elif i < current_step_idx:
            progress_cols[i].markdown(f"### ✅ {step_name}")
        else:
            progress_cols[i].markdown(f"### ⚪ {step_name}")
    
    st.markdown("---")

    # 步骤 1: 上传文件
    if st.session_state.step == 1:
        st.header("📤 上传文件")
        
        # 批量上传文件
        uploaded_files = st.file_uploader(
            "选择供应商价格表文件",
            type=['xls', 'xlsx'],
            accept_multiple_files=True,
            help="支持多个Excel文件同时上传，系统将自动识别内容"
        )
        
        if uploaded_files:
            if len(uploaded_files) > 5:
                st.error(f"⚠️ 一次最多只能上传 5 个文件，您上传了 {len(uploaded_files)} 个。请重新选择。")
            else:
                st.success(f"已选择 {len(uploaded_files)} 个文件")
                
                # 显示文件列表
                with st.expander("📁 查看已选文件列表"):
                    for file in uploaded_files:
                        st.write(f"**{file.name}** ({file.size/1024:.1f} KB)")
                
                # 处理按钮
                if st.button("🚀 开始智能提取", type="primary", use_container_width=True):
                    if manufacturer == "请选择厂家":
                        st.error("⚠️ 请先在左侧侧边栏选择一个厂家！")
                    else:
                        # 使用 status 容器显示进度
                        with st.status("正在处理文件...", expanded=True) as status:
                            # 创建批处理器
                            batch_processor = BatchProcessor()
                            
                            st.write("正在初始化处理器...")
                            # 处理所有文件
                            results, file_infos = batch_processor.process_multiple_files(
                                uploaded_files,
                                manufacturer=manufacturer
                            )
                            
                            # 保存结果到session state
                            st.session_state.results = results
                            st.session_state.file_infos = file_infos
                            
                            if results:
                                status.update(label="✅ 处理完成！", state="complete", expanded=False)
                                st.success(f"成功处理 {len(results)} 个文件")
                                st.session_state.step = 2
                                st.rerun()
                            else:
                                status.update(label="❌ 处理失败", state="error")

    # 步骤 2: 结果预览
    elif st.session_state.step == 2:
        st.header("👀 结果预览")
        
        if st.session_state.results:
            # 选择要预览的文件
            file_options = list(st.session_state.results.keys())
            selected_file = st.selectbox("选择要预览的文件", file_options)
            
            if selected_file:
                df = st.session_state.results[selected_file]
                file_info = st.session_state.file_infos.get(selected_file, {})
                
                # 显示文件信息摘要
                with st.expander("📄 文件识别摘要", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**产品类型:**", file_info.get('product_type', '未识别'))
                        st.write("**品名:**", file_info.get('product_name', '未识别'))
                        st.write("**品牌/厂家:**", file_info.get('brand', '未识别'))
                        st.write("**单位:**", file_info.get('unit', '未识别'))
                    with col2:
                        st.write("**长度:**", file_info.get('length', '未识别'))
                        st.write("**计价方式:**", file_info.get('price_type', '未识别'))
                        st.write("**材质:**", file_info.get('material', '未识别'))
                        st.write("**执行标准:**", file_info.get('standard', '未识别'))
                
                # 规格映射说明与批量填充
                p_type = file_info.get('product_type', '')
                mapping_info = {
                    '方矩管': {'规格1': '壁厚', '规格2': '长度', '规格3': '支重', '规格4': '支/件', '规格5': '预留'},
                    '板材': {'规格1': '厚度', '规格2': '宽度', '规格3': '长度', '规格4': 'kg/块', '规格5': '预留'},
                    '型材': {'规格1': '支重', '规格2': '长度', '规格3': '负差', '规格4': '支/件', '规格5': '预留'},
                    '管材': {'规格1': '壁厚', '规格2': '长度', '规格3': '支重', '规格4': '支/件', '规格5': '预留'},
                    '矿用品': {'规格1': '米重', '规格2': '长度', '规格3': '支/件', '规格4': '预留', '规格5': '预留'},
                    '棒材': {'规格1': '长度', '规格2': '米重', '规格3': '支/件', '规格4': '预留', '规格5': '预留'},
                    '彩涂卷': {'规格1': '厚度', '规格2': '宽度', '规格3': '长度', '规格4': 'kg/块', '规格5': '预留'}
                }
                
                current_mapping = mapping_info.get(p_type, {})
                
                if current_mapping:
                    with st.expander("📝 规格映射与批量填充", expanded=True):
                        st.info(f"当前产品类型【{p_type}】的规格映射关系如下：")
                        
                        # 展示映射关系并提供输入框
                        cols = st.columns(5)
                        fill_values = {}
                        
                        for i in range(1, 6):
                            spec_key = f'规格{i}'
                            col_name = current_mapping.get(spec_key, '未知')
                            
                            with cols[i-1]:
                                st.markdown(f"**{spec_key} ({col_name})**")
                                # 检查当前列是否为空（或大部分为空）
                                is_empty = False
                                if spec_key in df.columns:
                                    # 简单的检查：如果空值比例超过80%，则认为是空列
                                    empty_ratio = df[spec_key].replace('', pd.NA).isna().mean()
                                    if empty_ratio > 0.8:
                                        is_empty = True
                                
                                if is_empty:
                                    val = st.text_input(f"填充{col_name}", key=f"fill_{selected_file}_{spec_key}", placeholder="输入值以填充")
                                    if val:
                                        fill_values[spec_key] = val
                                else:
                                    st.caption("已识别数据")
                        
                        # 应用填充
                        if fill_values:
                            if st.button("应用批量填充"):
                                for key, val in fill_values.items():
                                    df[key] = df[key].replace('', val).fillna(val)
                                    # 如果全是空字符串，replace可能不起作用，强制赋值
                                    if df[key].eq('').all():
                                        df[key] = val
                                st.session_state.results[selected_file] = df
                                st.success("填充完成！")
                                st.rerun()

                # 显示数据预览 (可编辑)
                st.info("💡 提示：您可以直接点击表格中的单元格进行修改，修改后的内容将包含在下载文件中。")
                edited_df = st.data_editor(
                    df, 
                    use_container_width=True, 
                    hide_index=True,
                    key=f"editor_{selected_file}"
                )
                
                # 实时更新Session State
                if not edited_df.equals(df):
                    st.session_state.results[selected_file] = edited_df
                
                # 显示数据统计
                with st.expander("📊 数据统计"):
                    st.write(f"**数据形状:** {edited_df.shape}")
                    st.write(f"**列数:** {len(edited_df.columns)}")
                    st.write(f"**行数:** {len(edited_df)}")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("⬅️ 返回上传", use_container_width=True):
                    st.session_state.step = 1
                    st.session_state.results = {}
                    st.rerun()
            with col2:
                if st.button("✅ 确认无误，前往下载", type="primary", use_container_width=True):
                    st.session_state.step = 3
                    st.rerun()
        else:
            st.warning("暂无数据，请返回重新上传")
            if st.button("返回"):
                st.session_state.step = 1
                st.rerun()

    # 步骤 3: 下载结果
    elif st.session_state.step == 3:
        st.header("📥 下载结果")
        
        # 下载选项
        col1, col2 = st.columns(2)
        
        with col1:
            download_format = st.radio(
                "选择下载格式",
                ["Excel", "CSV"],
                horizontal=True
            )
        
        with col2:
            if len(st.session_state.results) > 1:
                output_option = st.radio(
                    "输出方式",
                    ["合并所有文件", "分开下载文件"]
                )
            else:
                output_option = "单个文件"
        
        # 高级选项
        with st.expander("⚙️ 高级下载选项"):
            include_file_info = st.checkbox("包含文件识别信息", value=True)
            format_prices = st.checkbox("格式化价格列", value=True)
        
        # 自定义文件名
        output_filename = st.text_input("输出文件名 (无需后缀)", value="智能提取结果")
        
        st.markdown("### 点击下方按钮下载")
        
        # 准备数据
        if output_option == "合并所有文件":
            # 合并所有DataFrame
            all_data_frames = []
            for filename, df in st.session_state.results.items():
                df_copy = df.copy()
                df_copy['来源文件'] = filename
                if include_file_info and filename in st.session_state.file_infos:
                    file_info = st.session_state.file_infos[filename]
                    for key, value in file_info.items():
                        if key not in df_copy.columns:
                            # 如果是列表（如notes），转换为字符串，避免长度不匹配错误
                            if isinstance(value, list):
                                value = "; ".join(map(str, value))
                            df_copy[key] = value
                all_data_frames.append(df_copy)
            
            if all_data_frames:
                merged_df = pd.concat(all_data_frames, ignore_index=True)
                
                if download_format == "Excel":
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        merged_df.to_excel(writer, index=False, sheet_name='合并数据')
                        if include_file_info:
                            pd.DataFrame.from_dict(st.session_state.file_infos, orient='index').to_excel(writer, sheet_name='文件信息')
                    output.seek(0)
                    data = output
                    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ext = "xlsx"
                else:
                    data = merged_df.to_csv(index=False).encode('utf-8-sig')
                    mime = "text/csv"
                    ext = "csv"
                    
                st.download_button(
                    label=f"📥 下载合并文件 (. {ext})",
                    data=data,
                    file_name=f"{output_filename}.{ext}",
                    mime=mime,
                    type="primary",
                    use_container_width=True
                )
        else:
            # 分开下载
            st.info("请点击下方按钮分别下载文件：")
            cols = st.columns(2)
            for idx, (filename, df) in enumerate(st.session_state.results.items()):
                base_name = filename.split('.')[0]
                col = cols[idx % 2]
                
                if download_format == "Excel":
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='数据')
                        if include_file_info and filename in st.session_state.file_infos:
                            pd.DataFrame([st.session_state.file_infos[filename]]).to_excel(writer, sheet_name='文件信息', index=False)
                    output.seek(0)
                    data = output
                    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ext = "xlsx"
                else:
                    data = df.to_csv(index=False).encode('utf-8-sig')
                    mime = "text/csv"
                    ext = "csv"
                
                col.download_button(
                    label=f"📥 {base_name}",
                    data=data,
                    file_name=f"{output_filename}_{base_name}.{ext}",
                    mime=mime,
                    key=f"dl_{idx}"
                )
        
        st.markdown("---")
        if st.button("🔄 开始新任务", use_container_width=True):
            st.session_state.results = {}
            st.session_state.file_infos = {}
            st.session_state.step = 1
            st.rerun()

def main():
    st.set_page_config(
        page_title="产品数据智能提取工具",
        page_icon="🤖",
        layout="wide"
    )
    
    # 侧边栏导航
    with st.sidebar:
        st.title("🤖 菜单")
        app_mode = st.radio("选择功能", ["智能提取", "通用工具箱"])
        st.markdown("---")

    if app_mode == "通用工具箱":
        render_toolbox()
    else:
        render_extraction_tool()

if __name__ == "__main__":
    main()