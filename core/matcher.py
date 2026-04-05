from tqdm import tqdm # 用于在终端中显示进度条

def color_matrix_dist(mat1, mat2):
    """计算两个颜色矩阵的平均差异，转换为与 pHash 相似的距离尺度"""
    if not mat1 or not mat2 or len(mat1) != len(mat2):
        return 999
    # 将差异缩小，使其与 pHash 的汉明距离尺度相近
    return sum(abs(a - b) for a, b in zip(mat1, mat2)) / 80.0

def group_similar_images(image_infos, threshold):
    """
    根据相似度阈值将图片分组。
    哈希值之间的“汉明距离”越小，说明图片越相似。
    """
    groups = [] # 保存分组结果的列表，每个组是一个包含多张相似图片信息的列表
    processed = set() # 用一个集合来记录已经分配到某个组的图片的索引，避免重复处理

    # 遍历每一张图片。使用 tqdm 包装以显示进度条
    for i, info1 in enumerate(tqdm(image_infos, desc="Comparing hashes")):
        # 如果这张图片已经被分过组了，就跳过
        if i in processed:
            continue
            
        # 创建一个新的组，先把当前图片放进去
        current_group = [info1]
        processed.add(i) # 记录当前图片已处理

        # 拿当前图片和它后面的所有图片进行比较
        for j in range(i + 1, len(image_infos)):
            if j in processed:
                continue # 如果后面的某张图片已经分过组，也跳过
                
            info2 = image_infos[j]
            
            if info1.get('ai_vector') and info2.get('ai_vector'):
                # 【AI 深度学习引擎】
                sim = sum(a * b for a, b in zip(info1['ai_vector'], info2['ai_vector']))
                target_sim = 0.98 - (threshold * 0.0065)
                if sim >= target_sim:
                    current_group.append(info2)
                    processed.add(j)
            else:
                # 【传统视觉哈希强化引擎】
                dist_p = info1['hash_p'] - info2['hash_p']
                dist_d = info1['hash_d'] - info2['hash_d']
                dist_c = color_matrix_dist(info1['hash_c'], info2['hash_c'])
                
                if (min(dist_p, dist_d) <= threshold and dist_c <= (threshold + 5)) or ((dist_p + dist_c) <= (threshold * 1.5)):
                    current_group.append(info2)
                    processed.add(j)
                
        if len(current_group) > 1:
            groups.append(current_group)

    return groups # 返回所有相似图片的分组