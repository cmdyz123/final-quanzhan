"""
Food Recognition Module - 食物图像识别

Supports two modes:
- simulation: Uses color/feature heuristics with a built-in food database (no API needed)
- api: Calls a vision-capable LLM API for real food recognition
"""

import json
import os
from PIL import Image
import io


# Comprehensive food nutrition database (per 100g)
# Organized by category for easy maintenance
FOOD_DB = {
    # ===== 主食 / 粉面 / 早餐 =====
    '米饭': {'calories': 116, 'protein': 2.6, 'fat': 0.3, 'carbs': 25.9, 'fiber': 0.3},
    '糙米饭': {'calories': 123, 'protein': 2.7, 'fat': 0.9, 'carbs': 25.6, 'fiber': 3.3},
    '白粥': {'calories': 46, 'protein': 1.1, 'fat': 0.1, 'carbs': 9.8, 'fiber': 0.1},
    '小米粥': {'calories': 49, 'protein': 1.4, 'fat': 0.5, 'carbs': 9.5, 'fiber': 0.8},
    '皮蛋瘦肉粥': {'calories': 62, 'protein': 4.0, 'fat': 1.8, 'carbs': 8.0, 'fiber': 0.1},
    '面条': {'calories': 137, 'protein': 4.5, 'fat': 0.6, 'carbs': 28.5, 'fiber': 0.8},
    '汤面': {'calories': 110, 'protein': 3.5, 'fat': 2.0, 'carbs': 20.0, 'fiber': 0.5},
    '炒面': {'calories': 160, 'protein': 5.0, 'fat': 5.5, 'carbs': 23.0, 'fiber': 0.6},
    '河粉': {'calories': 125, 'protein': 3.0, 'fat': 2.0, 'carbs': 24.0, 'fiber': 0.5},
    '炒河粉': {'calories': 170, 'protein': 5.5, 'fat': 7.0, 'carbs': 22.0, 'fiber': 0.8},
    '米粉': {'calories': 120, 'protein': 2.5, 'fat': 0.8, 'carbs': 26.0, 'fiber': 0.3},
    # 肠粉家族
    '肠粉': {'calories': 110, 'protein': 3.0, 'fat': 1.5, 'carbs': 21.0, 'fiber': 0.3},
    '鸡蛋肠粉': {'calories': 130, 'protein': 5.0, 'fat': 3.5, 'carbs': 20.0, 'fiber': 0.3},
    '瘦肉肠粉': {'calories': 145, 'protein': 7.0, 'fat': 4.5, 'carbs': 20.0, 'fiber': 0.3},
    '牛肉肠粉': {'calories': 140, 'protein': 7.5, 'fat': 3.5, 'carbs': 20.5, 'fiber': 0.3},
    '叉烧肠粉': {'calories': 155, 'protein': 6.5, 'fat': 5.5, 'carbs': 21.0, 'fiber': 0.3},
    '鲜虾肠粉': {'calories': 125, 'protein': 6.5, 'fat': 2.0, 'carbs': 20.5, 'fiber': 0.3},
    '鸡蛋油条肠粉': {'calories': 175, 'protein': 6.0, 'fat': 7.0, 'carbs': 23.0, 'fiber': 0.5},
    '油条肠粉': {'calories': 165, 'protein': 4.5, 'fat': 6.5, 'carbs': 23.0, 'fiber': 0.5},
    # 其他早餐
    '油条': {'calories': 386, 'protein': 6.9, 'fat': 17.6, 'carbs': 50.1, 'fiber': 0.9},
    '豆浆': {'calories': 31, 'protein': 2.4, 'fat': 1.0, 'carbs': 2.0, 'fiber': 0.1},
    '豆腐脑': {'calories': 47, 'protein': 3.0, 'fat': 1.5, 'carbs': 5.5, 'fiber': 0.2},
    '煎饼果子': {'calories': 220, 'protein': 8.0, 'fat': 8.0, 'carbs': 30.0, 'fiber': 1.0},
    '小笼包': {'calories': 230, 'protein': 9.0, 'fat': 10.0, 'carbs': 27.0, 'fiber': 0.8},
    '生煎包': {'calories': 250, 'protein': 9.0, 'fat': 12.0, 'carbs': 28.0, 'fiber': 0.8},
    '烧麦': {'calories': 180, 'protein': 6.0, 'fat': 6.0, 'carbs': 26.0, 'fiber': 0.5},
    '虾饺': {'calories': 115, 'protein': 6.0, 'fat': 3.5, 'carbs': 15.0, 'fiber': 0.3},
    '凤爪': {'calories': 175, 'protein': 12.0, 'fat': 11.0, 'carbs': 7.0, 'fiber': 0},
    '糯米鸡': {'calories': 185, 'protein': 7.0, 'fat': 8.0, 'carbs': 22.0, 'fiber': 0.8},
    '叉烧包': {'calories': 260, 'protein': 8.0, 'fat': 8.0, 'carbs': 40.0, 'fiber': 0.8},
    '奶黄包': {'calories': 280, 'protein': 6.5, 'fat': 9.0, 'carbs': 44.0, 'fiber': 0.5},
    '馒头': {'calories': 223, 'protein': 7.0, 'fat': 1.1, 'carbs': 44.2, 'fiber': 1.3},
    '花卷': {'calories': 214, 'protein': 6.4, 'fat': 1.5, 'carbs': 44.0, 'fiber': 1.2},
    '面包': {'calories': 266, 'protein': 8.8, 'fat': 3.4, 'carbs': 49.0, 'fiber': 2.7},
    '全麦面包': {'calories': 246, 'protein': 9.0, 'fat': 2.8, 'carbs': 44.0, 'fiber': 6.0},
    '吐司': {'calories': 280, 'protein': 8.5, 'fat': 5.0, 'carbs': 50.0, 'fiber': 2.2},
    # 粗粮
    '红薯': {'calories': 86, 'protein': 1.6, 'fat': 0.1, 'carbs': 20.1, 'fiber': 3.0},
    '紫薯': {'calories': 82, 'protein': 1.8, 'fat': 0.1, 'carbs': 18.5, 'fiber': 3.5},
    '山药': {'calories': 57, 'protein': 1.5, 'fat': 0.1, 'carbs': 13.0, 'fiber': 1.9},

    # ===== 肉类 / 蛋白质 =====
    '鸡蛋': {'calories': 144, 'protein': 13.3, 'fat': 8.8, 'carbs': 2.8, 'fiber': 0},
    '水煮蛋': {'calories': 151, 'protein': 12.5, 'fat': 10.5, 'carbs': 1.0, 'fiber': 0},
    '煎蛋': {'calories': 196, 'protein': 12.0, 'fat': 16.0, 'carbs': 1.5, 'fiber': 0},
    '炒蛋': {'calories': 170, 'protein': 11.5, 'fat': 13.0, 'carbs': 2.5, 'fiber': 0},
    '鸡胸肉': {'calories': 133, 'protein': 31.0, 'fat': 1.2, 'carbs': 0, 'fiber': 0},
    '鸡腿': {'calories': 181, 'protein': 20.0, 'fat': 11.0, 'carbs': 0, 'fiber': 0},
    '鸡翅': {'calories': 194, 'protein': 18.0, 'fat': 13.0, 'carbs': 0, 'fiber': 0},
    '鸡排': {'calories': 260, 'protein': 20.0, 'fat': 18.0, 'carbs': 8.0, 'fiber': 0},
    '猪肉': {'calories': 395, 'protein': 13.2, 'fat': 37.0, 'carbs': 2.4, 'fiber': 0},
    '瘦肉': {'calories': 143, 'protein': 20.3, 'fat': 6.2, 'carbs': 1.5, 'fiber': 0},
    '猪排骨': {'calories': 264, 'protein': 18.0, 'fat': 20.0, 'carbs': 1.0, 'fiber': 0},
    '猪蹄': {'calories': 260, 'protein': 22.0, 'fat': 18.0, 'carbs': 2.0, 'fiber': 0},
    '猪肝': {'calories': 129, 'protein': 19.3, 'fat': 3.5, 'carbs': 5.0, 'fiber': 0},
    '牛肉': {'calories': 125, 'protein': 20.2, 'fat': 4.2, 'carbs': 0.2, 'fiber': 0},
    '牛腩': {'calories': 175, 'protein': 18.0, 'fat': 11.0, 'carbs': 0, 'fiber': 0},
    '牛排': {'calories': 155, 'protein': 22.0, 'fat': 7.0, 'carbs': 0, 'fiber': 0},
    '肥牛': {'calories': 325, 'protein': 16.0, 'fat': 28.0, 'carbs': 0, 'fiber': 0},
    '羊肉': {'calories': 203, 'protein': 19.0, 'fat': 14.1, 'carbs': 0, 'fiber': 0},
    '羊排': {'calories': 240, 'protein': 18.0, 'fat': 18.0, 'carbs': 0, 'fiber': 0},

    # ===== 水产 / 海鲜 =====
    '三文鱼': {'calories': 208, 'protein': 20.4, 'fat': 13.4, 'carbs': 0, 'fiber': 0},
    '虾': {'calories': 99, 'protein': 20.0, 'fat': 1.4, 'carbs': 0, 'fiber': 0},
    '虾仁': {'calories': 87, 'protein': 18.0, 'fat': 0.8, 'carbs': 1.0, 'fiber': 0},
    '鱼片': {'calories': 110, 'protein': 19.0, 'fat': 3.5, 'carbs': 0, 'fiber': 0},
    '带鱼': {'calories': 127, 'protein': 18.0, 'fat': 5.5, 'carbs': 0, 'fiber': 0},
    '鲈鱼': {'calories': 105, 'protein': 18.6, 'fat': 3.4, 'carbs': 0, 'fiber': 0},
    '鱿鱼': {'calories': 92, 'protein': 17.0, 'fat': 1.8, 'carbs': 2.0, 'fiber': 0},
    '螃蟹': {'calories': 95, 'protein': 13.8, 'fat': 2.3, 'carbs': 4.7, 'fiber': 0},
    '花甲': {'calories': 75, 'protein': 11.0, 'fat': 1.5, 'carbs': 4.0, 'fiber': 0},
    '生蚝': {'calories': 73, 'protein': 8.0, 'fat': 2.5, 'carbs': 5.0, 'fiber': 0},

    # ===== 豆制品 / 素菜 =====
    '豆腐': {'calories': 76, 'protein': 8.1, 'fat': 3.7, 'carbs': 4.2, 'fiber': 0.4},
    '嫩豆腐': {'calories': 55, 'protein': 5.5, 'fat': 2.5, 'carbs': 3.0, 'fiber': 0.3},
    '老豆腐': {'calories': 76, 'protein': 8.1, 'fat': 3.7, 'carbs': 4.2, 'fiber': 0.4},
    '豆腐干': {'calories': 140, 'protein': 16.0, 'fat': 8.0, 'carbs': 2.0, 'fiber': 0.5},
    '豆腐皮': {'calories': 409, 'protein': 44.6, 'fat': 17.4, 'carbs': 18.6, 'fiber': 0.5},
    '腐竹': {'calories': 459, 'protein': 44.6, 'fat': 21.7, 'carbs': 22.3, 'fiber': 1.0},
    '豆芽': {'calories': 18, 'protein': 2.0, 'fat': 0.1, 'carbs': 3.0, 'fiber': 1.6},
    '毛豆': {'calories': 131, 'protein': 13.0, 'fat': 6.0, 'carbs': 10.0, 'fiber': 4.0},
    '面筋': {'calories': 142, 'protein': 26.0, 'fat': 0.5, 'carbs': 8.5, 'fiber': 0.5},

    # ===== 蔬菜 =====
    '西兰花': {'calories': 34, 'protein': 2.8, 'fat': 0.4, 'carbs': 6.6, 'fiber': 2.6},
    '菠菜': {'calories': 23, 'protein': 2.9, 'fat': 0.4, 'carbs': 3.6, 'fiber': 2.2},
    '生菜': {'calories': 15, 'protein': 1.4, 'fat': 0.1, 'carbs': 2.8, 'fiber': 1.3},
    '白菜': {'calories': 13, 'protein': 1.5, 'fat': 0.2, 'carbs': 2.2, 'fiber': 1.0},
    '娃娃菜': {'calories': 13, 'protein': 1.2, 'fat': 0.1, 'carbs': 2.3, 'fiber': 1.0},
    '空心菜': {'calories': 20, 'protein': 2.2, 'fat': 0.3, 'carbs': 3.1, 'fiber': 2.0},
    '油麦菜': {'calories': 16, 'protein': 1.5, 'fat': 0.2, 'carbs': 2.5, 'fiber': 1.5},
    '番茄': {'calories': 18, 'protein': 0.9, 'fat': 0.2, 'carbs': 3.9, 'fiber': 1.2},
    '黄瓜': {'calories': 16, 'protein': 0.7, 'fat': 0.1, 'carbs': 2.9, 'fiber': 0.5},
    '胡萝卜': {'calories': 41, 'protein': 0.9, 'fat': 0.2, 'carbs': 9.6, 'fiber': 2.8},
    '白萝卜': {'calories': 21, 'protein': 0.9, 'fat': 0.1, 'carbs': 4.5, 'fiber': 1.6},
    '土豆': {'calories': 77, 'protein': 2.0, 'fat': 0.1, 'carbs': 17.5, 'fiber': 2.2},
    '茄子': {'calories': 23, 'protein': 1.1, 'fat': 0.2, 'carbs': 4.9, 'fiber': 3.0},
    '青椒': {'calories': 22, 'protein': 1.0, 'fat': 0.2, 'carbs': 4.6, 'fiber': 1.7},
    '洋葱': {'calories': 40, 'protein': 1.1, 'fat': 0.1, 'carbs': 9.1, 'fiber': 1.7},
    '芹菜': {'calories': 16, 'protein': 0.8, 'fat': 0.1, 'carbs': 3.3, 'fiber': 1.6},
    '韭菜': {'calories': 26, 'protein': 2.4, 'fat': 0.4, 'carbs': 3.8, 'fiber': 1.4},
    '秋葵': {'calories': 33, 'protein': 1.9, 'fat': 0.2, 'carbs': 7.5, 'fiber': 3.2},
    '莲藕': {'calories': 73, 'protein': 2.0, 'fat': 0.1, 'carbs': 16.4, 'fiber': 2.6},
    '冬瓜': {'calories': 12, 'protein': 0.4, 'fat': 0.2, 'carbs': 2.6, 'fiber': 0.8},
    '南瓜': {'calories': 23, 'protein': 0.7, 'fat': 0.1, 'carbs': 5.3, 'fiber': 0.8},
    '苦瓜': {'calories': 19, 'protein': 0.8, 'fat': 0.1, 'carbs': 3.5, 'fiber': 1.4},
    '玉米': {'calories': 112, 'protein': 4.0, 'fat': 1.2, 'carbs': 22.8, 'fiber': 2.9},
    '香菇': {'calories': 26, 'protein': 2.2, 'fat': 0.3, 'carbs': 5.2, 'fiber': 3.3},
    '金针菇': {'calories': 26, 'protein': 2.4, 'fat': 0.4, 'carbs': 4.1, 'fiber': 2.7},
    '木耳': {'calories': 27, 'protein': 1.5, 'fat': 0.2, 'carbs': 6.0, 'fiber': 2.9},
    '海带': {'calories': 13, 'protein': 1.1, 'fat': 0.1, 'carbs': 2.1, 'fiber': 1.0},

    # ===== 中式热菜 =====
    '炒青菜': {'calories': 45, 'protein': 2.0, 'fat': 3.0, 'carbs': 3.0, 'fiber': 1.8},
    '蒜蓉西兰花': {'calories': 50, 'protein': 3.0, 'fat': 3.5, 'carbs': 5.0, 'fiber': 2.5},
    '红烧肉': {'calories': 305, 'protein': 8.0, 'fat': 28.0, 'carbs': 5.0, 'fiber': 0},
    '红烧排骨': {'calories': 280, 'protein': 16.0, 'fat': 20.0, 'carbs': 8.0, 'fiber': 0},
    '红烧牛肉': {'calories': 160, 'protein': 22.0, 'fat': 6.0, 'carbs': 5.0, 'fiber': 0.5},
    '红烧鱼': {'calories': 155, 'protein': 18.0, 'fat': 7.0, 'carbs': 5.0, 'fiber': 0},
    '宫保鸡丁': {'calories': 185, 'protein': 18.0, 'fat': 10.0, 'carbs': 8.0, 'fiber': 1.0},
    '鱼香肉丝': {'calories': 170, 'protein': 12.0, 'fat': 10.0, 'carbs': 10.0, 'fiber': 1.0},
    '回锅肉': {'calories': 290, 'protein': 14.0, 'fat': 23.0, 'carbs': 6.0, 'fiber': 0.5},
    '糖醋里脊': {'calories': 250, 'protein': 14.0, 'fat': 12.0, 'carbs': 22.0, 'fiber': 0},
    '麻婆豆腐': {'calories': 120, 'protein': 10.0, 'fat': 7.5, 'carbs': 5.0, 'fiber': 0.5},
    '西红柿炒鸡蛋': {'calories': 85, 'protein': 6.0, 'fat': 5.0, 'carbs': 5.0, 'fiber': 0.8},
    '番茄炒蛋': {'calories': 85, 'protein': 6.0, 'fat': 5.0, 'carbs': 5.0, 'fiber': 0.8},  # alias
    '酸辣土豆丝': {'calories': 95, 'protein': 2.0, 'fat': 5.0, 'carbs': 13.0, 'fiber': 1.5},
    '地三鲜': {'calories': 110, 'protein': 2.5, 'fat': 6.0, 'carbs': 14.0, 'fiber': 2.0},
    '干煸四季豆': {'calories': 120, 'protein': 3.0, 'fat': 8.0, 'carbs': 10.0, 'fiber': 2.5},
    '小炒肉': {'calories': 210, 'protein': 16.0, 'fat': 14.0, 'carbs': 4.0, 'fiber': 0.5},
    '黄焖鸡': {'calories': 170, 'protein': 18.0, 'fat': 8.0, 'carbs': 7.0, 'fiber': 0.5},
    '可乐鸡翅': {'calories': 220, 'protein': 17.0, 'fat': 12.0, 'carbs': 12.0, 'fiber': 0},
    '清蒸鱼': {'calories': 105, 'protein': 18.0, 'fat': 3.0, 'carbs': 1.0, 'fiber': 0},
    '剁椒鱼头': {'calories': 130, 'protein': 16.0, 'fat': 5.0, 'carbs': 4.0, 'fiber': 0.3},
    '水煮鱼': {'calories': 160, 'protein': 17.0, 'fat': 9.0, 'carbs': 3.0, 'fiber': 0.3},
    '水煮牛肉': {'calories': 185, 'protein': 20.0, 'fat': 10.0, 'carbs': 4.0, 'fiber': 0.5},
    '酸菜鱼': {'calories': 135, 'protein': 16.0, 'fat': 5.5, 'carbs': 5.0, 'fiber': 0.5},
    '口水鸡': {'calories': 195, 'protein': 20.0, 'fat': 12.0, 'carbs': 2.0, 'fiber': 0},
    '白切鸡': {'calories': 160, 'protein': 22.0, 'fat': 7.0, 'carbs': 1.0, 'fiber': 0},
    '盐焗鸡': {'calories': 150, 'protein': 24.0, 'fat': 5.0, 'carbs': 2.0, 'fiber': 0},
    '手撕鸡': {'calories': 170, 'protein': 23.0, 'fat': 8.0, 'carbs': 1.0, 'fiber': 0},
    '烧鸭': {'calories': 280, 'protein': 18.0, 'fat': 22.0, 'carbs': 2.0, 'fiber': 0},
    '烧鹅': {'calories': 305, 'protein': 20.0, 'fat': 24.0, 'carbs': 2.0, 'fiber': 0},
    '叉烧': {'calories': 260, 'protein': 20.0, 'fat': 16.0, 'carbs': 10.0, 'fiber': 0},
    '烤鸭': {'calories': 240, 'protein': 14.0, 'fat': 20.0, 'carbs': 0, 'fiber': 0},
    '蒸排骨': {'calories': 200, 'protein': 18.0, 'fat': 13.0, 'carbs': 3.0, 'fiber': 0},
    '粉蒸肉': {'calories': 320, 'protein': 10.0, 'fat': 25.0, 'carbs': 15.0, 'fiber': 0.5},
    '梅菜扣肉': {'calories': 350, 'protein': 8.0, 'fat': 30.0, 'carbs': 10.0, 'fiber': 0.8},
    '东坡肉': {'calories': 370, 'protein': 10.0, 'fat': 33.0, 'carbs': 6.0, 'fiber': 0},

    # ===== 汤品 =====
    '紫菜蛋花汤': {'calories': 30, 'protein': 2.5, 'fat': 1.0, 'carbs': 3.0, 'fiber': 0.3},
    '番茄蛋汤': {'calories': 25, 'protein': 1.5, 'fat': 1.0, 'carbs': 3.0, 'fiber': 0.5},
    '排骨汤': {'calories': 80, 'protein': 6.0, 'fat': 5.5, 'carbs': 2.0, 'fiber': 0},
    '鸡汤': {'calories': 55, 'protein': 5.0, 'fat': 3.5, 'carbs': 1.5, 'fiber': 0},
    '酸辣汤': {'calories': 40, 'protein': 2.5, 'fat': 1.5, 'carbs': 5.0, 'fiber': 0.3},
    '豆腐汤': {'calories': 35, 'protein': 2.5, 'fat': 1.5, 'carbs': 3.0, 'fiber': 0.3},
    '冬瓜汤': {'calories': 20, 'protein': 0.5, 'fat': 0.5, 'carbs': 3.5, 'fiber': 0.5},

    # ===== 煲仔饭 / 盖饭 / 炒饭 =====
    '煲仔饭': {'calories': 185, 'protein': 7.0, 'fat': 6.0, 'carbs': 26.0, 'fiber': 0.5},
    '腊味煲仔饭': {'calories': 210, 'protein': 8.5, 'fat': 9.0, 'carbs': 25.0, 'fiber': 0.5},
    '排骨煲仔饭': {'calories': 195, 'protein': 8.0, 'fat': 7.0, 'carbs': 26.0, 'fiber': 0.5},
    '滑蛋牛肉饭': {'calories': 175, 'protein': 12.0, 'fat': 6.0, 'carbs': 20.0, 'fiber': 0.3},
    '咖喱鸡肉饭': {'calories': 180, 'protein': 12.0, 'fat': 7.0, 'carbs': 18.0, 'fiber': 0.8},
    '卤肉饭': {'calories': 220, 'protein': 8.5, 'fat': 14.0, 'carbs': 17.0, 'fiber': 0.3},
    '蛋炒饭': {'calories': 170, 'protein': 6.0, 'fat': 6.0, 'carbs': 24.0, 'fiber': 0.3},
    '扬州炒饭': {'calories': 190, 'protein': 7.5, 'fat': 7.0, 'carbs': 25.0, 'fiber': 0.5},

	    # 常见盖饭/套餐
	    '猪脚饭': {'calories': 280, 'protein': 16.0, 'fat': 18.0, 'carbs': 20.0, 'fiber': 0.3},
	    '猪蹄饭': {'calories': 275, 'protein': 15.5, 'fat': 17.5, 'carbs': 20.0, 'fiber': 0.3},
	    '鸡腿饭': {'calories': 260, 'protein': 18.0, 'fat': 12.0, 'carbs': 22.0, 'fiber': 0.5},
	    '白切鸡饭': {'calories': 240, 'protein': 20.0, 'fat': 10.0, 'carbs': 20.0, 'fiber': 0.5},
	    '叉烧饭': {'calories': 280, 'protein': 18.0, 'fat': 14.0, 'carbs': 22.0, 'fiber': 0.3},
	    '烤鸭饭': {'calories': 270, 'protein': 16.0, 'fat': 15.0, 'carbs': 20.0, 'fiber': 0.3},
	    '烧鸭饭': {'calories': 275, 'protein': 17.0, 'fat': 16.0, 'carbs': 20.0, 'fiber': 0.3},
	    '烧鹅饭': {'calories': 290, 'protein': 18.0, 'fat': 17.0, 'carbs': 20.0, 'fiber': 0.3},
	    '豉油鸡饭': {'calories': 250, 'protein': 19.0, 'fat': 11.0, 'carbs': 21.0, 'fiber': 0.3},
	    '扣肉饭': {'calories': 320, 'protein': 12.0, 'fat': 24.0, 'carbs': 16.0, 'fiber': 0.3},
	    '卤鸡腿饭': {'calories': 255, 'protein': 19.0, 'fat': 11.5, 'carbs': 21.0, 'fiber': 0.3},
	    '卤蛋': {'calories': 75, 'protein': 6.5, 'fat': 5.0, 'carbs': 1.0, 'fiber': 0},
	    '酸菜': {'calories': 18, 'protein': 1.0, 'fat': 0.2, 'carbs': 3.5, 'fiber': 1.5},

    # ===== 麻辣烫 / 冒菜 / 火锅 / 干锅 =====
    '火锅': {'calories': 350, 'protein': 25.0, 'fat': 25.0, 'carbs': 10.0, 'fiber': 2.0},
    '麻辣烫': {'calories': 200, 'protein': 12.0, 'fat': 12.0, 'carbs': 14.0, 'fiber': 2.5},
    '冒菜': {'calories': 220, 'protein': 14.0, 'fat': 14.0, 'carbs': 12.0, 'fiber': 2.0},
    '干锅': {'calories': 240, 'protein': 15.0, 'fat': 16.0, 'carbs': 10.0, 'fiber': 1.5},
    '麻辣香锅': {'calories': 250, 'protein': 16.0, 'fat': 17.0, 'carbs': 10.0, 'fiber': 1.5},

    # ===== 烧烤 / 油炸 =====
    '烧烤': {'calories': 280, 'protein': 18.0, 'fat': 20.0, 'carbs': 8.0, 'fiber': 0.5},
    '烤串': {'calories': 250, 'protein': 16.0, 'fat': 18.0, 'carbs': 6.0, 'fiber': 0.3},
    '羊肉串': {'calories': 220, 'protein': 20.0, 'fat': 15.0, 'carbs': 2.0, 'fiber': 0},
    '炸鸡': {'calories': 245, 'protein': 18.0, 'fat': 15.0, 'carbs': 10.0, 'fiber': 0},
    '炸鸡腿': {'calories': 260, 'protein': 18.0, 'fat': 16.0, 'carbs': 12.0, 'fiber': 0},
    '炸鸡排': {'calories': 280, 'protein': 17.0, 'fat': 18.0, 'carbs': 14.0, 'fiber': 0},
    '薯条': {'calories': 312, 'protein': 3.4, 'fat': 15.0, 'carbs': 41.0, 'fiber': 3.8},

    # ===== 饺子 / 馄饨 / 包子 =====
    '饺子': {'calories': 240, 'protein': 9.0, 'fat': 8.0, 'carbs': 33.0, 'fiber': 1.5},
    '水饺': {'calories': 220, 'protein': 8.5, 'fat': 6.0, 'carbs': 32.0, 'fiber': 1.2},
    '煎饺': {'calories': 270, 'protein': 9.0, 'fat': 12.0, 'carbs': 33.0, 'fiber': 1.3},
    '馄饨': {'calories': 180, 'protein': 7.0, 'fat': 5.0, 'carbs': 27.0, 'fiber': 0.8},
    '包子': {'calories': 230, 'protein': 8.0, 'fat': 6.0, 'carbs': 35.0, 'fiber': 1.2},
    '肉包': {'calories': 245, 'protein': 9.0, 'fat': 8.0, 'carbs': 34.0, 'fiber': 1.0},
    '菜包': {'calories': 200, 'protein': 6.0, 'fat': 4.0, 'carbs': 36.0, 'fiber': 1.8},

    # ===== 日韩料理 =====
    '寿司': {'calories': 145, 'protein': 5.0, 'fat': 1.0, 'carbs': 28.0, 'fiber': 0.5},
    '刺身': {'calories': 120, 'protein': 22.0, 'fat': 3.0, 'carbs': 0, 'fiber': 0},
    '天妇罗': {'calories': 230, 'protein': 5.0, 'fat': 14.0, 'carbs': 22.0, 'fiber': 1.0},
    '拉面': {'calories': 160, 'protein': 7.0, 'fat': 4.0, 'carbs': 25.0, 'fiber': 0.5},
    '乌冬面': {'calories': 130, 'protein': 4.0, 'fat': 0.5, 'carbs': 28.0, 'fiber': 0.8},
    '石锅拌饭': {'calories': 170, 'protein': 7.0, 'fat': 5.5, 'carbs': 24.0, 'fiber': 1.5},
    '泡菜': {'calories': 24, 'protein': 1.0, 'fat': 0.2, 'carbs': 4.6, 'fiber': 1.6},
    '炸酱面': {'calories': 175, 'protein': 7.0, 'fat': 6.0, 'carbs': 24.0, 'fiber': 0.8},

    # ===== 西式快餐 =====
    '披萨': {'calories': 266, 'protein': 11.0, 'fat': 10.0, 'carbs': 33.0, 'fiber': 1.5},
    '汉堡': {'calories': 295, 'protein': 17.0, 'fat': 14.0, 'carbs': 24.0, 'fiber': 1.0},
    '热狗': {'calories': 280, 'protein': 10.0, 'fat': 17.0, 'carbs': 22.0, 'fiber': 0.8},
    '三明治': {'calories': 230, 'protein': 12.0, 'fat': 8.0, 'carbs': 28.0, 'fiber': 2.0},
    '意大利面': {'calories': 160, 'protein': 5.5, 'fat': 3.5, 'carbs': 28.0, 'fiber': 1.8},
    '牛排': {'calories': 155, 'protein': 22.0, 'fat': 7.0, 'carbs': 0, 'fiber': 0},
    '沙拉': {'calories': 30, 'protein': 1.5, 'fat': 0.5, 'carbs': 5.0, 'fiber': 2.0},
    '凯撒沙拉': {'calories': 95, 'protein': 6.0, 'fat': 6.5, 'carbs': 4.0, 'fiber': 1.5},

    # ===== 水果 =====
    '苹果': {'calories': 52, 'protein': 0.3, 'fat': 0.2, 'carbs': 13.8, 'fiber': 2.4},
    '香蕉': {'calories': 89, 'protein': 1.1, 'fat': 0.3, 'carbs': 22.8, 'fiber': 2.6},
    '橙子': {'calories': 47, 'protein': 0.9, 'fat': 0.1, 'carbs': 11.8, 'fiber': 2.4},
    '橘子': {'calories': 44, 'protein': 0.8, 'fat': 0.1, 'carbs': 10.5, 'fiber': 1.9},
    '葡萄': {'calories': 69, 'protein': 0.7, 'fat': 0.2, 'carbs': 18.1, 'fiber': 0.9},
    '西瓜': {'calories': 31, 'protein': 0.5, 'fat': 0.1, 'carbs': 6.8, 'fiber': 0.3},
    '草莓': {'calories': 32, 'protein': 0.7, 'fat': 0.3, 'carbs': 7.1, 'fiber': 2.0},
    '芒果': {'calories': 60, 'protein': 0.8, 'fat': 0.4, 'carbs': 15.0, 'fiber': 1.6},
    '猕猴桃': {'calories': 61, 'protein': 1.1, 'fat': 0.5, 'carbs': 14.7, 'fiber': 3.0},
    '火龙果': {'calories': 55, 'protein': 1.1, 'fat': 0.4, 'carbs': 13.0, 'fiber': 2.0},
    '梨': {'calories': 51, 'protein': 0.4, 'fat': 0.1, 'carbs': 13.1, 'fiber': 3.1},
    '桃子': {'calories': 48, 'protein': 0.9, 'fat': 0.1, 'carbs': 12.2, 'fiber': 1.5},
    '樱桃': {'calories': 50, 'protein': 1.0, 'fat': 0.3, 'carbs': 12.0, 'fiber': 2.1},
    '蓝莓': {'calories': 57, 'protein': 0.7, 'fat': 0.3, 'carbs': 14.5, 'fiber': 2.4},
    '菠萝': {'calories': 44, 'protein': 0.5, 'fat': 0.1, 'carbs': 10.8, 'fiber': 1.4},
    '哈密瓜': {'calories': 34, 'protein': 0.5, 'fat': 0.1, 'carbs': 8.2, 'fiber': 0.9},
    '榴莲': {'calories': 147, 'protein': 1.5, 'fat': 5.3, 'carbs': 27.1, 'fiber': 3.8},
    '牛油果': {'calories': 160, 'protein': 2.0, 'fat': 14.7, 'carbs': 8.5, 'fiber': 6.7},

    # ===== 饮品 =====
    '牛奶': {'calories': 61, 'protein': 3.0, 'fat': 3.2, 'carbs': 4.8, 'fiber': 0},
    '脱脂牛奶': {'calories': 34, 'protein': 3.1, 'fat': 0.2, 'carbs': 4.9, 'fiber': 0},
    '酸奶': {'calories': 72, 'protein': 2.5, 'fat': 2.7, 'carbs': 9.3, 'fiber': 0},
    '奶酪': {'calories': 328, 'protein': 25.0, 'fat': 25.0, 'carbs': 1.3, 'fiber': 0},
    '咖啡': {'calories': 2, 'protein': 0.1, 'fat': 0, 'carbs': 0.3, 'fiber': 0},
    '拿铁': {'calories': 46, 'protein': 2.5, 'fat': 2.5, 'carbs': 3.5, 'fiber': 0},
    '卡布奇诺': {'calories': 38, 'protein': 2.0, 'fat': 2.0, 'carbs': 3.0, 'fiber': 0},
    '美式咖啡': {'calories': 3, 'protein': 0.1, 'fat': 0, 'carbs': 0.5, 'fiber': 0},
    '奶茶': {'calories': 80, 'protein': 1.5, 'fat': 3.0, 'carbs': 13.0, 'fiber': 0},
    '珍珠奶茶': {'calories': 100, 'protein': 1.5, 'fat': 3.5, 'carbs': 18.0, 'fiber': 0},
    '柠檬茶': {'calories': 35, 'protein': 0.1, 'fat': 0, 'carbs': 9.0, 'fiber': 0},
    '可乐': {'calories': 42, 'protein': 0, 'fat': 0, 'carbs': 10.6, 'fiber': 0},
    '雪碧': {'calories': 41, 'protein': 0, 'fat': 0, 'carbs': 10.2, 'fiber': 0},
    '橙汁': {'calories': 45, 'protein': 0.7, 'fat': 0.2, 'carbs': 10.4, 'fiber': 0.2},
    '苹果汁': {'calories': 46, 'protein': 0.1, 'fat': 0.1, 'carbs': 11.3, 'fiber': 0.2},
    '啤酒': {'calories': 43, 'protein': 0.5, 'fat': 0, 'carbs': 3.6, 'fiber': 0},
    '红酒': {'calories': 85, 'protein': 0.1, 'fat': 0, 'carbs': 2.6, 'fiber': 0},

    # ===== 甜品 / 零食 =====
    '蛋糕': {'calories': 347, 'protein': 4.0, 'fat': 18.0, 'carbs': 45.0, 'fiber': 0.5},
    '冰淇淋': {'calories': 207, 'protein': 3.5, 'fat': 13.0, 'carbs': 24.0, 'fiber': 0},
    '巧克力': {'calories': 546, 'protein': 4.9, 'fat': 31.0, 'carbs': 60.0, 'fiber': 2.5},
    '饼干': {'calories': 433, 'protein': 6.5, 'fat': 14.0, 'carbs': 71.0, 'fiber': 1.5},
    '薯片': {'calories': 536, 'protein': 5.0, 'fat': 35.0, 'carbs': 53.0, 'fiber': 3.0},
    '坚果': {'calories': 607, 'protein': 20.0, 'fat': 54.0, 'carbs': 16.0, 'fiber': 8.0},
    '花生': {'calories': 567, 'protein': 25.8, 'fat': 49.0, 'carbs': 16.0, 'fiber': 8.5},
    '杏仁': {'calories': 579, 'protein': 21.0, 'fat': 50.0, 'carbs': 20.0, 'fiber': 12.5},
    '核桃': {'calories': 654, 'protein': 15.0, 'fat': 65.0, 'carbs': 14.0, 'fiber': 6.7},
    '瓜子': {'calories': 582, 'protein': 23.0, 'fat': 50.0, 'carbs': 18.0, 'fiber': 8.0},
    '蛋挞': {'calories': 330, 'protein': 5.5, 'fat': 19.0, 'carbs': 35.0, 'fiber': 0.5},
    '双皮奶': {'calories': 95, 'protein': 4.0, 'fat': 5.0, 'carbs': 10.0, 'fiber': 0},
    '布丁': {'calories': 120, 'protein': 3.5, 'fat': 4.5, 'carbs': 18.0, 'fiber': 0},
}

# Color-based food category heuristics for simulation mode
COLOR_FOOD_MAP = {
    'white_grain': ['米饭', '面条', '馒头', '面包'],
    'white_protein': ['鸡胸肉', '豆腐', '鸡蛋'],
    'brown_red_meat': ['牛肉', '猪肉', '红烧肉', '羊肉'],
    'green_veg': ['西兰花', '菠菜', '炒青菜', '黄瓜', '沙拉'],
    'red_veg': ['番茄', '胡萝卜'],
    'yellow_fruit': ['香蕉', '玉米', '橙子'],
    'red_fruit': ['苹果', '葡萄'],
    'orange_mixed': ['宫保鸡丁', '西红柿炒鸡蛋', '炸鸡'],
    'dark_mixed': ['饺子', '包子', '汉堡', '披萨'],
    'white_dairy': ['牛奶', '酸奶', '奶酪'],
}


class FoodRecognizer:
    """Food image recognition engine"""

    def __init__(self, mode='simulation', api_key=None, api_base=None, model=None):
        self.mode = mode
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.food_db = FOOD_DB

    def recognize(self, image_path):
        """Main recognition method - returns list of food items with confidence and portion"""
        if self.mode == 'api':
            return self._recognize_api(image_path)
        else:
            return self._recognize_simulation(image_path)

    def _recognize_simulation(self, image_path):
        """
        Simulation mode: Uses image color analysis + heuristics to guess food items.
        In a real deployment, this would be replaced with a trained CV model.
        For demo purposes, this provides reasonable mock results.
        """
        try:
            img = Image.open(image_path)
            img = img.convert('RGB')
            img = img.resize((300, 300))

            pixels = list(img.getdata())
            total = len(pixels)

            # Analyze color distribution
            r_sum = sum(p[0] for p in pixels) / total
            g_sum = sum(p[1] for p in pixels) / total
            b_sum = sum(p[2] for p in pixels) / total

            # Determine brightness and color bias
            brightness = (r_sum + g_sum + b_sum) / 3

            results = []

            # Heuristic color-based food recognition
            if g_sum > r_sum and g_sum > b_sum and g_sum > 120:
                # Green dominant - likely vegetables
                results.append({
                    'name': '西兰花',
                    'name_en': 'Broccoli',
                    'confidence': 0.78,
                    'portion_g': 150,
                    'nutrition': dict(self.food_db.get('西兰花', {}))
                })
                results.append({
                    'name': '菠菜',
                    'name_en': 'Spinach',
                    'confidence': 0.65,
                    'portion_g': 100,
                    'nutrition': dict(self.food_db.get('菠菜', {}))
                })

            elif r_sum > g_sum and r_sum > b_sum and r_sum > 160:
                # Red/orange dominant - likely meat or tomato dishes
                if brightness > 150:
                    results.append({
                        'name': '西红柿炒鸡蛋',
                        'name_en': 'Tomato Egg Stir-fry',
                        'confidence': 0.72,
                        'portion_g': 200,
                        'nutrition': dict(self.food_db.get('西红柿炒鸡蛋', {}))
                    })
                else:
                    results.append({
                        'name': '红烧肉',
                        'name_en': 'Braised Pork',
                        'confidence': 0.70,
                        'portion_g': 180,
                        'nutrition': dict(self.food_db.get('红烧肉', {}))
                    })

            elif brightness > 180:
                # Very bright - likely rice, bread, dairy
                results.append({
                    'name': '米饭',
                    'name_en': 'Rice',
                    'confidence': 0.82,
                    'portion_g': 200,
                    'nutrition': dict(self.food_db.get('米饭', {}))
                })
                results.append({
                    'name': '鸡胸肉',
                    'name_en': 'Chicken Breast',
                    'confidence': 0.68,
                    'portion_g': 120,
                    'nutrition': dict(self.food_db.get('鸡胸肉', {}))
                })

            elif brightness < 100:
                # Dark - likely meat dishes, dark sauces
                results.append({
                    'name': '宫保鸡丁',
                    'name_en': 'Kung Pao Chicken',
                    'confidence': 0.75,
                    'portion_g': 200,
                    'nutrition': dict(self.food_db.get('宫保鸡丁', {}))
                })

            else:
                # Default: balanced meal assumption
                results.append({
                    'name': '米饭',
                    'name_en': 'Rice',
                    'confidence': 0.80,
                    'portion_g': 200,
                    'nutrition': dict(self.food_db.get('米饭', {}))
                })
                results.append({
                    'name': '西红柿炒鸡蛋',
                    'name_en': 'Tomato Egg Stir-fry',
                    'confidence': 0.70,
                    'portion_g': 180,
                    'nutrition': dict(self.food_db.get('西红柿炒鸡蛋', {}))
                })
                results.append({
                    'name': '炒青菜',
                    'name_en': 'Stir-fried Greens',
                    'confidence': 0.63,
                    'portion_g': 120,
                    'nutrition': dict(self.food_db.get('炒青菜', {}))
                })

            return results

        except Exception as e:
            # Fallback: return generic results
            return [{
                'name': '未知食物',
                'name_en': 'Unknown Food',
                'confidence': 0.3,
                'portion_g': 200,
                'nutrition': {'calories': 250, 'protein': 10, 'fat': 10, 'carbs': 30, 'fiber': 2}
            }]

    def _recognize_api(self, image_path):
        """API mode: Use LLM to recognize food from image.
        Tries vision API first; falls back to color analysis + LLM text reasoning
        for text-only models (e.g. DeepSeek)."""
        import base64

        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # Try vision API first (OpenAI-compatible image_url format)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.api_base)

            prompt = """Analyze this food image carefully. Return ONLY a JSON array of food items.
Each item should have: name (Chinese name), name_en (English name), confidence (0-1), portion_g (estimated grams).
Also include nutrition per 100g: calories, protein_g, fat_g, carbs_g, fiber_g.
Only return the JSON, no other text.

Example format:
[{"name": "米饭", "name_en": "Rice", "confidence": 0.9, "portion_g": 200, "nutrition": {"calories": 116, "protein_g": 2.6, "fat_g": 0.3, "carbs_g": 25.9, "fiber_g": 0.3}}]"""

            response = client.chat.completions.create(
                model=self.model or 'gpt-4o',
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{image_data}'}}
                    ]
                }],
                max_tokens=1000,
                temperature=0.3
            )

            content = response.choices[0].message.content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
                if content.endswith('```'):
                    content = content[:-3]
            return json.loads(content)

        except Exception as vision_error:
            error_msg = str(vision_error)
            # If vision not supported (DeepSeek etc.), use color analysis + LLM
            if 'image_url' in error_msg or 'unknown variant' in error_msg or 'proxies' in error_msg:
                return self._recognize_text_api(image_path, image_data)
            # For other errors, fall back to simulation
            print(f"Vision API error, using simulation: {error_msg}")
            return self._recognize_simulation(image_path)

    def _call_llm(self, messages, max_tokens=800, temperature=0.3):
        """Call LLM API using either OpenAI library or direct HTTP request."""
        # Try OpenAI library first
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.api_base)
            response = client.chat.completions.create(
                model=self.model or 'gpt-4o',
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception:
            pass

        # Fallback: direct HTTP request
        try:
            import urllib.request
            data = json.dumps({
                'model': self.model or 'gpt-4o',
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature
            }).encode('utf-8')
            req = urllib.request.Request(
                f'{self.api_base}/chat/completions',
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                }
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                return result['choices'][0]['message']['content'].strip()
        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {e}")

    def _recognize_text_api(self, image_path, image_data):
        """
        For text-only LLMs (DeepSeek):
        1. Analyze image color distribution
        2. Send color features as text to LLM
        3. LLM reasons about what food it might be
        """
        try:
            # Step 1: Analyze image colors
            img = Image.open(image_path)
            img = img.convert('RGB')
            img_small = img.resize((100, 100))

            pixels = list(img_small.getdata())
            total = len(pixels)

            r_avg = sum(p[0] for p in pixels) / total
            g_avg = sum(p[1] for p in pixels) / total
            b_avg = sum(p[2] for p in pixels) / total
            brightness = (r_avg + g_avg + b_avg) / 3

            # Determine dominant color
            if g_avg > r_avg and g_avg > b_avg:
                dominant = 'green'
            elif r_avg > g_avg and r_avg > b_avg:
                dominant = 'red/orange'
            elif b_avg > r_avg and b_avg > g_avg:
                dominant = 'blue/purple'
            else:
                dominant = 'neutral'

            if brightness > 180:
                tone = 'very bright/white'
            elif brightness > 140:
                tone = 'bright'
            elif brightness > 80:
                tone = 'medium'
            else:
                tone = 'dark'

            # Step 2: Get initial guess from simulation
            sim_results = self._recognize_simulation(image_path)

            # Step 3: Build text prompt for LLM
            food_names = [f['name'] for f in sim_results]
            food_list = ', '.join(food_names)

            prompt = f"""你是一个食物识别专家。根据以下图片的色彩分析数据，判断这是什么食物。

图片色彩特征:
- 主色调: {dominant}
- 亮度: {tone}
- 红色通道均值: {r_avg:.1f}
- 绿色通道均值: {g_avg:.1f}
- 蓝色通道均值: {b_avg:.1f}

已知食物数据库中可能的匹配（基于色彩启发式）: {food_list}

请根据色彩特征，识别图片中最可能的食物。返回JSON数组格式（只返回JSON，不要其他文字）:
[{{"name": "食物中文名", "name_en": "English name", "confidence": 0.8, "portion_g": 200, "nutrition": {{"calories": 150, "protein_g": 10, "fat_g": 8, "carbs_g": 15, "fiber_g": 2}}}}]

注意:
1. name必须是中文食物名
2. nutrition中的字段名必须是: calories, protein_g, fat_g, carbs_g, fiber_g
3. confidence基于色彩匹配度，0-1之间
4. 如果绿色为主，可能是蔬菜类
5. 如果红色/深色为主，可能是肉类或红烧菜
6. 如果亮白色为主，可能是米饭、面食类"""

            content = self._call_llm(
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=800,
                temperature=0.3
            )

            if content.startswith('```'):
                content = content.split('\n', 1)[1]
                if content.endswith('```'):
                    content = content[:-3]

            results = json.loads(content)

            # Ensure nutrition uses correct keys
            for item in results:
                if 'nutrition' in item:
                    nut = item['nutrition']
                    for old_key, new_key in [('protein_g', 'protein'), ('fat_g', 'fat'),
                                              ('carbs_g', 'carbs'), ('fiber_g', 'fiber')]:
                        if old_key in nut and new_key not in nut:
                            nut[new_key] = nut[old_key]

            return results

        except Exception as e:
            print(f"Text API recognition error: {e}")
            return self._recognize_simulation(image_path)


def search_food(keyword, limit=10):
    """
    Fuzzy search food database by keyword.
    Handles compound food names like "鸡蛋油条肠粉" by trying:
    1. Exact match
    2. The keyword as substring of DB entry (user typed partial)
    3. DB entry as substring of keyword (user typed compound name)
    4. Individual character overlap
    5. Trailing/leading substring matching (for compound names)

    Returns list of dicts: {name, nutrition, match_score}
    """
    keyword = keyword.strip()
    if not keyword:
        return []

    results = {}
    kw_len = len(keyword)

    for name, nutrition in FOOD_DB.items():
        score = 0

        # Exact match
        if keyword == name:
            score = 100
        # Keyword is substring of DB name (user typed partial name)
        elif keyword in name:
            # Longer keyword match = higher confidence
            score = 80 + min(kw_len / len(name) * 10, 10)
        # DB name is substring of keyword (user typed compound like "鸡蛋油条肠粉")
        elif name in keyword:
            # The longer the matched DB entry relative to keyword, the better
            score = 75 + min(len(name) / kw_len * 15, 15)
        # Character-level matching
        else:
            matched_chars = sum(1 for c in keyword if c in name)
            char_ratio = matched_chars / max(kw_len, 1)
            if char_ratio >= 0.5:
                score = 40 + char_ratio * 20
            elif char_ratio >= 0.3:
                score = 20 + char_ratio * 30

        # Bonus: if the DB name appears at the end or beginning of keyword
        # (common in compound food names like "鸡蛋" + "肠粉")
        if score < 70 and len(name) >= 2:
            if keyword.endswith(name) or keyword.startswith(name):
                score = max(score, 70)
            # Also check if we remove first/last char
            elif len(keyword) > 2:
                if keyword[1:].endswith(name) or keyword[:-1].endswith(name):
                    score = max(score, 55)

        if score > 0:
            # Only keep the best match per food name
            if name not in results or score > results[name]['match_score']:
                results[name] = {
                    'name': name,
                    'name_en': name,
                    'nutrition': dict(nutrition),
                    'match_score': round(score, 1)
                }

    # Sort by match score descending
    sorted_results = sorted(results.values(), key=lambda x: x['match_score'], reverse=True)

    return sorted_results[:limit]


def get_food_nutrition(food_name):
    """Get nutrition data for a specific food by exact name."""
    return FOOD_DB.get(food_name)


def get_all_food_names():
    """Return all food names in the database."""
    return list(FOOD_DB.keys())


def parse_food_text(text):
    """
    解析复合食物文本输入，自动拆分为多个食物并匹配数据库。

    支持的分隔符：加、+、和、、、配、跟、与、带、含、拌、还有、还有.

    示例:
        "猪脚饭加卤蛋" → [猪脚饭, 卤蛋]
        "鸡腿饭加酸菜" → [鸡腿饭, 酸菜]
        "米饭加红烧肉加炒青菜" → [米饭, 红烧肉, 炒青菜]

    Returns:
        list of dicts: [{name, name_en, portion_g, nutrition, confidence}]
    """
    import re

    if not text or not text.strip():
        return []

    text = text.strip()

    # Step 1: Split by known separators
    separators = ['还有', '还加', '再加', '加', '\\+', '和', '、', '，', ',',
                  '配', '跟', '与', '带', '含', '拌', '还有']
    sep_pattern = '|'.join(separators)
    parts = re.split(sep_pattern, text)
    parts = [p.strip() for p in parts if p.strip()]

    results = []

    for part in parts:
        # Step 2: Try exact match first
        if part in FOOD_DB:
            results.append({
                'name': part,
                'name_en': part,
                'confidence': 1.0,
                'portion_g': 200,
                'nutrition': dict(FOOD_DB[part])
            })
            continue

        # Step 3: Try fuzzy search
        matches = search_food(part, limit=1)
        if matches and matches[0]['match_score'] >= 70:
            m = matches[0]
            results.append({
                'name': m['name'],
                'name_en': m['name'],
                'confidence': m['match_score'] / 100.0,
                'portion_g': 200,
                'nutrition': m['nutrition']
            })
            continue

        # Step 4: Try probing sub-strings (from longest to shortest, min 2 chars)
        # This handles cases where the compound word itself isn't in DB but its parts are
        # e.g., searching for longest matching substring
        best_len = 0
        best_food = None
        for food_name in FOOD_DB:
            if food_name in part and len(food_name) > best_len:
                best_len = len(food_name)
                best_food = food_name

        if best_food and best_len >= 2:
            results.append({
                'name': best_food,
                'name_en': best_food,
                'confidence': 0.75,
                'portion_g': 200,
                'nutrition': dict(FOOD_DB[best_food])
            })
            continue

        # Step 5: Give up and return as unknown
        results.append({
            'name': part,
            'name_en': part,
            'confidence': 0.3,
            'portion_g': 200,
            'nutrition': {'calories': 150, 'protein': 5, 'fat': 5, 'carbs': 20, 'fiber': 1}
        })

    return results


def create_recognizer(config):
    """Factory function to create a FoodRecognizer from app config"""
    return FoodRecognizer(
        mode=config.get('AI_MODE', 'simulation'),
        api_key=config.get('LLM_API_KEY'),
        api_base=config.get('LLM_API_BASE'),
        model=config.get('VISION_MODEL')
    )
