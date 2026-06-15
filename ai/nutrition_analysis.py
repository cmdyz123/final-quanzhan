"""
Nutrition Analysis Module - 营养分析

Analyzes food recognition results and provides nutritional insights.
Supports LLM-based deep analysis and rule-based quick analysis.
"""

import json
from datetime import date


class NutritionAnalyzer:
    """Nutrition analysis engine"""

    def __init__(self, mode='simulation', api_key=None, api_base=None, model=None):
        self.mode = mode
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

    def analyze_meal(self, foods, user_info=None):
        """
        Analyze a meal's nutritional content.

        Args:
            foods: list of food dicts from recognizer
            user_info: dict with user's height, weight, age, gender, goal

        Returns:
            dict with nutrition totals and analysis
        """
        # Calculate totals
        total_nutrition = {
            'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0
        }

        for food in foods:
            nutrition = food.get('nutrition', {})
            portion = food.get('portion_g', 100)
            factor = portion / 100.0

            total_nutrition['calories'] += nutrition.get('calories', 0) * factor
            total_nutrition['protein'] += nutrition.get('protein', 0) * factor
            total_nutrition['fat'] += nutrition.get('fat', 0) * factor
            total_nutrition['carbs'] += nutrition.get('carbs', 0) * factor
            total_nutrition['fiber'] += nutrition.get('fiber', 0) * factor

        # Round values
        for k in total_nutrition:
            total_nutrition[k] = round(total_nutrition[k], 1)

        # Generate analysis
        analysis = self._generate_analysis(total_nutrition, user_info)

        return {
            'foods': foods,
            'totals': total_nutrition,
            'analysis': analysis
        }

    def _generate_analysis(self, nutrition, user_info=None):
        """Generate nutritional analysis text"""
        cals = nutrition['calories']
        protein = nutrition['protein']
        fat = nutrition['fat']
        carbs = nutrition['carbs']
        fiber = nutrition['fiber']

        analysis_parts = []

        # Calorie assessment
        if cals < 200:
            analysis_parts.append("这是一份低热量餐食，适合作为轻食或加餐。")
        elif cals < 500:
            analysis_parts.append("热量适中，作为一餐来说是合理的摄入量。")
        elif cals < 800:
            analysis_parts.append("热量较高，请注意控制总体热量平衡。")
        else:
            analysis_parts.append("热量偏高，建议减少高热量食物摄入或增加运动消耗。")

        # Protein assessment
        if protein < 15:
            analysis_parts.append("蛋白质含量偏低，建议搭配肉类、鸡蛋或豆制品。")
        elif protein < 30:
            analysis_parts.append("蛋白质含量适中，能满足基本需求。")
        else:
            analysis_parts.append("蛋白质含量充足，有助于肌肉维持和修复。")

        # Fat assessment
        fat_ratio = (fat * 9) / max(cals, 1) * 100
        if fat_ratio > 35:
            analysis_parts.append("脂肪占比较高，建议减少油炸食品和肥肉摄入。")
        elif fat_ratio < 15:
            analysis_parts.append("脂肪含量较低，可适量增加健康脂肪如坚果、橄榄油等。")
        else:
            analysis_parts.append("脂肪比例合理。")

        # Fiber assessment
        if fiber < 3:
            analysis_parts.append("膳食纤维不足，建议增加蔬菜和水果摄入。")
        else:
            analysis_parts.append(f"膳食纤维{fiber:.0f}g，有助于肠道健康。")

        # Goal-based advice
        if user_info:
            goal = user_info.get('goal', 'maintain')
            if goal == 'lose':
                if cals > 500:
                    analysis_parts.append("减重期间建议控制每餐热量在400-500千卡以内。")
            elif goal == 'gain':
                if protein < 25:
                    analysis_parts.append("增肌期间建议每餐保证充足的蛋白质摄入（25g以上）。")

        return ' '.join(analysis_parts)

    def deep_analyze(self, nutrition_data, user_info, meal_history=None):
        """Use LLM for deep nutritional analysis (API mode)"""
        if self.mode != 'api':
            return self._generate_analysis(nutrition_data.get('totals', {}), user_info)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.api_base)

            prompt = self._build_deep_analysis_prompt(nutrition_data, user_info, meal_history)

            response = client.chat.completions.create(
                model=self.model or 'gpt-4o',
                messages=[
                    {'role': 'system', 'content': '你是一位专业的营养师，请根据用户的餐食数据提供专业的营养分析。'},
                    {'role': 'user', 'content': prompt}
                ],
                max_tokens=800,
                temperature=0.5
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Deep analysis error: {e}")
            return self._generate_analysis(nutrition_data.get('totals', {}), user_info)

    def _build_deep_analysis_prompt(self, nutrition_data, user_info, meal_history):
        prompt_parts = ["请分析以下餐食的营养数据：\n"]

        totals = nutrition_data.get('totals', {})
        prompt_parts.append(f"- 总热量: {totals.get('calories', 0)}千卡")
        prompt_parts.append(f"- 蛋白质: {totals.get('protein', 0)}g")
        prompt_parts.append(f"- 脂肪: {totals.get('fat', 0)}g")
        prompt_parts.append(f"- 碳水化合物: {totals.get('carbs', 0)}g")
        prompt_parts.append(f"- 膳食纤维: {totals.get('fiber', 0)}g")

        foods = nutrition_data.get('foods', [])
        if foods:
            prompt_parts.append("\n识别的食物：")
            for f in foods:
                prompt_parts.append(f"- {f.get('name', '未知')} ({f.get('portion_g', '?')}g)")

        if user_info:
            prompt_parts.append(f"\n用户信息：")
            if user_info.get('height'):
                prompt_parts.append(f"- 身高: {user_info['height']}cm")
            if user_info.get('weight'):
                prompt_parts.append(f"- 体重: {user_info['weight']}kg")
            if user_info.get('goal'):
                goal_map = {'lose': '减重', 'gain': '增肌', 'maintain': '维持'}
                prompt_parts.append(f"- 目标: {goal_map.get(user_info['goal'], '维持')}")

        prompt_parts.append("\n请提供：1) 整体营养评价 2) 改进建议 3) 下一餐推荐")
        return '\n'.join(prompt_parts)

    def analyze_daily_summary(self, meals_today, user_info=None):
        """Analyze the full day's nutrition against targets"""
        daily_totals = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0}

        for meal in meals_today:
            nutrition = meal.get_nutrition()
            for k in daily_totals:
                daily_totals[k] += nutrition.get(k, 0)

        for k in daily_totals:
            daily_totals[k] = round(daily_totals[k], 1)

        targets = {
            'calories': 2000, 'protein': 60, 'fat': 65, 'carbs': 300, 'fiber': 25
        }

        percentages = {}
        for k in daily_totals:
            percentages[k] = round(daily_totals[k] / max(targets.get(k, 1), 1) * 100, 1)

        # Generate summary message
        summary = ""
        if percentages['calories'] < 60:
            summary += "今日热量摄入偏低，记得按时吃饭哦！"
        elif percentages['calories'] < 90:
            summary += "今日热量摄入适中，再接再厉！"
        elif percentages['calories'] <= 110:
            summary += "今日热量摄入达标，非常棒！"
        else:
            summary += "今日热量摄入偏高，明天注意控制～"

        return {
            'totals': daily_totals,
            'targets': targets,
            'percentages': percentages,
            'summary': summary
        }


def create_analyzer(config):
    """Factory function"""
    return NutritionAnalyzer(
        mode=config.get('AI_MODE', 'simulation'),
        api_key=config.get('LLM_API_KEY'),
        api_base=config.get('LLM_API_BASE'),
        model=config.get('LLM_MODEL')
    )
