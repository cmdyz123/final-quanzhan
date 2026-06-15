import os
import uuid
from datetime import date
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, MealRecord, ChatHistory, MealPlan
from ai.food_recognition import FoodRecognizer, search_food, get_food_nutrition
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


@api_bp.route('/api/manual-record', methods=['POST'])
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
