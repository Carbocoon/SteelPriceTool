import streamlit.web.cli as stcli
import os, sys
import webbrowser
from threading import Timer

# Dummy imports to ensure PyInstaller packages them
import pandas as pd
import openpyxl
import core.processor
import core.rules

def resolve_path(path):
    if getattr(sys, "frozen", False):
        basedir = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)

def open_browser():
    # 延迟一小段时间等待 Streamlit 服务器启动
    webbrowser.open_new("http://localhost:8501")

if __name__ == "__main__":
    # 启动定时器，在主程序启动后打开浏览器
    Timer(2, open_browser).start()

    # 强制 headless 模式，避免弹出浏览器选择
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    
    app_path = resolve_path("app.py")
    
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
