import argparse # 用于解析命令行输入的参数
import os # 提供了与操作系统交互的功能，比如处理文件路径、读取文件大小等
import shutil # 用于高级的文件操作，比如移动文件
import concurrent.futures # 用于实现多进程并发处理，加速图片读取和计算
from tqdm import tqdm # 用于在终端中显示进度条

# 引入我们刚刚抽离出来的模块
from core.cache import load_cache, save_cache, get_uncached_paths
from core.engine import get_image_info, AI_MODE
from core.matcher import group_similar_images
from utils.file_ops import find_images, format_size

def handle_similar_groups(groups, target_dir, action):
    """
    处理找出的相似图片分组。
    可以打印出来（report）或者把质量较差的移动到一个审核文件夹（move）。
    """
    # 定义用来存放较差图片的文件夹路径
    review_dir = os.path.join(target_dir, 'Review_Inferior_Images')
    
    # 如果用户选择的是 move 操作，并且审核文件夹不存在，就创建它
    if action == 'move' and not os.path.exists(review_dir):
        os.makedirs(review_dir)

    total_moved = 0 # 记录移动了多少张图片
    total_saved_bytes = 0 # 记录节省了多少磁盘空间（字节）

    print(f"\nFound {len(groups)} groups of similar images.") # 打印找到了多少组相似图片

    # 遍历每一个相似图片组（idx 是从 1 开始的组号）
    for idx, group in enumerate(groups, 1):
        # 对组内的图片进行排序：主要按分辨率从大到小排，如果分辨率一样，再按文件大小从大到小排
        # 这样排序后，排在第一位的（索引为 0 的）就是质量“最好”的图片
        group.sort(key=lambda x: (x['resolution'], x['size']), reverse=True)
        
        best_image = group[0] # 质量最好的那张
        inferior_images = group[1:] # 剩下的都是质量较差的

        print(f"\nGroup {idx}:")
        print(f"  Best quality: {best_image['path']} (Res: {best_image['dimensions']}, Date: {best_image['date_taken']}, Size: {format_size(best_image['size'])})")
        
        # 遍历质量较差的图片
        for img in inferior_images:
            print(f"  Inferior:     {img['path']} (Res: {img['dimensions']}, Date: {img['date_taken']}, Size: {format_size(img['size'])})")
            total_saved_bytes += img['size'] # 累加潜在节省的空间
            
            # 如果操作是 'move'，则将图片移动到审核文件夹
            if action == 'move':
                filename = os.path.basename(img['path']) # 获取文件名
                dest_path = os.path.join(review_dir, filename) # 拼接目标路径
                
                # 处理同名冲突：如果审核文件夹里已经有同名文件了，就在文件名后加数字
                counter = 1
                while os.path.exists(dest_path):
                    # 分离文件名和扩展名
                    name, ext = os.path.splitext(filename)
                    # 重新拼接加上了序号的新文件名
                    dest_path = os.path.join(review_dir, f"{name}_{counter}{ext}")
                    counter += 1
                
                try:
                    # 使用 shutil.move 移动文件
                    shutil.move(img['path'], dest_path)
                    total_moved += 1 # 移动计数加一
                except Exception as e:
                    print(f"  Failed to move {img['path']}: {e}") # 打印移动失败的信息

    # 打印总结信息
    if action == 'move':
        print(f"\nOperation complete. Moved {total_moved} inferior images to '{review_dir}'.")
    else:
        print(f"\nOperation complete. Found {sum(len(g)-1 for g in groups)} inferior images.")
        
    print(f"Potential space savings: {total_saved_bytes / (1024 * 1024):.2f} MB")

def main():
    """
    程序的主入口函数。
    在这里设置命令行参数并统筹整个执行流程。
    """
    # 初始化命令行参数解析器
    parser = argparse.ArgumentParser(description='Find and manage similar images in a folder.')
    # 添加一个必填参数：要扫描的目录
    parser.add_argument('directory', type=str, help='Directory containing the images to scan.')
    # 添加一个可选参数：相似度阈值。默认值是 5。数值越小，判断标准越严格，找出的图片越像
    parser.add_argument('--threshold', type=int, default=5, help='Similarity threshold (Hamming distance of phash, default: 5. Lower is more strict).')
    # 添加一个可选参数：执行的操作。可以是 'report'（仅报告）或 'move'（移动差图），默认为 'move'
    parser.add_argument('--action', choices=['report', 'move'], default='move', 
                        help='What to do with inferior images. "report" only prints them, "move" puts them in a Review folder. Default: move.')
    # 添加一个可选参数：使用的进程数，默认为电脑的 CPU 核心数，用于加速处理
    parser.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 4) - 2), help='Number of parallel workers for processing images.')
    # 添加一个可选参数：是否禁用递归扫描子文件夹
    parser.add_argument('--no-recursive', action='store_true', help='Do not scan subdirectories.')
    # 添加一个可选参数：是否启用 AI 深度学习算法
    parser.add_argument('--use-ai', action='store_true', help='Enable AI CNN feature extraction.')

    # 解析用户在命令行中输入的参数
    args = parser.parse_args()
    
    # 获取要扫描目录的绝对路径
    target_dir = os.path.abspath(args.directory)
    # 检查该路径是否真的是一个存在的目录
    if not os.path.isdir(target_dir):
        print(f"Error: Directory '{target_dir}' does not exist.")
        return # 目录不存在则退出程序

    print(f"Scanning '{target_dir}' for images...")
    # 调用函数查找所有的图片
    image_paths = find_images(target_dir, recursive=not args.no_recursive)
    print(f"Found {len(image_paths)} supported images.")
    
    # 如果图片少于 2 张，无法比较，直接退出
    if len(image_paths) < 2:
        print("Not enough images to compare.")
        return

    # 加载当前目录的本地缓存
    cache_file = os.path.join(target_dir, '.sim_image_cache.json')
    cache_data = load_cache(cache_file)
    needs_calc, cached_infos = get_uncached_paths(image_paths, cache_data, use_ai=args.use_ai)
    
    image_infos = cached_infos
    
    if needs_calc:
        print(f"Calculating hashes for {len(needs_calc)} new/modified images using {args.workers} workers...")
        
        # 使用多进程并发池仅对缺失缓存的图片进行计算
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
            # 提交任务时带上 use_ai 标识
            futures = [executor.submit(get_image_info, p, args.use_ai) for p in needs_calc]
            # 收集结果
            results = [f.result() for f in tqdm(concurrent.futures.as_completed(futures), total=len(needs_calc))]
    
        # 遍历处理结果
        for res in results:
            if res.get('error'):
                print(f"Warning: Could not process {res['path']}: {res['error']}")
            else:
                image_infos.append(res) # 正常的图片信息加入列表
                
                # 将计算完的结果更新到字典中以备缓存
                cache_entry = res.copy()
                cache_entry['hash_p'] = str(cache_entry['hash_p']) # ImageHash 转为字符串以便 JSON 序列化
                cache_entry['hash_d'] = str(cache_entry['hash_d'])
                # 新版 hash_c 是数字列表，原生支持 JSON 保存，直接省去 str() 转换！
                cache_data[res['path']] = cache_entry
        
        # 扫描完毕，将最新的缓存数据写入文件
        save_cache(cache_file, cache_data)
    else:
        print("All image hashes loaded from cache.")

    # 调用函数对计算好哈希值的图片进行分组
    groups = group_similar_images(image_infos, args.threshold)
    
    if not groups:
        print("No similar images found.") # 没找到相似的，退出
        return
        
    # 调用函数处理找出的相似图片组
    handle_similar_groups(groups, target_dir, args.action)

# 这是一句 Python 的常用惯用法 (idiom)
# 它的意思是：如果这个脚本是作为主程序直接运行的（而不是被其他脚本 import 导入的），
# 那么就执行 main() 函数。这样写是个好习惯，也是程序规范的入口。
if __name__ == '__main__':
    main()
