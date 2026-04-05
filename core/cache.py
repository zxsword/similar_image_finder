import os
import json
import imagehash

def load_cache(cache_file):
    """从本地 JSON 文件读取哈希缓存。"""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cache(cache_file, cache_data):
    """将计算好的哈希结果保存到本地 JSON 缓存文件。"""
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Failed to save cache: {e}")

def get_uncached_paths(image_paths, cache_data, use_ai=False):
    """对比文件修改时间，分离出需要重新计算哈希的图片和可以直接使用缓存的图片。"""
    needs_calc = []
    cached_infos = []
    
    # 自动清理已经不存在（被移动或删除）的图片的缓存条目
    existing_paths = set(image_paths)
    stale_keys = [k for k in cache_data.keys() if k not in existing_paths]
    for k in stale_keys:
        del cache_data[k]
        
    for p in image_paths:
        try:
            mtime = os.path.getmtime(p)
            is_valid = p in cache_data and cache_data[p]['mtime'] == mtime and 'hash_c' in cache_data[p]
            if is_valid and not isinstance(cache_data[p]['hash_c'], list):
                is_valid = False
            if is_valid and use_ai and not cache_data[p].get('ai_vector'):
                is_valid = False
                
            if is_valid:
                info = cache_data[p].copy()
                info['hash_p'] = imagehash.hex_to_hash(info['hash_p'])
                info['hash_d'] = imagehash.hex_to_hash(info['hash_d'])
                cached_infos.append(info)
            else:
                needs_calc.append(p)
        except OSError:
            needs_calc.append(p)
            
    return needs_calc, cached_infos