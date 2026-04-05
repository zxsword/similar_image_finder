import sys # sys 模块提供了访问由解释器使用或维护的变量以及与解释器强烈交互的函数。在这里用来获取命令行参数。
import multiprocessing # 用于支持多进程编程。在这里主要为了解决 Windows 下打包成可执行文件的兼容性问题。

def start_gui():
    """
    启动图形用户界面 (GUI) 模式。
    这个函数会按需导入 GUI 相关的库，避免在纯命令行模式下不必要地加载图形库。
    """
    import tkinter as tk # 导入 GUI 基础库
    from gui_app import SimilarImageGUI # 从我们的 gui_app.py 中导入 GUI 类
    
    root = tk.Tk() # 创建主窗口对象（这是所有界面的地基）
    app = SimilarImageGUI(root) # 实例化我们写的图形界面应用
    root.mainloop() # 让主窗口进入无限循环监听状态，这样窗口才不会闪退，能一直响应鼠标点击

def start_cli():
    """
    启动命令行 (CLI) 模式。
    按需导入 CLI 相关的库。
    """
    from find_similar import main as cli_main # 导入命令行工具的主函数，并起个别名防止名字冲突
    cli_main() # 执行命令行主逻辑

# 判断当前文件是否是被直接运行（而不是被其他文件当作模块导入）
if __name__ == '__main__':
    # 修复在 Windows 上使用多进程（打包成 exe 后）的常见问题。
    # 必须在主模块的最前面加上这一句，否则多进程代码会无限循环启动新的子进程导致系统崩溃。
    multiprocessing.freeze_support()
    
    # sys.argv 是一个列表，包含了在命令行中输入的所有参数。
    # 第一个参数 sys.argv[0] 永远是脚本的名字（如 main.py）。
    # 如果列表长度大于 1，说明用户在运行脚本时还输入了其他参数（如 `python main.py "D:\图片"`）
    if len(sys.argv) > 1:
        # 只要带了参数，就认为用户想要使用纯命令行模式，这样方便高级用户写脚本自动化处理
        start_cli()
    else:
        # 如果什么参数都没带（比如直接双击运行脚本或 exe），就默认启动好用的图形界面
        start_gui()
