import tkinter as tk
from tkinter import ttk, filedialog
from core.engine import AI_MODE

class ControlPanel(ttk.Frame):
    """顶部控制面板组件：包含路径选择、参数微调与扫描按钮"""
    def __init__(self, parent, vars_dict, commands_dict, *args, **kwargs):
        super().__init__(parent, padding="10", *args, **kwargs)
        self.vars = vars_dict
        self.cmds = commands_dict
        self._build_ui()

    def _build_ui(self):
        # 第一行：主文件夹选择
        row1 = ttk.Frame(self)
        row1.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Label(row1, text="壁纸文件夹:", width=15).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.vars['directory'], width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="浏览...", command=self._browse_dir).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(row1, text="包含子文件夹", variable=self.vars['recursive']).pack(side=tk.LEFT)
        
        # 第二行：辅助文件夹选择
        row2 = ttk.Frame(self)
        row2.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Label(row2, text="对比文件夹(可选):", width=15).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.vars['directory2'], width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="浏览...", command=self._browse_dir2).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(row2, text="(偶尔使用：跨文件夹比对，留空则仅扫描上方文件夹)").pack(side=tk.LEFT)
        
        # 第三行：参数设置与核心按钮
        row3 = ttk.Frame(self)
        row3.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Label(row3, text="相似度标准:", width=15).pack(side=tk.LEFT)
        ttk.Label(row3, text="严格(0)").pack(side=tk.LEFT)
        ttk.Scale(row3, from_=0, to=20, variable=self.vars['threshold'], orient=tk.HORIZONTAL, length=150,
                  command=lambda v: self.thresh_val_label.config(text=f"当前值: {int(float(v))}")).pack(side=tk.LEFT, padx=5)
        ttk.Label(row3, text="宽松(20)").pack(side=tk.LEFT)
        self.thresh_val_label = ttk.Label(row3, text=f"当前值: {self.vars['threshold'].get()}")
        self.thresh_val_label.pack(side=tk.LEFT, padx=(10, 20))
        
        self.scan_btn = ttk.Button(row3, text="开始扫描", command=self.cmds['start_scan'])
        self.scan_btn.pack(side=tk.LEFT, padx=5)
        self.cancel_btn = ttk.Button(row3, text="取消扫描", command=self.cmds['cancel_scan'], state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # 第四行：附加功能开关
        row4 = ttk.Frame(self)
        row4.pack(side=tk.TOP, fill=tk.X, pady=2)
        ttk.Label(row4, text="附加选项:", width=15).pack(side=tk.LEFT)
        if AI_MODE: ttk.Checkbutton(row4, text="启用 AI 神经网络精准识别(较慢)", variable=self.vars['use_ai']).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(row4, text="开启右侧预览", variable=self.vars['show_preview'], command=self.cmds['toggle_preview']).pack(side=tk.LEFT, padx=5)

    def _browse_dir(self):
        d = filedialog.askdirectory(); self.vars['directory'].set(d) if d else None
    def _browse_dir2(self):
        d = filedialog.askdirectory(); self.vars['directory2'].set(d) if d else None
    def set_state(self, is_scanning):
        self.scan_btn.config(state=tk.DISABLED if is_scanning else tk.NORMAL)
        self.cancel_btn.config(state=tk.NORMAL if is_scanning else tk.DISABLED)