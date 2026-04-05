import tkinter as tk
from tkinter import ttk

class ActionPanel(ttk.Frame):
    """底部动作面板组件：全局勾选和一键回收"""
    def __init__(self, parent, commands_dict, *args, **kwargs):
        super().__init__(parent, padding="10", *args, **kwargs)
        self.cmds = commands_dict
        self._build_ui()

    def _build_ui(self):
        self.btn_restore = ttk.Button(self, text="恢复默认推荐勾选", command=self.cmds['restore_default'], state=tk.DISABLED)
        self.btn_restore.pack(side=tk.LEFT, padx=5)
        self.btn_deselect = ttk.Button(self, text="一键取消所有勾选", command=self.cmds['deselect_all'], state=tk.DISABLED)
        self.btn_deselect.pack(side=tk.LEFT, padx=5)
        self.del_btn = ttk.Button(self, text="将选中图片移至回收站", command=self.cmds['delete_selected'], state=tk.DISABLED)
        self.del_btn.pack(side=tk.RIGHT)

    def set_state(self, has_results):
        state = tk.NORMAL if has_results else tk.DISABLED
        self.btn_restore.config(state=state); self.btn_deselect.config(state=state); self.del_btn.config(state=state)