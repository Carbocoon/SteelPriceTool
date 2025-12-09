import streamlit as st
import pandas as pd
from core.processor import process_files, generate_preview_dataframe
import os

# --- 页面配置 ---
st.set_page_config(
    page_title="钢材价格自动整理工具", 
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 自定义样式 ---
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        height: 3em;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 标题区域 ---
st.markdown('<div class="main-header">🏗️ 钢材价格自动整理工具</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">智能识别 · 自动计算 · 一键生成</div>', unsafe_allow_html=True)
st.markdown("---")

# --- 侧边栏：配置区域 ---
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    with st.expander("📊 计算模式 (必选)", expanded=True):
        price_mode = st.radio(
            "选择模式",
            options=["auto", "direct", "rule"],
            index=None,
            format_func=lambda x: {
                "auto": "🤖 自动计算 (智能识别基价)",
                "direct": "📄 直接读取 (已有最终价)",
                "rule": "📝 自定义规则 (高级模式)"
            }[x],
            help="自动计算：寻找基价并加上小额加价；直接读取：直接使用Excel中的价格列；自定义规则：使用下方输入的规则进行计算。"
        )

    # 动态显示配置项
    if price_mode == "auto":
        with st.expander("💰 基价策略", expanded=True):
            base_price_strategy = st.radio(
                "基价来源",
                options=["auto_identify", "fixed"],
                format_func=lambda x: "🔍 自动识别 (组内最大值)" if x == "auto_identify" else "📌 固定基价 (手动输入)",
                index=None,
                help="自动识别：程序会在每组数据中寻找一个“完整价格”作为基价；固定基价：所有数据都使用下方输入的基价。"
            )
            
            base_price_default = None
            if base_price_strategy == "fixed":
                base_price_default = st.number_input("输入固定基价 (元)", value=None, step=10, placeholder="例如: 3300")
            else:
                base_price_default = st.number_input("默认基价 (备用)", value=3300, step=10, help="当无法自动识别基价时使用的默认值")

            rule_text = st.text_area(
                "➕ 额外加价规则 (可选)",
                height=100,
                placeholder="例如：\n简装管加价10元\n打包带加价20元",
                help="在此输入需要额外叠加的加价规则。程序会先自动计算基础价格，再叠加这里的规则。"
            )

    elif price_mode == "rule":
        with st.expander("📝 规则定义", expanded=True):
            base_price_default = st.number_input("今日基价 (元)", value=3300, step=10)
            rule_text = st.text_area(
                "输入规则 (自然语言)",
                height=200,
                placeholder="例如：\n槽钢以16A槽为基价，22AB槽-30AB槽9米12米统一加价60元/吨\n全风1.30角4-5公斤加价400元/吨",
                help="支持复杂的自然语言规则，包括基价指定、区间加价、特定规格加价等。"
            )
    else:
        # Direct 模式
        base_price_default = 3300
        rule_text = ""
        base_price_strategy = "auto_identify"



# --- 主区域：文件操作 ---
col1, col2 = st.columns(2)

with col1:
    st.info("步骤 1: 上传原始数据")
    data_file = st.file_uploader("📄 上传 Data 文件 (Excel)", type=["xlsx"], label_visibility="collapsed")

with col2:
    st.info("步骤 2: 上传目标模板")
    model_file = st.file_uploader("📋 上传 Model 文件 (Excel)", type=["xlsx"], label_visibility="collapsed")

# --- 弹窗逻辑定义 ---
# 定义错误提示弹窗
@st.dialog("⚠️ 提示")
def show_alert_dialog(message):
    st.warning(message)
    if st.button("知道了", type="primary", use_container_width=True):
        st.rerun()

# --- 执行区域 ---
st.markdown("---")

# 初始化session state
if 'preview_data' not in st.session_state:
    st.session_state['preview_data'] = None
if 'user_inputs' not in st.session_state:
    st.session_state['user_inputs'] = {}
if 'global_product_name' not in st.session_state:
    st.session_state['global_product_name'] = ""
if 'output_filename' not in st.session_state:
    st.session_state['output_filename'] = "整理后的报价单"

# 检查并显示下载按钮 (如果已处理成功)
if st.session_state.get('process_success', False) and st.session_state.get('processed_data'):
    st.success("✅ 处理成功！文件已准备好。")
    col_dl, col_reset = st.columns([3, 1])
    with col_dl:
        st.download_button(
            label=f"📥 点击下载: {st.session_state['output_filename']}.xlsx",
            data=st.session_state['processed_data'],
            file_name=f"{st.session_state['output_filename']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
    with col_reset:
        if st.button("🔄 开始新任务", use_container_width=True):
            st.session_state['process_success'] = False
            st.session_state['processed_data'] = None
            st.session_state['preview_data'] = None
            st.session_state['user_inputs'] = {}
            st.rerun()

# 显示预览和配置界面
elif st.session_state.get('preview_data'):
    # preview_data 现在是一个包含 'preview_df' 的字典
    preview_df = st.session_state['preview_data']['preview_df']
    
    st.markdown("### 📋 全数据预览与编辑")
    
    # --- 统一品名设置 ---
    col_g1, col_g2, col_g3 = st.columns([2, 2, 1])
    with col_g1:
        new_global_name = st.text_input(
            "统一品名 (可选)",
            value=st.session_state.get('global_product_name', ""),
            placeholder="例如：角钢",
            help="如果Data文件中没有“品名”列，或者您希望强制指定所有数据的品名，请在此输入。"
        )
    with col_g2:
        new_output_filename = st.text_input(
            "生成文件名",
            value=st.session_state.get('output_filename', "整理后的报价单"),
            help="无需输入后缀名，程序会自动添加 .xlsx"
        )
        st.session_state['output_filename'] = new_output_filename
        
    with col_g3:
        st.write("")
        st.write("")
        if st.button("🔄 更新预览", use_container_width=True):
            st.session_state['global_product_name'] = new_global_name
            with st.spinner("正在重新生成预览..."):
                try:
                    # 重新调用生成函数
                    new_preview_df = generate_preview_dataframe(
                        data_file, 
                        model_file, 
                        default_base_price=base_price_default if base_price_default is not None else 3300, 
                        rule_text=rule_text,
                        price_mode=price_mode if price_mode is not None else "auto",
                        global_product_name=new_global_name,
                        base_price_strategy=base_price_strategy if base_price_strategy is not None else "auto_identify"
                    )
                    st.session_state['preview_data'] = {"preview_df": new_preview_df}
                    st.rerun()
                except Exception as e:
                    st.error(f"更新失败: {str(e)}")

    st.info("👇 下表是即将生成的完整数据。您可以直接修改任意单元格（如补充缺失值、修改价格等）。修改后的结果将直接写入Excel。")

    # 显示可编辑表格
    # 动态计算高度：每行约35px，最大高度800px
    height = min(len(preview_df) * 35 + 38, 800)
    
    edited_df = st.data_editor(
        preview_df,
        hide_index=True,
        use_container_width=True,
        height=height,
        num_rows="dynamic" # 允许添加/删除行
    )
    
    st.divider()
    
    col_gen, col_back = st.columns([1, 1])
    with col_gen:
        if st.button("🚀 确认并生成 Excel", type="primary", use_container_width=True):
            with st.spinner("正在写入Excel文件..."):
                try:
                    # 直接使用编辑后的 DataFrame
                    output_io = process_files(
                        data_file, 
                        model_file, 
                        final_df=edited_df
                    )
                    st.session_state['processed_data'] = output_io
                    st.session_state['process_success'] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 生成失败: {str(e)}")
                    
    with col_back:
        if st.button("⬅️ 返回重新上传", use_container_width=True):
            st.session_state['preview_data'] = None
            st.rerun()

else:
    # 显示开始按钮
    if st.button("🔍 开始识别预览", type="primary", use_container_width=True):
        # 1. 基础校验
        if not data_file or not model_file:
            show_alert_dialog("请先上传 Data 文件和 Model 文件！")
        elif not price_mode:
            show_alert_dialog("请在左侧侧边栏选择一种【计算模式】！")
        
        # 2. 模式特定校验
        elif price_mode == "auto":
            if not base_price_strategy:
                show_alert_dialog("请在左侧选择【基价策略】（自动识别 或 固定基价）！")
            elif base_price_strategy == "fixed" and base_price_default is None:
                show_alert_dialog("您选择了【固定基价】策略，但未输入基价金额！")
            else:
                # 执行分析
                with st.spinner("正在生成全数据预览..."):
                    try:
                        preview_df = generate_preview_dataframe(
                            data_file, 
                            model_file, 
                            default_base_price=base_price_default if base_price_default is not None else 3300, 
                            rule_text=rule_text,
                            price_mode="auto",
                            global_product_name=st.session_state.get('global_product_name'),
                            base_price_strategy=base_price_strategy
                        )
                        st.session_state['preview_data'] = {"preview_df": preview_df}
                        st.rerun()
                    except Exception as e:
                        show_alert_dialog(f"分析失败: {str(e)}")
                
        elif price_mode == "rule":
            if not rule_text:
                show_alert_dialog("您选择了【自定义规则】模式，但未输入任何规则！")
            else:
                # 执行分析
                with st.spinner("正在生成全数据预览..."):
                    try:
                        preview_df = generate_preview_dataframe(
                            data_file, 
                            model_file, 
                            default_base_price=base_price_default if base_price_default is not None else 3300, 
                            rule_text=rule_text,
                            price_mode="rule",
                            global_product_name=st.session_state.get('global_product_name'),
                            base_price_strategy="auto_identify"
                        )
                        st.session_state['preview_data'] = {"preview_df": preview_df}
                        st.rerun()
                    except Exception as e:
                        show_alert_dialog(f"分析失败: {str(e)}")
        
        else:
            # Direct 模式
            # 执行分析
            with st.spinner("正在生成全数据预览..."):
                try:
                    preview_df = generate_preview_dataframe(
                        data_file, 
                        model_file, 
                        default_base_price=base_price_default if base_price_default is not None else 3300, 
                        rule_text=rule_text,
                        price_mode="direct",
                        global_product_name=st.session_state.get('global_product_name'),
                        base_price_strategy="auto_identify"
                    )
                    st.session_state['preview_data'] = {"preview_df": preview_df}
                    st.rerun()
                except Exception as e:
                    show_alert_dialog(f"分析失败: {str(e)}")

if not data_file and not model_file:
    st.info("👋 请先上传 Data 文件和 Model 模板文件以开始。")
