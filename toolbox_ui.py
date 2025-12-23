import streamlit as st
import pandas as pd
from io import BytesIO

def render_toolbox():
    st.header("🧰 通用工具箱")
    
    tab1, tab2 = st.tabs(["🔢 数值列运算", "🚧 更多功能敬请期待"])
    
    with tab1:
        st.subheader("数值列批量运算")
        st.markdown("上传表格，选择一列数值，对其进行加减乘除运算。")
        
        uploaded_file = st.file_uploader("上传Excel或CSV文件", type=['xlsx', 'xls', 'csv'], key="toolbox_uploader")
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.write("数据预览：")
                st.dataframe(df.head())
                
                # 筛选数值类型的列
                numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
                
                if not numeric_columns:
                    st.warning("未检测到数值类型的列，请检查数据格式。")
                else:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        selected_col = st.selectbox("选择要处理的列", numeric_columns)
                    
                    with col2:
                        operation = st.selectbox("选择运算", ["加 (+)", "减 (-)", "乘 (*)", "除 (/)"])
                    
                    with col3:
                        operand = st.number_input("输入运算数值", value=0.0, step=0.1)
                    
                    if st.button("执行运算"):
                        try:
                            result_df = df.copy()
                            if operation == "加 (+)":
                                result_df[selected_col] = result_df[selected_col] + operand
                            elif operation == "减 (-)":
                                result_df[selected_col] = result_df[selected_col] - operand
                            elif operation == "乘 (*)":
                                result_df[selected_col] = result_df[selected_col] * operand
                            elif operation == "除 (/)":
                                if operand == 0:
                                    st.error("除数不能为0")
                                    return
                                result_df[selected_col] = result_df[selected_col] / operand
                            
                            st.success("运算完成！")
                            st.dataframe(result_df.head())
                            
                            # 下载结果
                            output = BytesIO()
                            if uploaded_file.name.endswith('.csv'):
                                result_df.to_csv(output, index=False, encoding='utf-8-sig')
                                file_name = f"processed_{uploaded_file.name}"
                                mime_type = "text/csv"
                            else:
                                result_df.to_excel(output, index=False)
                                file_name = f"processed_{uploaded_file.name}"
                                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            
                            st.download_button(
                                label="📥 下载处理后的文件",
                                data=output.getvalue(),
                                file_name=file_name,
                                mime=mime_type
                            )
                            
                        except Exception as e:
                            st.error(f"运算过程中发生错误: {str(e)}")
                            
            except Exception as e:
                st.error(f"读取文件失败: {str(e)}")
