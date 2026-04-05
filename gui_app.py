import os
import tkinter as tk
from tkinter import ttk, messagebox

from core.engine import AI_MODE
from core.scanner import ScannerWorker
from utils.file_ops import open_in_explorer, delete_to_trash
from ui.control_panel import ControlPanel
from ui.action_panel import ActionPanel
from ui.preview_panel import PreviewPanel
from ui.pagination_view import PaginationView
from ui.exif_window import show_exif_window

class SimilarImageGUI:
    """
    MVC 架构的主控制器 (Controller)：负责串联和统筹所有的 UI 组件与数据状态。
    新手理解：这就好比一个“包工头”。他自己不负责画图（那是 ui 文件夹干的事），
    也不负责干苦力计算（那是 core 文件夹干的事）。他只负责接收用户的点击，然后指派对应的人去干活。
    """
    def __init__(self, root):
        self.root = root
        self.root.title(f"相似壁纸查找与清理工具{' (AI 深度学习引擎已启用)' if AI_MODE else ' (增强型视觉交叉引擎)'}") 
        self.root.minsize(850, 280)
        self.root.geometry("850x280")
        
        # StringVar, IntVar 是 Tkinter 特有的“绑定变量”。
        # 它们的好处是：只要代码里修改了这些变量的值，界面上对应的输入框/滑动条就会自动跟着变，反之亦然。
        self.vars = {
            'directory': tk.StringVar(),
            'directory2': tk.StringVar(),
            'threshold': tk.IntVar(value=5),
            'recursive': tk.BooleanVar(value=True),
            'use_ai': tk.BooleanVar(value=False),
            'show_preview': tk.BooleanVar(value=True)
        }
        self.groups, self.image_vars = [], {}
        self.scanner_worker = None
        
        self._build_ui()
        
    def _build_ui(self):
        # 挂载：顶部控制面板
        cmds = {'start_scan': self.start_scan, 'cancel_scan': self.cancel_scan, 'toggle_preview': self._toggle_preview}
        self.control_panel = ControlPanel(self.root, self.vars, cmds)
        self.control_panel.pack(side=tk.TOP, fill=tk.X)
        
        # 挂载：进度条区域
        self.progress_frame = ttk.Frame(self.root, padding="5")
        self.progress_frame.pack(side=tk.TOP, fill=tk.X)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.status_label = ttk.Label(self.progress_frame, text="")
        
        # 挂载：中间主视窗区域 (分页列表 + 右侧大图)
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.pagination_view = PaginationView(
            self.paned_window,
            on_preview_request=lambda p, info: self.preview_panel.update_preview(p, info) if self.vars['show_preview'].get() else None,
            on_explore_request=lambda p: self._safe_execute(open_in_explorer, p),
            on_delete_single_request=self._delete_single_image,
            on_exif_request=lambda p: show_exif_window(self.root, p),
            on_render_status_update=lambda msg: self.status_label.config(text=msg),
            on_render_complete=self._on_render_complete
        )
        self.paned_window.add(self.pagination_view, weight=3)
        
        self.preview_panel = PreviewPanel(self.paned_window)
        if self.vars['show_preview'].get():
            self.paned_window.add(self.preview_panel, weight=1)
        
        # 挂载：底部动作面板
        act_cmds = {'restore_default': self.restore_default_selection, 'deselect_all': self.deselect_all, 'delete_selected': self.delete_selected}
        self.action_panel = ActionPanel(self.root, act_cmds)
        self.action_panel.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 绑定全局鼠标滚轮事件，交由主控制器进行智能路由分发
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """智能处理鼠标滚轮事件：区分是左侧滚动还是右侧大图缩放"""
        # 如果预览面板开着，且鼠标正悬停在预览区的画布上，则执行图片缩放
        if self.vars['show_preview'].get() and hasattr(self, 'preview_panel') and event.widget == self.preview_panel.preview_canvas:
            self.preview_panel.do_zoom(event)
        else:
            # 否则，默认执行左侧界面的垂直滚动
            self.pagination_view._on_mousewheel(event)
        
    def _toggle_preview(self):
        if self.vars['show_preview'].get():
            self.paned_window.add(self.preview_panel, weight=1)
        else:
            self.paned_window.forget(self.preview_panel)
            
    def cancel_scan(self):
        if self.scanner_worker: self.scanner_worker.cancel()
        self.control_panel.cancel_btn.config(state=tk.DISABLED)
        self.status_label.config(text="正在安全中断扫描进程，请稍候...")

    def start_scan(self):
        d, d2 = self.vars['directory'].get(), self.vars['directory2'].get().strip()
        if not d or not os.path.isdir(d):
            return messagebox.showerror("错误", "请选择有效的文件夹路径")
        if d2 and not os.path.isdir(d2):
            return messagebox.showerror("错误", "对比文件夹路径无效")
            
        self.control_panel.set_state(is_scanning=True)
        self.action_panel.set_state(has_results=False)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.status_label.pack(side=tk.LEFT)
        self.progress_var.set(0)
        self.preview_panel.show_default()
        self.pagination_view.clear()
        self.groups, self.image_vars = [], {}
        
        # 这里是精髓：给后台苦力 (ScannerWorker) 留下的一系列“对讲机频道”(回调函数)。
        # 后台干活时不能直接碰界面组件，必须通过 root.after(0, ...) 安全地呼叫包工头来更新界面。
        callbacks = {
            'on_status': lambda msg: self.root.after(0, lambda: self.status_label.config(text=msg)),
            'on_progress': lambda val, msg: self.root.after(0, lambda: [self.progress_var.set(val), self.status_label.config(text=msg)]),
            'on_complete': lambda groups: self.root.after(0, lambda: self._on_scan_complete(groups)),
            'on_error': lambda err: self.root.after(0, lambda: [messagebox.showerror("扫描出错", err), self._scan_done("扫描发生错误。")]),
            'on_cancel': lambda: self.root.after(0, lambda: self._scan_done("扫描已终止。未完成的分析将不会显示。"))
        }
        self.scanner_worker = ScannerWorker(
            d, d2, self.vars['threshold'].get(), self.vars['recursive'].get(), self.vars['use_ai'].get(), callbacks
        )
        self.scanner_worker.start()
        
    def _on_scan_complete(self, groups):
        self.groups = groups
        if not self.groups: 
            self._play_notification_sound() # 播放柔和的完成提示音
            return self._scan_done("恭喜，没有找到相似的图片。")
        self.root.geometry("1250x800")
        self.pagination_view.load_groups(self.groups, self.image_vars)

    def _scan_done(self, text):
        self.control_panel.set_state(is_scanning=False)
        self.progress_bar.pack_forget()
        self.status_label.config(text=text)

    def _on_render_complete(self, total_groups):
        self.action_panel.set_state(has_results=True)
        
        # 渲染出所有图片列表后，播放柔和的完成提示音
        self._play_notification_sound() 
        
        self._scan_done(f"扫描完成，共找到 {total_groups} 组相似图片。")

    def _safe_execute(self, func, *args):
        try: func(*args)
        except Exception as e: messagebox.showerror("错误", str(e))
            
    def deselect_all(self):
        for var in self.image_vars.values(): var.set(False)
            
    def restore_default_selection(self):
        for group in self.groups:
            if not group: continue
            if group[0]['path'] in self.image_vars: self.image_vars[group[0]['path']].set(False)
            for img_info in group[1:]:
                if img_info['path'] in self.image_vars: self.image_vars[img_info['path']].set(True)

    def _delete_single_image(self, filepath, frame):
        if not messagebox.askyesno("确认", f"确定移至回收站吗？\n\n{os.path.basename(filepath)}"): return
        try:
            delete_to_trash(filepath); frame.destroy()
            if filepath in self.image_vars: del self.image_vars[filepath]
        except Exception as e:
            messagebox.showerror("删除失败", str(e))

    def delete_selected(self):
        to_delete = [path for path, var in self.image_vars.items() if var.get()]
        if not to_delete: return messagebox.showinfo("提示", "您还没有勾选任何图片。")
        if not messagebox.askyesno("确认", f"确定要将这 {len(to_delete)} 张图片移至回收站吗？"): return
            
        success_count, error_count = 0, 0
        for path in to_delete:
            try:
                delete_to_trash(path)
                success_count += 1
            except Exception as e:
                print(f"删除失败 {path}: {e}")
                error_count += 1
                
        messagebox.showinfo("清理完成", f"成功移出 {success_count} 张。{'有 '+str(error_count)+' 张失败。' if error_count else ''}")
        self.start_scan()

    def _play_notification_sound(self):
        """跨平台播放柔和悦耳的系统提示音，代替刺耳的警告音"""
        import sys
        try:
            if sys.platform == 'win32':
                import winsound
                import os
                # 优先寻找 Windows 10/11 柔和的现代系统通知音
                wav_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Media', 'Windows Notify System Generic.wav')
                if not os.path.exists(wav_path):
                    # 如果找不到，退而求其次寻找经典的清脆风铃声
                    wav_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Media', 'chimes.wav')
                
                if os.path.exists(wav_path):
                    # SND_FILENAME 表示这是一个文件路径；SND_ASYNC 表示异步后台播放，绝对不会卡住界面
                    winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                else:
                    winsound.MessageBeep(winsound.MB_OK)
            elif sys.platform == 'darwin':
                import subprocess
                import os
                mac_sound = '/System/Library/Sounds/Glass.aiff'
                if os.path.exists(mac_sound):
                    # 使用 Popen 进行异步播放，防止卡顿界面，并且隐藏掉潜在的终端报错输出
                    subprocess.Popen(['afplay', mac_sound], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    self.root.bell()
            else:
                self.root.bell() # Linux 等系统退回默认
        except Exception:
            self.root.bell()

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    # 补全独立运行时的启动代码，方便单独测试界面
    root = tk.Tk()
    app = SimilarImageGUI(root)
    root.mainloop()
