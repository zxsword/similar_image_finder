import os
from PIL import Image, ExifTags
import imagehash

# 使用 importlib 极速检测是否安装了 AI 库，避免在启动时执行耗时的 import torch
import importlib.util
if importlib.util.find_spec('torch') is not None and importlib.util.find_spec('torchvision') is not None:
    AI_MODE = True
else:
    AI_MODE = False

cnn_model = None       # 延迟加载，防止多进程环境下内存成倍暴增
cnn_preprocess = None

def get_color_matrix(img_rgb):
    """
    计算一个 4x4 的颜色矩阵，用于高效对比色彩分布，且完全兼容 JSON 缓存。
    新手必读：传统的指纹算法对“不同的风景图（比如都是大面积的蓝天白云）”容易误判。
    这个函数会把高分辨率的图片强行缩小成 4x4 像素的极小方块，
    用来提取最宏观、最基础的颜色分布，作为交叉比对的依据，能有效防止误报！
    """
    resample = Image.Resampling.BILINEAR if hasattr(Image, 'Resampling') else Image.BILINEAR
    small = img_rgb.resize((4, 4), resample)
    data = list(small.getdata())
    # 展平 RGB 元组为普通整数列表
    return [val for pixel in data for val in pixel]

def get_image_info(filepath, use_ai=False):
    """
    获取图片的信息：包括哈希值、分辨率、文件大小和拍照日期。
    这是并发处理的核心函数，每张图片都会调用它。
    """
    try:
        # 获取文件的大小（字节）
        size = os.path.getsize(filepath)
        # 获取文件的最后修改时间，用于验证缓存是否过期
        mtime = os.path.getmtime(filepath)
        # 使用 Pillow 打开图片。使用 with 语句可以确保处理完后图片文件会被正确关闭
        with Image.open(filepath) as img:
            # 获取图片的确切宽度和高度（必须在缩放前获取原图尺寸）
            width, height = img.size
            resolution = width * height
            dimensions = f"{width}x{height}"
            
            # 尝试获取图片的 EXIF 拍照日期（必须在缩放前获取）
            date_taken = "未知"
            try:
                exif = img.getexif() # 获取 EXIF 数据
                if exif:
                    for tag_id, val in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        if tag == 'DateTimeOriginal':
                            date_taken = val
                            break
            except Exception:
                pass

            # 【核心优化】在进行耗时的色彩转换、哈希和 AI 运算前，将图片缩小到 512x512 以内。
            resample = Image.Resampling.BILINEAR if hasattr(Image, 'Resampling') else Image.BILINEAR
            img.thumbnail((512, 512), resample)
            
            # 将图像转为 RGB，防止部分带有透明通道(Alpha)或怪异色域的图片导致后续处理失败
            img_rgb = img.convert('RGB')
            
            if AI_MODE and use_ai:
                # 只有在真正开始执行 AI 扫描时，才导入庞大的 torch 库
                import torch 
                
                # 如果启用了 AI，按需初始化模型 (仅在首次处理图片时加载入内存)
                global cnn_model, cnn_preprocess
                if cnn_model is None:
                    import warnings
                    import torchvision.transforms as transforms
                    from torchvision.models import mobilenet_v2
                    
                    warnings.filterwarnings("ignore") # 忽略预训练权重 API 的警告
                    cnn_model = mobilenet_v2(pretrained=True) # 加载轻量级卷积神经网络
                    cnn_model.eval() # 设置为推理模式
                    cnn_model.classifier = torch.nn.Identity() # 剥离分类层，只取前面的 1280 维特征向量
                    cnn_preprocess = transforms.Compose([
                        transforms.Resize(256), transforms.CenterCrop(224),
                        transforms.ToTensor(),
                        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                    ])
                
                # 【AI 魔法核心】利用 CNN 卷积神经网络“阅读”图片内容并提取高级语义特征。
                # 它不再只是对比颜色或轮廓，而是能理解图片里有“一只猫”或“一辆车”。
                # torch.no_grad() 的意思是告诉显卡/CPU：“我不训练模型，只做推理解析，帮我省点内存”。
                with torch.no_grad():
                    tensor = cnn_preprocess(img_rgb).unsqueeze(0)
                    feat = cnn_model(tensor).squeeze()
                    feat = torch.nn.functional.normalize(feat, p=2, dim=0) # 归一化以便后续计算余弦相似度
                    ai_vector = feat.tolist() # 转为普通列表，方便 JSON 缓存
            else:
                ai_vector = None

            # 无论是否启用 AI，都计算基础视觉哈希（加入了 ColorHash 色彩哈希）
            img_hash_p = imagehash.phash(img_rgb)
            img_hash_d = imagehash.dhash(img_rgb)
            img_hash_c = get_color_matrix(img_rgb)
            
        # 返回一个字典，包含了图片的各项数据
        return {
            'path': filepath, 'hash_p': img_hash_p, 'hash_d': img_hash_d, 'hash_c': img_hash_c,
            'ai_vector': ai_vector, 'resolution': resolution, 'dimensions': dimensions,
            'date_taken': date_taken, 'size': size, 'mtime': mtime, 'error': None
        }
    except Exception as e:
        return {'path': filepath, 'error': str(e)}