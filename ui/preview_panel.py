import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class PreviewPanel(ttk.Frame):
    """
    独立的右侧图片预览面板组件。
    负责展示大图、鼠标拖拽漫游、滚轮缩放以及详细信息显示。
    """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, relief=tk.SUNKEN, borderwidth=1, *args, **kwargs)
        
        self.preview_info = ttk.Label(self, text="", justify=tk.CENTER)
        self.preview_info.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        self.preview_canvas = tk.Canvas(self, bg="#e8e8e8", highlightthickness=0)
        self.preview_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.preview_pil_image = None
        self.preview_scale = 1.0
        self.preview_image_id = None
        
        # 绑定内部画布事件
        self.preview_canvas.bind("<ButtonPress-1>", lambda e: self.preview_canvas.scan_mark(e.x, e.y))
        self.preview_canvas.bind("<B1-Motion>", lambda e: self.preview_canvas.scan_dragto(e.x, e.y, gain=1))
        self.preview_canvas.bind("<Configure>", lambda e: self._fit_preview_to_canvas() if self.preview_pil_image else self.show_default())
        
        self.show_default()

    def show_default(self):
        """清空图片，显示默认提示文本"""
        self.preview_pil_image = None
        self.preview_info.config(text="")
        self.preview_canvas.delete("all")
        self.preview_image_id = None
        c_w = self.preview_canvas.winfo_width() or 400
        c_h = self.preview_canvas.winfo_height() or 400
        self.preview_canvas.create_text(
            c_w//2, c_h//2, 
            text="点击左侧图片\n即可在此处查看大图预览\n(支持鼠标拖拽与滚轮缩放)", 
            justify=tk.CENTER, fill="#666"
        )

    def update_preview(self, filepath, info_text):
        """外部调用的接口：加载并显示新图片"""
        try:
            with Image.open(filepath) as img:
                self.preview_pil_image = img.convert("RGB")
            self.preview_info.config(text=info_text)
            self._fit_preview_to_canvas()
        except Exception as e:
            self.preview_pil_image = None
            self.preview_info.config(text="")
            self.preview_canvas.delete("all")
            c_w = self.preview_canvas.winfo_width() or 400
            c_h = self.preview_canvas.winfo_height() or 400
            self.preview_canvas.create_text(c_w//2, c_h//2, text=f"预览加载失败\n{e}", justify=tk.CENTER)

    def _fit_preview_to_canvas(self):
        if not self.preview_pil_image: return
        c_w, c_h = self.preview_canvas.winfo_width(), self.preview_canvas.winfo_height()
        if c_w <= 1 or c_h <= 1: return
        i_w, i_h = self.preview_pil_image.size
        self.preview_scale = min(c_w / i_w, c_h / i_h) * 0.95 
        self.preview_canvas.xview_moveto(0)
        self.preview_canvas.yview_moveto(0)
        self._draw_preview_image(center_x=c_w//2, center_y=c_h//2)
        
    def _draw_preview_image(self, center_x=None, center_y=None):
        if not self.preview_pil_image: return
        new_w = max(1, int(self.preview_pil_image.width * self.preview_scale))
        new_h = max(1, int(self.preview_pil_image.height * self.preview_scale))
        resample = Image.Resampling.BILINEAR if hasattr(Image, 'Resampling') else Image.BILINEAR
        self.preview_tk_image = ImageTk.PhotoImage(self.preview_pil_image.resize((new_w, new_h), resample))
        if self.preview_image_id is not None and self.preview_canvas.type(self.preview_image_id):
            self.preview_canvas.itemconfig(self.preview_image_id, image=self.preview_tk_image)
        else:
            self.preview_canvas.delete("all")
            self.preview_image_id = self.preview_canvas.create_image(center_x or 200, center_y or 200, anchor=tk.CENTER, image=self.preview_tk_image)

    def do_zoom(self, event):
        """处理外部传来的鼠标滚轮缩放事件"""
        if not self.preview_pil_image: return
        zoom_factor = 1.1 if event.delta > 0 else 0.9
        new_scale = self.preview_scale * zoom_factor
        if 0.01 < new_scale < 10.0:
            self.preview_scale = new_scale
            self._draw_preview_image()