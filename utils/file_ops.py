import os
import sys
import subprocess
from send2trash import send2trash

# 尝试导入 pillow_heif 以支持苹果的 .HEIC 格式
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:
    HEIF_SUPPORTED = False

# 定义支持的图片文件扩展名集合，只有这些格式的文件才会被处理
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
if HEIF_SUPPORTED:
    SUPPORTED_EXTENSIONS.update({'.heic', '.heif'})

def find_images(directory, recursive=True):
    """
    在一个目录中查找所有支持的图片文件。
    如果 recursive 为 True，则递归包含所有子文件夹；否则仅扫描当前目录。
    """
    images = [] # 用于保存找到的图片路径的列表
    
    if recursive:
        # os.walk 会遍历指定目录下的所有层级的文件夹
        for root, _, files in os.walk(directory):
            for file in files:
                # 获取文件的扩展名，并转换为小写，比如 '.JPG' 变成 '.jpg'
                ext = os.path.splitext(file)[1].lower()
                # 检查扩展名是否在我们支持的集合中
                if ext in SUPPORTED_EXTENSIONS:
                    # 拼接完整的文件路径并添加到列表中
                    images.append(os.path.join(root, file))
    else:
        # 只遍历当前目录下的文件，不深入子文件夹
        try:
            for entry in os.scandir(directory):
                if entry.is_file() and os.path.splitext(entry.name)[1].lower() in SUPPORTED_EXTENSIONS:
                    images.append(entry.path)
        except OSError:
            pass
    return images # 返回所有找到的图片路径

def format_size(size_bytes):
    """将文件大小（字节）格式化为人类易读的字符串（KB 或 MB）。"""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"

def open_in_explorer(filepath):
    """跨平台调用系统的文件资源管理器，打开文件所在目录并尝试高亮选中该文件。"""
    if not os.path.exists(filepath):
        raise FileNotFoundError("找不到该文件，可能已被移动或删除。")
    if sys.platform == 'win32':
        subprocess.run(['explorer', '/select,', os.path.normpath(filepath)])
    elif sys.platform == 'darwin': # macOS
        subprocess.run(['open', '-R', filepath])
    else: # Linux 等其他系统
        subprocess.run(['xdg-open', os.path.dirname(filepath)])

def delete_to_trash(filepath):
    """安全删除文件到回收站"""
    target_path = os.path.abspath(os.path.normpath(filepath))
    if not os.path.exists(target_path): raise FileNotFoundError("找不到该文件。")
    send2trash(target_path)