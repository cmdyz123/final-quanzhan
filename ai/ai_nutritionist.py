"""
AI Nutritionist Agent - AI营养师智能体

A conversational AI agent that acts as a professional nutritionist.
Features multi-turn memory, personalized advice, and meal planning.
"""

import json
from datetime import date, datetime, timedelta


SYSTEM_PROMPT = """你是一位专业、友好的AI营养师，名叫"小营"。你的职责是：

1. 根据用户的饮食记录和身体数据，提供个性化的营养建议
2. 回答用户关于营养、健康饮食的问题
3. 帮助用户制定合理的饮食计划
4. 鼓励用户养成健康的饮食习惯

你的特点：
- 专业但不刻板，用通俗易懂的语言解释营养知识
- 关注用户的饮食趋势，而不仅仅是单餐分析
- 记住用户的目标（减重/增肌/维持）并针对性建议
- 善用具体数据说话，让建议更有说服力
- 适当给予鼓励和正面反馈

注意事项：
- 你不是医生，遇到医疗问题请建议用户咨询专业医生
- 避免推荐极端的饮食方式（如极低热量饮食）
- 尊重用户的饮食偏好和文化习惯"""


class AINutritionist:
    """AI Nutritionist Agent with conversation memory"""

    def __init__(self, mode='simulation', api_key=None, api_base=None, model=None):
        self.mode = mode
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.system_prompt = SYSTEM_PROMPT
        self.conversations = {}  # user_id -> list of messages

    def chat(self, user_id, message, user_info=None, meal_history=None):
        """
        Chat with the AI nutritionist.

        Args:
            user_id: user identifier
            message: user's message
            user_info: dict with user profile
            meal_history: list of recent meal records

        Returns:
            str: AI response
        """
        if self.mode == 'api':
            return self._chat_api(user_id, message, user_info, meal_history)
        else:
            return self._chat_simulation(user_id, message, user_info, meal_history)

    def _chat_simulation(self, user_id, message, user_info, meal_history):
        """Simulation mode: Rule-based responses for demo without API key"""
        msg_lower = message.strip().lower()

        # Initialize conversation if needed
        if user_id not in self.conversations:
            self.conversations[user_id] = []

        # Build context
        context = ""
        if user_info:
            goal_map = {'lose': '减重', 'gain': '增肌', 'maintain': '维持体重'}
            goal = goal_map.get(user_info.get('goal', 'maintain'), '维持体重')
            context = f"用户目标：{goal}"
            if user_info.get('weight'):
                context += f"，体重{user_info['weight']}kg"
            if user_info.get('height'):
                context += f"，身高{user_info['height']}cm"

        if meal_history:
            today_meals = []
            today = date.today()
            for m in meal_history:
                if m.created_at.date() == today:
                    nutrition = m.get_nutrition()
                    today_meals.append(nutrition)

            if today_meals:
                total_cal = sum(n.get('calories', 0) for n in today_meals)
                total_protein = sum(n.get('protein', 0) for n in today_meals)
                context += f"。今日已摄入{total_cal:.0f}千卡热量，{total_protein:.0f}g蛋白质"

        self.conversations[user_id].append({'role': 'user', 'content': message})

        # Generate response based on keywords
        response = self._generate_rule_response(msg_lower, context)

        self.conversations[user_id].append({'role': 'assistant', 'content': response})
        return response

    def _generate_rule_response(self, message, context):
        """Generate rule-based responses"""
        if any(w in message for w in ['你好', '嗨', 'hi', 'hello', '在吗']):
            return "你好呀！我是你的AI营养师小营 🥗 有什么营养方面的问题可以随时问我哦～今天吃得好吗？"

        if any(w in message for w in ['减', '瘦', 'lose', '减肥']):
            return ("关于减重，我有几点建议：\n\n"
                    "1. **控制热量缺口**：每天摄入比消耗少300-500千卡是比较健康的速度\n"
                    "2. **保证蛋白质**：减重期间蛋白质摄入很重要，每公斤体重至少1.2g\n"
                    "3. **不要极端节食**：过度节食会降低基础代谢，反而不利于长期减重\n"
                    "4. **搭配运动**：有氧+力量训练结合效果更好\n\n"
                    f"{context}\n\n需要我帮你制定一个减重饮食计划吗？")

        if any(w in message for w in ['增', '肌', 'gain', '增重']):
            return ("增肌饮食的关键点：\n\n"
                    "1. **蛋白质是基础**：每公斤体重1.6-2.0g蛋白质\n"
                    "2. **热量盈余要适度**：每天多摄入300-500千卡即可\n"
                    "3. **碳水也很重要**：训练前后补充碳水有助于表现和恢复\n"
                    "4. **分餐制**：把蛋白质均匀分配到4-5餐中吸收更好\n\n"
                    "你目前的训练频率是怎样的？我可以针对性地帮你调整饮食～")

        if any(w in message for w in ['吃什么', '推荐', '建议', '推荐一下', '食谱']):
            return ("根据你的情况，我推荐以下搭配思路：\n\n"
                    "🥬 **蔬菜**：每餐至少占1/3（西兰花、菠菜、番茄都不错）\n"
                    "🍗 **蛋白质**：优选鸡胸肉、鱼虾、豆腐、鸡蛋\n"
                    "🍚 **主食**：粗粮细粮搭配（糙米、全麦面包、红薯）\n"
                    "🫒 **好脂肪**：坚果、牛油果、橄榄油适量摄入\n\n"
                    "记住口诀：**一拳主食、一掌蛋白、两拳蔬菜**～")

        if any(w in message for w in ['热量', '卡路里', 'calorie']):
            return ("关于热量管理：\n\n"
                    "- 成年女性日均需要约1800-2000千卡\n"
                    "- 成年男性日均需要约2000-2400千卡\n"
                    "- 减重建议控制在1500-1800千卡/天\n"
                    "- 每餐建议400-600千卡\n\n"
                    "你现在每餐的热量摄入情况如何？我可以帮你看看～")

        if any(w in message for w in ['蛋白', 'protein']):
            return ("蛋白质是身体必需的营养素！\n\n"
                    "**每日推荐摄入量**：\n"
                    "- 普通成人：0.8-1.0g/kg体重\n"
                    "- 运动人群：1.2-1.6g/kg体重\n"
                    "- 增肌期：1.6-2.0g/kg体重\n\n"
                    "**优质蛋白来源**：鸡胸肉、鸡蛋、牛奶、鱼虾、豆腐、牛肉\n\n"
                    "你今天蛋白质吃够了吗？😊")

        if any(w in message for w in ['今天', '今日', 'today', '记录']):
            if '今日' in context and '千卡' in context:
                return f"来看看你今天的饮食情况～{context}\n\n继续保持，注意营养均衡哦！有什么想了解的具体问题尽管问我。"
            return "让我看看你的饮食记录... 你今天还没记录餐食呢！记得上传餐食照片，我会帮你分析营养情况～"

        # Default response
        return ("好的，我理解你的问题～ 作为你的AI营养师，我建议：\n\n"
                "- 保持三餐规律，不要跳过早餐\n"
                "- 每餐保证有蛋白质+蔬菜+主食\n"
                "- 多喝水，每天至少1.5-2L\n"
                "- 少吃加工食品，多吃天然食物\n\n"
                "有什么具体的营养问题，随时问我！🥗")

    def _chat_api(self, user_id, message, user_info, meal_history):
        """API mode: Use LLM for natural conversation"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.api_base)

            # Build messages with history
            messages = [{'role': 'system', 'content': self.system_prompt}]

            # Add user context
            if user_info:
                context_msg = "当前用户信息：\n"
                if user_info.get('height'):
                    context_msg += f"- 身高: {user_info['height']}cm\n"
                if user_info.get('weight'):
                    context_msg += f"- 体重: {user_info['weight']}kg\n"
                if user_info.get('age'):
                    context_msg += f"- 年龄: {user_info['age']}岁\n"
                if user_info.get('gender'):
                    gender_map = {'male': '男', 'female': '女'}
                    context_msg += f"- 性别: {gender_map.get(user_info['gender'], '未知')}\n"
                if user_info.get('goal'):
                    goal_map = {'lose': '减重', 'gain': '增肌', 'maintain': '维持'}
                    context_msg += f"- 目标: {goal_map.get(user_info['goal'], '维持')}\n"
                messages.append({'role': 'system', 'content': context_msg})

            # Add meal history context
            if meal_history:
                today = date.today()
                today_meals = [m for m in meal_history if m.created_at.date() == today]
                if today_meals:
                    meal_context = "用户今日饮食记录：\n"
                    for m in today_meals:
                        nutrition = m.get_nutrition()
                        meal_context += f"- {m.meal_type}: {m.get_foods()}, "
                        meal_context += f"热量{nutrition.get('calories',0)}千卡, "
                        meal_context += f"蛋白质{nutrition.get('protein',0)}g\n"
                    messages.append({'role': 'system', 'content': meal_context})

            # Add conversation history (last 10 turns)
            if user_id in self.conversations:
                recent = self.conversations[user_id][-20:]
                for turn in recent:
                    messages.append({
                        'role': turn['role'],
                        'content': turn['content']
                    })

            # Add current message
            messages.append({'role': 'user', 'content': message})

            response = client.chat.completions.create(
                model=self.model or 'gpt-4o',
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )

            reply = response.choices[0].message.content

            # Store conversation
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            self.conversations[user_id].append({'role': 'user', 'content': message})
            self.conversations[user_id].append({'role': 'assistant', 'content': reply})

            return reply

        except Exception as e:
            print(f"AI chat API error: {e}")
            return self._chat_simulation(user_id, message, user_info, meal_history)

    def generate_meal_plan(self, user_id, user_info, meal_history, target_calories=None):
        """
        Generate personalized meal plan using AIGC.

        Returns:
            dict with meal plan for the day
        """
        if self.mode == 'api':
            return self._generate_meal_plan_api(user_info, meal_history, target_calories)
        else:
            return self._generate_meal_plan_simulation(user_info, meal_history, target_calories)

    def _generate_meal_plan_simulation(self, user_info, meal_history, target_calories):
        """Generate meal plan in simulation mode"""
        goal = user_info.get('goal', 'maintain') if user_info else 'maintain'
        target_cal = target_calories or 2000

        # Calculate today's remaining
        today = date.today()
        today_consumed = 0
        if meal_history:
            today_consumed = sum(
                m.get_nutrition().get('calories', 0)
                for m in meal_history if m.created_at.date() == today
            )

        remaining = max(target_cal - today_consumed, 300)

        plans = {
            'lose': {
                'breakfast': {
                    'foods': [
                        {'name': '全麦面包', 'portion': '2片', 'calories': 160},
                        {'name': '水煮蛋', 'portion': '1个', 'calories': 72},
                        {'name': '脱脂牛奶', 'portion': '200ml', 'calories': 70},
                        {'name': '小番茄', 'portion': '5颗', 'calories': 20}
                    ],
                    'total_calories': 322,
                    'tip': '高蛋白、高纤维早餐，提供持久饱腹感'
                },
                'lunch': {
                    'foods': [
                        {'name': '糙米饭', 'portion': '半碗(100g)', 'calories': 116},
                        {'name': '清蒸鸡胸肉', 'portion': '150g', 'calories': 200},
                        {'name': '凉拌西兰花', 'portion': '200g', 'calories': 68},
                        {'name': '紫菜蛋花汤', 'portion': '1碗', 'calories': 50}
                    ],
                    'total_calories': 434,
                    'tip': '低脂高蛋白，搭配粗粮有助于控制血糖'
                },
                'dinner': {
                    'foods': [
                        {'name': '蒸红薯', 'portion': '1个(150g)', 'calories': 116},
                        {'name': '清蒸鱼', 'portion': '120g', 'calories': 120},
                        {'name': '蒜蓉菠菜', 'portion': '200g', 'calories': 46},
                    ],
                    'total_calories': 282,
                    'tip': '晚餐清淡少油，七分饱即可'
                }
            },
            'gain': {
                'breakfast': {
                    'foods': [
                        {'name': '燕麦片', 'portion': '50g', 'calories': 190},
                        {'name': '全脂牛奶', 'portion': '300ml', 'calories': 183},
                        {'name': '煮鸡蛋', 'portion': '2个', 'calories': 144},
                        {'name': '香蕉', 'portion': '1根', 'calories': 89},
                        {'name': '花生酱', 'portion': '1勺(15g)', 'calories': 88}
                    ],
                    'total_calories': 694,
                    'tip': '高热量高蛋白，为一天训练提供充足能量'
                },
                'lunch': {
                    'foods': [
                        {'name': '米饭', 'portion': '1碗(200g)', 'calories': 232},
                        {'name': '红烧牛肉', 'portion': '200g', 'calories': 250},
                        {'name': '炒西兰花', 'portion': '150g', 'calories': 68},
                        {'name': '番茄蛋汤', 'portion': '1碗', 'calories': 60},
                    ],
                    'total_calories': 610,
                    'tip': '足量蛋白质+碳水，训练后恢复的关键'
                },
                'dinner': {
                    'foods': [
                        {'name': '全麦面包', 'portion': '2片', 'calories': 160},
                        {'name': '煎三文鱼', 'portion': '200g', 'calories': 416},
                        {'name': '牛油果沙拉', 'portion': '1份', 'calories': 180},
                        {'name': '酸奶', 'portion': '200g', 'calories': 144},
                    ],
                    'total_calories': 900,
                    'tip': '优质脂肪+蛋白质，帮助夜间肌肉修复'
                }
            },
            'maintain': {
                'breakfast': {
                    'foods': [
                        {'name': '全麦吐司', 'portion': '2片', 'calories': 160},
                        {'name': '煎蛋', 'portion': '1个', 'calories': 90},
                        {'name': '牛奶', 'portion': '250ml', 'calories': 152},
                        {'name': '苹果', 'portion': '1个', 'calories': 80}
                    ],
                    'total_calories': 482,
                    'tip': '均衡搭配，开启元气满满的一天'
                },
                'lunch': {
                    'foods': [
                        {'name': '米饭', 'portion': '1碗(150g)', 'calories': 174},
                        {'name': '宫保鸡丁', 'portion': '180g', 'calories': 333},
                        {'name': '清炒时蔬', 'portion': '200g', 'calories': 60},
                        {'name': '豆腐汤', 'portion': '1碗', 'calories': 50}
                    ],
                    'total_calories': 617,
                    'tip': '荤素搭配，营养均衡'
                },
                'dinner': {
                    'foods': [
                        {'name': '杂粮饭', 'portion': '半碗(100g)', 'calories': 110},
                        {'name': '清蒸虾', 'portion': '150g', 'calories': 149},
                        {'name': '炒菠菜', 'portion': '150g', 'calories': 35},
                    ],
                    'total_calories': 294,
                    'tip': '晚餐适量，清淡为主'
                }
            }
        }

        plan = plans.get(goal, plans['maintain'])
        total = sum(p['total_calories'] for p in plan.values())

        return {
            'goal': goal,
            'remaining_calories_today': round(remaining),
            'meal_plan': plan,
            'total_calories': total,
            'note': f'本食谱基于你的{goal}目标生成，全天总热量约{total}千卡。'
                    f'今日还可摄入约{remaining:.0f}千卡。'
        }

    def _generate_meal_plan_api(self, user_info, meal_history, target_calories):
        """Generate meal plan using LLM API"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.api_base)

            prompt = "请根据以下用户信息，生成一份今日的个性化餐食计划，返回JSON格式。\n\n"
            if user_info:
                if user_info.get('goal'):
                    goal_map = {'lose': '减重', 'gain': '增肌', 'maintain': '维持'}
                    prompt += f"目标: {goal_map.get(user_info['goal'], '维持')}\n"
                if user_info.get('weight'):
                    prompt += f"体重: {user_info['weight']}kg\n"

            prompt += f"目标热量: {target_calories}千卡\n"
            prompt += "\n请返回JSON，包含breakfast/lunch/dinner，每餐含foods列表和total_calories。"

            response = client.chat.completions.create(
                model=self.model or 'gpt-4o',
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=1500,
                temperature=0.7,
                response_format={'type': 'json_object'}
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            print(f"Meal plan API error: {e}")
            return self._generate_meal_plan_simulation(user_info, meal_history, target_calories)


def create_nutritionist(config):
    """Factory function"""
    return AINutritionist(
        mode=config.get('AI_MODE', 'simulation'),
        api_key=config.get('LLM_API_KEY'),
        api_base=config.get('LLM_API_BASE'),
        model=config.get('LLM_MODEL')
    )
