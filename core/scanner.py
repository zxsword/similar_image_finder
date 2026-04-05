import os
import threading
import concurrent.futures
from core.cache import load_cache, save_cache, get_uncached_paths
from core.engine import get_image_info
from core.matcher import group_similar_images
from utils.file_ops import find_images

class ScannerWorker:
    """
    独立的扫描工作线程管理器 (后台苦力头子)。
    新手必读：如果把耗时的扫描直接写在界面代码里，界面会直接“无响应”卡死。
    所以我们用 Thread (线程) 在后台偷偷工作，用 ProcessPool (多进程池) 压榨电脑的多个CPU核心，
    最后通过 callbacks (回调函数) 安全地给界面发消息汇报进度。
    """
    def __init__(self, dir1, dir2, threshold, recursive, use_ai, callbacks):
        self.dir1, self.dir2, self.threshold = dir1, dir2, threshold
        self.recursive, self.use_ai, self.callbacks = recursive, use_ai, callbacks
        self.cancel_flag = False

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def cancel(self):
        self.cancel_flag = True

    def _run(self):
        try:
            self.callbacks['on_status']("正在扫描文件夹...")
            directories = [self.dir1]
            if self.dir2 and os.path.abspath(self.dir1) != os.path.abspath(self.dir2):
                directories.append(self.dir2)

            all_infos, tasks, total_calc = [], [], 0
            for d in directories:
                if self.cancel_flag: return self.callbacks['on_cancel']()
                paths = find_images(d, recursive=self.recursive)
                c_file = os.path.join(d, '.sim_image_cache.json')
                c_data = load_cache(c_file)
                needs, cached = get_uncached_paths(paths, c_data, use_ai=self.use_ai)
                
                all_infos.extend(cached); total_calc += len(needs)
                tasks.append({'needs': needs, 'c_data': c_data, 'c_file': c_file})
                
            if len(all_infos) + total_calc < 2: return self.callbacks['on_error']("选定范围图片数量不足。")

            if total_calc > 0:
                self.callbacks['on_status'](f"计算指纹中 (0/{total_calc})...")
                workers = max(1, (os.cpu_count() or 4) - 2)
                workers = min(workers, 2) if self.use_ai else min(workers, 6)
                completed = 0
                
                with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                    for t in tasks:
                        if not t['needs']: continue
                        futures = {executor.submit(get_image_info, p, self.use_ai): p for p in t['needs']}
                        for future in concurrent.futures.as_completed(futures):
                            if self.cancel_flag:
                                try: executor.shutdown(wait=False, cancel_futures=True)
                                except TypeError: executor.shutdown(wait=False)
                                return self.callbacks['on_cancel']()
                            
                            completed += 1; res = future.result()
                            if not res.get('error'):
                                all_infos.append(res)
                                entry = res.copy()
                                entry['hash_p'] = str(entry['hash_p']); entry['hash_d'] = str(entry['hash_d'])
                                t['c_data'][res['path']] = entry
                                
                            if completed % 5 == 0 or completed == total_calc:
                                self.callbacks['on_progress']((completed / total_calc) * 100, f"计算指纹中 ({completed}/{total_calc})...")
                        save_cache(t['c_file'], t['c_data'])
            else:
                self.callbacks['on_progress'](100, "所有图片已从缓存加载")
                        
            if self.cancel_flag: return self.callbacks['on_cancel']()
            self.callbacks['on_status']("正在分析和分组相似图片...")
            groups = group_similar_images(all_infos, self.threshold)
            self.callbacks['on_complete'](groups)
            
        except Exception as e:
            self.callbacks['on_error'](str(e))