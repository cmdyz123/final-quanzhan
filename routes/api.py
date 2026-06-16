import os
import uuid
from datetime import date
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, MealRecord, ChatHistory, MealPlan
from ai.food_recognition import FoodRecognizer, search_food, get_food_nutrition, parse_food_text
from ai.nutrition_analysis import NutritionAnalyzer
from ai.ai_nutritionist import AINutritionist
from config import Config

api_bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_ai_config():
    return {
        'AI_MODE': Config.AI_MODE,
        'LLM_API_KEY': Config.LLM_API_KEY,
        'LLM_API_BASE': Config.LLM_API_BASE,
        'LLM_MODEL': Config.LLM_MODEL,
        'VISION_MODEL': Config.VISION_MODEL,
    }


@api_bp.route('/api/search-food')
@login_required
def search_food_api():
    """Search food database by keyword"""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'results': []})

    results = search_food(q, limit=10)
    return jsonify({'results': results})


@api_bp.route('/api/quick-record', methods=['POST'])
@login_required
def quick_record():
    """Quick text input - 直接输入复合食物名称，自动拆分并记录
    Example: "猪脚饭加卤蛋" -> 拆分为猪脚饭+卤蛋并自动分析
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': '请输入食物名称'}), 400

    text = data['text'].strip()
    if not text:
        return jsonify({'error': '请输入食物名称'}), 400

    meal_type = data.get('meal_type', 'lunch')
    price = data.get('price')
    notes = data.get('notes', '')

    # Parse compound food text
    foods_result = parse_food_text(text)

    if not foods_result:
        return jsonify({'error': '未识别到食物，请尝试其他描述'}), 400

    # Calculate nutrition totals
    total_nutrition = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0}
    for food in foods_result:
        nutrition = food.get('nutrition', {})
        portion = food.get('portion_g', 100)
        factor = portion / 100.0
        total_nutrition['calories'] += nutrition.get('calories', 0) * factor
        total_nutrition['protein'] += nutrition.get('protein', 0) * factor
        total_nutrition['fat'] += nutrition.get('fat', 0) * factor
        total_nutrition['carbs'] += nutrition.get('carbs', 0) * factor
        total_nutrition['fiber'] += nutrition.get('fiber', 0) * factor

    for k in total_nutrition:
        total_nutrition[k] = round(total_nutrition[k], 1)

    # Analyze
    user_info = {
        'height': current_user.height,
        'weight': current_user.weight,
        'age': current_user.age,
        'gender': current_user.gender,
        'goal': current_user.goal,
    }
    ai_config = get_ai_config()
    analyzer = NutritionAnalyzer(mode=ai_config['AI_MODE'])
    analysis = analyzer.analyze_meal(foods_result, user_info)

    # Save record
    meal = MealRecord(
        user_id=current_user.id,
        meal_type=meal_type,
        price=price,
        input_method='manual',
        notes=notes or f'快速输入: {text}'
    )
    meal.set_foods(foods_result)
    meal.set_nutrition(total_nutrition)
    db.session.add(meal)
    db.session.commit()

    return jsonify({
        'success': True,
        'meal_id': meal.id,
        'foods': foods_result,
        'nutrition': total_nutrition,
        'analysis': analysis['analysis']
    })
@login_required
def manual_record():
    """Record a meal manually with food names and portions"""
    data = request.get_json()
    if not data or 'foods' not in data:
        return jsonify({'error': 'No food data provided'}), 400

    meal_type = data.get('meal_type', 'lunch')
    foods_input = data.get('foods', [])  # [{name, portion_g}]
    price = data.get('price')
    notes = data.get('notes', '')

    if not foods_input:
        return jsonify({'error': '至少添加一种食物'}), 400

    # Build food list with nutrition from DB
    foods_result = []
    total_nutrition = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0}

    for item in foods_input:
        name = item.get('name', '').strip()
        portion = float(item.get('portion_g', 100))

        nutrition = get_food_nutrition(name)
        if not nutrition:
            # Try fuzzy search
            search_results = search_food(name, limit=1)
            if search_results:
                name = search_results[0]['name']
                nutrition = search_results[0]['nutrition']
            else:
                nutrition = {'calories': 100, 'protein': 5, 'fat': 3, 'carbs': 15, 'fiber': 1}

        factor = portion / 100.0
        total_nutrition['calories'] += nutrition.get('calories', 0) * factor
        total_nutrition['protein'] += nutrition.get('protein', 0) * factor
        total_nutrition['fat'] += nutrition.get('fat', 0) * factor
        total_nutrition['carbs'] += nutrition.get('carbs', 0) * factor
        total_nutrition['fiber'] += nutrition.get('fiber', 0) * factor

        foods_result.append({
            'name': name,
            'name_en': name,
            'confidence': 1.0,
            'portion_g': portion,
            'nutrition': dict(nutrition)
        })

    # Round totals
    for k in total_nutrition:
        total_nutrition[k] = round(total_nutrition[k], 1)

    # Analyze
    user_info = {
        'height': current_user.height,
        'weight': current_user.weight,
        'age': current_user.age,
        'gender': current_user.gender,
        'goal': current_user.goal,
    }
    ai_config = get_ai_config()
    analyzer = NutritionAnalyzer(mode=ai_config['AI_MODE'])
    analysis = analyzer.analyze_meal(foods_result, user_info)

    # Save record
    meal = MealRecord(
        user_id=current_user.id,
        meal_type=meal_type,
        price=price,
        input_method='manual',
        notes=notes
    )
    meal.set_foods(foods_result)
    meal.set_nutrition(total_nutrition)
    db.session.add(meal)
    db.session.commit()

    return jsonify({
        'success': True,
        'meal_id': meal.id,
        'foods': foods_result,
        'nutrition': total_nutrition,
        'analysis': analysis['analysis']
    })


@api_bp.route('/api/analyze-food', methods=['POST'])
@login_required
def analyze_food():
    """API endpoint for food image analysis"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # Save temporarily
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"api_{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Recognize
    ai_config = get_ai_config()
    recognizer = FoodRecognizer(
        mode=ai_config['AI_MODE'],
        api_key=ai_config['LLM_API_KEY'],
        api_base=ai_config['LLM_API_BASE'],
        model=ai_config['VISION_MODEL']
    )
    foods = recognizer.recognize(filepath)

    # Analyze
    user_info = {
        'height': current_user.height,
        'weight': current_user.weight,
        'age': current_user.age,
        'gender': current_user.gender,
        'goal': current_user.goal,
    }
    analyzer = NutritionAnalyzer(mode=ai_config['AI_MODE'])
    analysis = analyzer.analyze_meal(foods, user_info)

    # Save record
    meal_type = request.form.get('meal_type', 'snack')
    price = request.form.get('price', type=float)
    meal = MealRecord(
        user_id=current_user.id,
        meal_type=meal_type,
        image_path=filepath,
        price=price,
        input_method='photo'
    )
    meal.set_foods(foods)
    meal.set_nutrition(analysis['totals'])
    db.session.add(meal)
    db.session.commit()

    return jsonify({
        'success': True,
        'meal_id': meal.id,
        'foods': foods,
        'nutrition': analysis['totals'],
        'analysis': analysis['analysis']
    })


@api_bp.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """API endpoint for AI nutritionist chat"""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    message = data['message']

    ai_config = get_ai_config()
    nutritionist = AINutritionist(
        mode=ai_config['AI_MODE'],
        api_key=ai_config['LLM_API_KEY'],
        api_base=ai_config['LLM_API_BASE'],
        model=ai_config['LLM_MODEL']
    )

    user_info = {
        'height': current_user.height,
        'weight': current_user.weight,
        'age': current_user.age,
        'gender': current_user.gender,
        'goal': current_user.goal,
    }

    recent_meals = MealRecord.query.filter_by(
        user_id=current_user.id
    ).order_by(MealRecord.created_at.desc()).limit(20).all()

    reply = nutritionist.chat(current_user.id, message, user_info, recent_meals)

    # Save to history
    ChatHistory(user_id=current_user.id, role='user', content=message)
    ChatHistory(user_id=current_user.id, role='assistant', content=reply)
    db.session.commit()

    return jsonify({'success': True, 'reply': reply})


@api_bp.route('/api/generate-plan', methods=['POST'])
@login_required
def generate_plan():
    """API endpoint for meal plan generation"""
    ai_config = get_ai_config()
    nutritionist = AINutritionist(
        mode=ai_config['AI_MODE'],
        api_key=ai_config['LLM_API_KEY'],
        api_base=ai_config['LLM_API_BASE'],
        model=ai_config['LLM_MODEL']
    )

    user_info = {
        'height': current_user.height,
        'weight': current_user.weight,
        'age': current_user.age,
        'gender': current_user.gender,
        'goal': current_user.goal,
    }

    today = date.today()
    today_meals = MealRecord.query.filter_by(
        user_id=current_user.id
    ).filter(
        MealRecord.created_at >= today.strftime('%Y-%m-%d')
    ).all()

    targets = {'calories': 2000}
    if current_user.goal == 'lose':
        targets['calories'] = 1600
    elif current_user.goal == 'gain':
        targets['calories'] = 2600

    plan = nutritionist.generate_meal_plan(
        current_user.id, user_info, today_meals, targets['calories']
    )

    return jsonify({'success': True, 'plan': plan})


@api_bp.route('/api/daily-stats', methods=['GET'])
@login_required
def daily_stats():
    """API endpoint for daily nutrition stats"""
    today = date.today()
    meals_today = MealRecord.query.filter_by(
        user_id=current_user.id
    ).filter(
        MealRecord.created_at >= today.strftime('%Y-%m-%d')
    ).all()

    analyzer = NutritionAnalyzer(mode=Config.AI_MODE)
    analysis = analyzer.analyze_daily_summary(meals_today)

    # Add price sum
    total_price = sum(m.price or 0 for m in meals_today)
    analysis['total_price'] = round(total_price, 2)

    return jsonify(analysis)


@api_bp.route('/api/daily-summary', methods=['GET'])
@login_required
def daily_summary():
    """Generate AI-powered daily meal summary.
    Only works when all 3 meals (breakfast/lunch/dinner) are recorded or skipped.
    Accepts optional ?date=YYYY-MM-DD parameter.
    """
    from ai import call_llm

    date_str = request.args.get('date', '')
    if date_str:
        try:
            query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            query_date = date.today()
    else:
        query_date = date.today()

    next_day = query_date + timedelta(days=1)

    all_today = MealRecord.query.filter_by(
        user_id=current_user.id
    ).filter(
        MealRecord.created_at >= query_date.strftime('%Y-%m-%d'),
        MealRecord.created_at < next_day.strftime('%Y-%m-%d')
    ).all()

    # Check meal completion status
    meal_status = {'breakfast': None, 'lunch': None, 'dinner': None}
    for m in all_today:
        mt = m.meal_type
        if mt in meal_status:
            if m.skipped:
                meal_status[mt] = {'status': 'skipped'}
            else:
                meal_status[mt] = {
                    'status': 'recorded',
                    'foods': [f['name'] for f in m.get_foods()],
                    'nutrition': m.get_nutrition(),
                    'price': m.price
                }

    # Only generate if all 3 meals are accounted for
    missing = [mt for mt, v in meal_status.items() if v is None]
    if missing:
        return jsonify({
            'ready': False,
            'message': f'还有{len(missing)}餐未记录，请先完成全天记录',
            'missing': missing
        })

    # Build summary data
    total_cal = 0
    total_protein = 0
    total_fat = 0
    total_carbs = 0
    total_price = 0
    recorded_count = 0
    skipped_count = 0
    all_foods = []

    for mt, data in meal_status.items():
        if data['status'] == 'skipped':
            skipped_count += 1
        elif data['status'] == 'recorded':
            recorded_count += 1
            nut = data['nutrition']
            total_cal += nut.get('calories', 0)
            total_protein += nut.get('protein', 0)
            total_fat += nut.get('fat', 0)
            total_carbs += nut.get('carbs', 0)
            total_price += data.get('price', 0) or 0
            all_foods.extend(data.get('foods', []))

    # Build prompt for AI
    type_labels = {'breakfast': '早餐', 'lunch': '午餐', 'dinner': '晚餐'}
    meal_desc = []
    for mt in ['breakfast', 'lunch', 'dinner']:
        data = meal_status[mt]
        if data['status'] == 'skipped':
            meal_desc.append(f"- {type_labels[mt]}: 已跳过（未吃）")
        else:
            foods = '、'.join(data.get('foods', []))
            cal = data['nutrition'].get('calories', 0)
            price = data.get('price', 0) or 0
            meal_desc.append(f"- {type_labels[mt]}: {foods}（{cal:.0f}千卡，¥{price:.1f}）")

    goal_map = {'lose': '减重', 'gain': '增肌', 'maintain': '维持体重'}
    user_goal = goal_map.get(current_user.goal, '维持体重')

    prompt = f"""作为一位专业营养师，请根据以下用户今天的饮食数据，生成一份简洁的每日饮食总结报告。

用户目标: {user_goal}

今日三餐情况:
{chr(10).join(meal_desc)}

今日总摄入: {total_cal:.0f}千卡 | 蛋白质 {total_protein:.0f}g | 脂肪 {total_fat:.0f}g | 碳水 {total_carbs:.0f}g | 消费 ¥{total_price:.1f}
实际用餐: {recorded_count}餐 | 跳过: {skipped_count}餐

请用中文生成总结，包含以下部分（用简洁的口语风格）：

1. 🍽️ **今日饮食回顾** - 一句话总结今天吃了什么
2. 📊 **营养评估** - 营养摄入是否合理，和用户目标匹配度
3. 💡 **明日建议** - 1-2条具体的改善建议
4. ⭐ **今日评分** - 给今天的饮食打一个1-10分，说明原因

请直接输出，控制在200字以内，不要用markdown标题。"""

    ai_config = get_ai_config()
    try:
        reply = call_llm(
            api_key=ai_config['LLM_API_KEY'],
            api_base=ai_config['LLM_API_BASE'],
            model=ai_config['LLM_MODEL'],
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=500,
            temperature=0.7
        )
        ai_summary = reply
    except Exception as e:
        ai_summary = None
        print(f"Daily summary API error: {e}")

    return jsonify({
        'ready': True,
        'summary': {
            'total_cal': round(total_cal),
            'total_protein': round(total_protein, 1),
            'total_fat': round(total_fat, 1),
            'total_carbs': round(total_carbs, 1),
            'total_price': round(total_price, 1),
            'recorded_count': recorded_count,
            'skipped_count': skipped_count,
            'all_foods': all_foods,
            'meal_status': {
                mt: data['status'] for mt, data in meal_status.items()
            }
        },
        'ai_summary': ai_summary
    })


@api_bp.route('/api/meal/<int:meal_id>/append', methods=['POST'])
@login_required
def meal_append(meal_id):
    """Append food items to an existing meal record.
    Body: {foods: [{name, portion_g}]} or {text: "猪脚饭加卤蛋"}
    """
    meal = MealRecord.query.get_or_404(meal_id)
    if meal.user_id != current_user.id:
        return jsonify({'error': '无权操作'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': '请提供食物数据'}), 400

    # Support both quick text and explicit food list
    if 'text' in data and data['text'].strip():
        new_foods = parse_food_text(data['text'].strip())
    elif 'foods' in data and data['foods']:
        new_foods = []
        for item in data['foods']:
            name = item.get('name', '').strip()
            portion = float(item.get('portion_g', 100))
            nutrition = get_food_nutrition(name)
            if not nutrition:
                search_results = search_food(name, limit=1)
                if search_results:
                    name = search_results[0]['name']
                    nutrition = search_results[0]['nutrition']
                else:
                    nutrition = {'calories': 100, 'protein': 5, 'fat': 3, 'carbs': 15, 'fiber': 1}
            new_foods.append({
                'name': name, 'name_en': name,
                'confidence': 1.0, 'portion_g': portion,
                'nutrition': dict(nutrition)
            })
    else:
        return jsonify({'error': '请提供食物数据 (foods 或 text)'}), 400

    if not new_foods:
        return jsonify({'error': '未识别到食物'}), 400

    # Merge with existing foods
    existing_foods = meal.get_foods()
    all_foods = existing_foods + new_foods

    # Recalculate nutrition
    total_nutrition = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0}
    for f in all_foods:
        nut = f.get('nutrition', {})
        portion = f.get('portion_g', 100)
        factor = portion / 100.0
        for k in total_nutrition:
            total_nutrition[k] += nut.get(k, 0) * factor

    for k in total_nutrition:
        total_nutrition[k] = round(total_nutrition[k], 1)

    meal.set_foods(all_foods)
    meal.set_nutrition(total_nutrition)
    db.session.commit()

    return jsonify({
        'success': True,
        'meal_id': meal.id,
        'added_foods': [f['name'] for f in new_foods],
        'foods': all_foods,
        'nutrition': total_nutrition
    })


@api_bp.route('/api/meal/<int:meal_id>', methods=['DELETE'])
@login_required
def meal_delete_api(meal_id):
    """Delete a meal record via API (for AJAX calls)"""
    meal = MealRecord.query.get_or_404(meal_id)
    if meal.user_id != current_user.id:
        return jsonify({'error': '无权操作'}), 403

    if meal.image_path and os.path.exists(meal.image_path):
        os.remove(meal.image_path)

    db.session.delete(meal)
    db.session.commit()

    return jsonify({'success': True})
