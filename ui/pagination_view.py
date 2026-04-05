import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from utils.file_ops import format_size

class PaginationView(ttk.Frame):
    """
    独立的分页与图片列表渲染组件。
    负责管理画布、滚动条、分页逻辑以及海量缩略图的异步加载。
    """
    def __init__(self, parent, on_preview_request, on_explore_request, on_delete_single_request, on_exif_request, on_render_status_update, on_render_complete, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # 注册父组件传进来的回调函数 (Callbacks)
        self.on_preview_request = on_preview_request
        self.on_explore_request = on_explore_request
        self.on_delete_single_request = on_delete_single_request
        self.on_exif_request = on_exif_request
        self.on_render_status_update = on_render_status_update
        self.on_render_complete = on_render_complete
        
        # 状态变量
        self.groups = []
        self.image_vars = {}
        self.current_page = 1
        self.total_pages = 1
        self.groups_per_page = 40 # 每页显示 40 组以防触碰底层渲染极限
        self.thumbnail_queue = []
        self._is_processing_thumbnails = False
        self.render_index = 0
        
        self._build_ui()
        
    def _build_ui(self):
        """构建分页器与滚动画布"""
        # --- 分页控制区域 ---
        self.pagination_frame = ttk.Frame(self)
        self.pagination_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        self.btn_prev = ttk.Button(self.pagination_frame, text="上一页", command=self._prev_page, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, padx=10)
        self.lbl_page = ttk.Label(self.pagination_frame, text="等待扫描...")
        self.lbl_page.pack(side=tk.LEFT, padx=10)
        self.btn_next = ttk.Button(self.pagination_frame, text="下一页", command=self._next_page, state=tk.DISABLED)
        self.btn_next.pack(side=tk.LEFT, padx=10)
        
        # --- 滚动画布区域 ---
        self.canvas = tk.Canvas(self, bg="#f0f0f0")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.x_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set, xscrollcommand=self.x_scrollbar.set)
        
        self.x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _on_mousewheel(self, event):
        """处理画布的垂直滚动"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def clear(self):
        """清空当前界面内容并重置状态"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.thumbnail_queue = []
        self.lbl_page.config(text="扫描中...")
        self.btn_prev.config(state=tk.DISABLED)
        self.btn_next.config(state=tk.DISABLED)

    def load_groups(self, groups, image_vars):
        """接收新数据并开始渲染第一页"""
        self.groups = groups
        self.image_vars = image_vars
        self.total_pages = max(1, (len(self.groups) + self.groups_per_page - 1) // self.groups_per_page)
        self.current_page = 1
        self._render_page()

    def _prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._render_page()
            
    def _next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._render_page()
            
    def _render_page(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.thumbnail_queue = []
        
        self.lbl_page.config(text=f"第 {self.current_page}/{self.total_pages} 页 (共 {len(self.groups)} 组)")
        self.btn_prev.config(state=tk.NORMAL if self.current_page > 1 else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL if self.current_page < self.total_pages else tk.DISABLED)
        
        start_idx = (self.current_page - 1) * self.groups_per_page
        end_idx = min(start_idx + self.groups_per_page, len(self.groups))
        
        self.current_page_groups = self.groups[start_idx:end_idx]
        self.global_group_start_idx = start_idx
        
        self.render_index = 0
        self.on_render_status_update(f"正在生成第 {self.current_page} 页界面...")
        self._render_group_chunk()

    def _render_group_chunk(self):
        chunk_size = 10
        end_idx = min(self.render_index + chunk_size, len(self.current_page_groups))
        
        for i in range(self.render_index, end_idx):
            display_idx = self.global_group_start_idx + i + 1 
            group = self.current_page_groups[i]
            group.sort(key=lambda x: (x['resolution'], x['size']), reverse=True)
            
            group_frame = ttk.LabelFrame(self.scrollable_frame, text=f"第 {display_idx} 组")
            group_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
            
            for img_idx, img_info in enumerate(group):
                path = img_info['path']
                img_frame = ttk.Frame(group_frame)
                img_frame.pack(side=tk.LEFT, padx=10, pady=5)
                
                lbl_img = tk.Label(img_frame, text="正在加载预览...", width=20, height=10, bg="#e0e0e0")
                lbl_img.pack(side=tk.TOP)
                self.thumbnail_queue.append((path, lbl_img))
                    
                info_text = f"{os.path.basename(path)}\n分辨率: {img_info.get('dimensions', '未知')}\n"
                if img_info.get('date_taken', '未知') != '未知':
                    info_text += f"日期: {img_info.get('date_taken')}\n"
                info_text += f"大小: {format_size(img_info['size'])} ({'最高质量' if img_idx == 0 else '建议删除'})"
                    
                info_label = ttk.Label(img_frame, text=info_text, justify=tk.CENTER)
                info_label.pack(side=tk.TOP, pady=2)
                
                lbl_img.bind("<Button-1>", lambda e, p=path, info=info_text: self.on_preview_request(p, info))
                info_label.bind("<Button-1>", lambda e, p=path, info=info_text: self.on_preview_request(p, info))
                
                if path not in self.image_vars:
                    self.image_vars[path] = tk.BooleanVar(value=(img_idx > 0))
                cb = ttk.Checkbutton(img_frame, text="批量选择此图片", variable=self.image_vars[path])
                cb.pack(side=tk.TOP)
                
                btn_frame = ttk.Frame(img_frame)
                btn_frame.pack(side=tk.TOP, pady=5)
                ttk.Button(btn_frame, text="在文件夹中显示", command=lambda p=path: self.on_explore_request(p)).pack(side=tk.TOP, fill=tk.X, pady=2)
                ttk.Button(btn_frame, text="单独删除此图", command=lambda p=path, f=img_frame: self.on_delete_single_request(p, f)).pack(side=tk.TOP, fill=tk.X, pady=2)
                ttk.Button(btn_frame, text="查看完整EXIF", command=lambda p=path: self.on_exif_request(p)).pack(side=tk.TOP, fill=tk.X, pady=2)
                
        self.render_index = end_idx
        
        if self.render_index < len(self.current_page_groups):
            self.on_render_status_update(f"正在生成界面 ({self.render_index}/{len(self.current_page_groups)})...")
            self.after(10, self._render_group_chunk)
        else:
            self.on_render_complete(len(self.groups))
            self.canvas.yview_moveto(0)
            if not getattr(self, '_is_processing_thumbnails', False):
                self.after(50, self._process_thumbnail_queue)
                
    def _process_thumbnail_queue(self):
        if not self.thumbnail_queue:
            self._is_processing_thumbnails = False
            return
            
        self._is_processing_thumbnails = True
        for _ in range(3):
            try:
                path, lbl_img = self.thumbnail_queue.pop(0)
            except IndexError:
                break
            if not lbl_img.winfo_exists():
                continue
            try:
                with Image.open(path) as pil_img:
                    img_copy = pil_img.copy()
                    img_copy.thumbnail((200, 200))
                    tk_img = ImageTk.PhotoImage(img_copy)
                    lbl_img.config(image=tk_img, text="", width=0, height=0)
                    lbl_img.image = tk_img
            except Exception:
                if lbl_img.winfo_exists(): lbl_img.config(text="图片加载失败", image="")
                
        if self.thumbnail_queue:
            self.after(10, self._process_thumbnail_queue)
        else:
            self._is_processing_thumbnails = False