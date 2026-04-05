import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ExifTags

def show_exif_window(parent, filepath):
    """弹出一个新窗口，展示图片的所有 EXIF 元数据"""
    try:
        with Image.open(filepath) as img:
            exif = img.getexif()
            if not exif:
                messagebox.showinfo("EXIF 信息", "该图片没有包含任何 EXIF 元数据。", parent=parent)
                return
            info = [f"{ExifTags.TAGS.get(k, k)}: {str(v)[:200]}" for k, v in exif.items()]
            info_str = "\n".join(info)
            
            top = tk.Toplevel(parent)
            top.title(f"EXIF 信息 - {os.path.basename(filepath)}")
            top.geometry("450x550")
            
            txt = tk.Text(top, wrap=tk.WORD, padx=10, pady=10)
            txt.insert(tk.END, info_str)
            txt.config(state=tk.DISABLED)
            scroll = ttk.Scrollbar(top, command=txt.yview)
            txt.config(yscrollcommand=scroll.set)
            scroll.pack(side=tk.RIGHT, fill=tk.Y); txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    except Exception as e:
        messagebox.showerror("错误", f"无法读取 EXIF:\n{e}", parent=parent)