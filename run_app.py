import streamlit.web.cli as stcli
import os, sys

def resolve_path(path):
    if getattr(sys, "frozen", False):
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)

if __name__ == "__main__":
    # 设置环境变量，防止Streamlit显示警告
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    
    # 获取app.py的路径
    app_path = resolve_path("app.py")
    
    # 构造启动参数
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        "--server.port=8501",
    ]
    
    sys.exit(stcli.main())