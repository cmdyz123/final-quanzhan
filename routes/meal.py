import os
import uuid
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, MealRecord, MealPlan
from ai.food_recognition import FoodRecognizer, search_food, get_food_nutrition, get_all_food_names
from ai.nutrition_analysis import NutritionAnalyzer
from ai.ai_nutritionist import AINutritionist
from config import Config

meal_bp = Blueprint('meal', __name__)

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


@meal_bp.route('/meal/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'GET':
        all_foods = get_all_food_names()
        return render_template('meal_upload.html', all_foods=all_foods)

    # Check if this is a manual input submission
    if request.form.get('input_method') == 'manual':
        return _handle_manual_input()

    # POST - handle file upload
    if 'food_image' not in request.files:
        flash('请选择图片文件', 'error')
        all_foods = get_all_food_names()
        return render_template('meal_upload.html', all_foods=all_foods)

    file = request.files['food_image']
    if file.filename == '':
        flash('请选择图片文件', 'error')
        all_foods = get_all_food_names()
        return render_template('meal_upload.html', all_foods=all_foods)

    if not allowed_file(file.filename):
        flash('仅支持PNG、JPG、JPEG、GIF、WebP格式', 'error')
        all_foods = get_all_food_names()
        return render_template('meal_upload.html', all_foods=all_foods)

    meal_type = request.form.get('meal_type', 'lunch')
    notes = request.form.get('notes', '')
    price = request.form.get('price', type=float)

    # Save image
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Recognize food
    ai_config = get_ai_config()
    recognizer = FoodRecognizer(
        mode=ai_config['AI_MODE'],
        api_key=ai_config['LLM_API_KEY'],
        api_base=ai_config['LLM_API_BASE'],
        model=ai_config['VISION_MODEL']
    )
    foods = recognizer.recognize(filepath)

    # Analyze nutrition
    user_info = {
        'height': current_user.height,
        'weight': current_user.weight,
        'age': current_user.age,
        'gender': current_user.gender,
        'goal': current_user.goal,
    }
    analyzer = NutritionAnalyzer(mode=ai_config['AI_MODE'])
    analysis = analyzer.analyze_meal(foods, user_info)

    # Save meal record
    meal = MealRecord(
        user_id=current_user.id,
        meal_type=meal_type,
        image_path=filepath,
        price=price,
        input_method='photo',
        notes=notes
    )
    meal.set_foods(foods)
    meal.set_nutrition(analysis['totals'])
    db.session.add(meal)
    db.session.commit()

    flash('餐食分析完成！', 'success')
    all_foods = get_all_food_names()
    return render_template(
        'meal_upload.html',
        analysis_result=analysis,
        meal_type=meal_type,
        all_foods=all_foods
    )


def _handle_manual_input():
    """Process manual food name input"""
    meal_type = request.form.get('meal_type', 'lunch')
    notes = request.form.get('notes', '')
    price = request.form.get('price', type=float)

    # Parse food entries from form
    food_names = request.form.getlist('food_name[]')
    food_portions = request.form.getlist('food_portion[]')

    if not food_names or len(food_names) == 0:
        flash('请至少添加一种食物', 'error')
        return redirect(url_for('meal.upload'))

    foods_result = []
    total_nutrition = {'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0}

    for i, name in enumerate(food_names):
        name = name.strip()
        if not name:
            continue
        portion = float(food_portions[i]) if i < len(food_portions) and food_portions[i] else 100

        nutrition = get_food_nutrition(name)
        if not nutrition:
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

    # Save
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

    flash('餐食记录成功！', 'success')
    all_foods = get_all_food_names()
    return render_template(
        'meal_upload.html',
        analysis_result=analysis,
        meal_type=meal_type,
        all_foods=all_foods
    )


@meal_bp.route('/meal/log')
@login_required
def meal_log():
    """View all meal records with optional date filter"""
    from datetime import datetime

    date_str = request.args.get('date', '')
    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = None
    else:
        filter_date = None

    today = date.today()
    if filter_date:
        meals = MealRecord.query.filter_by(
            user_id=current_user.id
        ).filter(
            MealRecord.created_at >= filter_date.strftime('%Y-%m-%d'),
            MealRecord.created_at < (filter_date + timedelta(days=1)).strftime('%Y-%m-%d')
        ).order_by(MealRecord.created_at.desc()).all()
        view_date = filter_date
        is_today = (filter_date == today)
    else:
        meals = MealRecord.query.filter_by(
            user_id=current_user.id
        ).order_by(MealRecord.created_at.desc()).limit(50).all()
        view_date = today
        is_today = True

    # Calculate spending for viewed date
    today_meals = [m for m in meals if m.created_at.date() == view_date]
    today_total_price = sum(m.price or 0 for m in today_meals)

    # Calculate week spending
    week_total_price = sum(m.price or 0 for m in meals
                           if (date.today() - m.created_at.date()).days < 7)

    return render_template(
        'meal_log.html',
        meals=meals,
        view_date=view_date,
        view_date_str=view_date.strftime('%Y-%m-%d'),
        is_today=is_today,
        prev_date=(view_date - timedelta(days=1)).strftime('%Y-%m-%d'),
        next_date=(view_date + timedelta(days=1)).strftime('%Y-%m-%d')
        if not is_today else None,
        today_total_price=today_total_price,
        week_total_price=week_total_price
    )


@meal_bp.route('/meal/<int:meal_id>')
@login_required
def meal_detail(meal_id):
    """View single meal detail"""
    meal = MealRecord.query.get_or_404(meal_id)
    if meal.user_id != current_user.id:
        flash('无权访问', 'error')
        return redirect(url_for('meal.meal_log'))
    return render_template('meal_detail.html', meal=meal)


@meal_bp.route('/meal/<int:meal_id>/delete', methods=['POST'])
@login_required
def meal_delete(meal_id):
    """Delete a meal record"""
    meal = MealRecord.query.get_or_404(meal_id)
    if meal.user_id != current_user.id:
        flash('无权操作', 'error')
        return redirect(url_for('meal.meal_log'))

    # Delete image file
    if meal.image_path and os.path.exists(meal.image_path):
        os.remove(meal.image_path)

    db.session.delete(meal)
    db.session.commit()
    flash('餐食记录已删除', 'info')
    return redirect(url_for('meal.meal_log'))


@meal_bp.route('/meal/skip', methods=['POST'])
@login_required
def meal_skip():
    """Mark a meal type as skipped for today (e.g., overslept breakfast)"""
    meal_type = request.form.get('meal_type', '')
    if meal_type not in ('breakfast', 'lunch', 'dinner'):
        flash('无效的餐食类型', 'error')
        return redirect(url_for('main.dashboard'))

    today = date.today()

    # Check if already has a real record for this meal type
    existing = MealRecord.query.filter_by(
        user_id=current_user.id, meal_type=meal_type
    ).filter(
        MealRecord.created_at >= today.strftime('%Y-%m-%d'),
        MealRecord.skipped == False
    ).first()

    if existing:
        flash(f'今天已经记录了{meal_type}，无需跳过', 'info')
        return redirect(url_for('main.dashboard'))

    # Check if already marked as skipped
    already_skipped = MealRecord.query.filter_by(
        user_id=current_user.id, meal_type=meal_type, skipped=True
    ).filter(
        MealRecord.created_at >= today.strftime('%Y-%m-%d')
    ).first()

    if already_skipped:
        flash(f'{meal_type}已标记为跳过', 'info')
        return redirect(url_for('main.dashboard'))

    # Create skip record
    skip_record = MealRecord(
        user_id=current_user.id,
        meal_type=meal_type,
        skipped=True,
        input_method='manual',
        price=0,
        notes=f'跳过{meal_type}（如睡过头等）'
    )
    skip_record.set_foods([])
    skip_record.set_nutrition({'calories': 0, 'protein': 0, 'fat': 0, 'carbs': 0, 'fiber': 0})
    db.session.add(skip_record)
    db.session.commit()

    type_labels = {'breakfast': '早餐', 'lunch': '午餐', 'dinner': '晚餐'}
    flash(f'已标记{type_labels.get(meal_type, meal_type)}为跳过', 'success')
    return redirect(url_for('main.dashboard'))


@meal_bp.route('/meal/undo-skip', methods=['POST'])
@login_required
def meal_undo_skip():
    """Undo a skip record"""
    meal_type = request.form.get('meal_type', '')
    if meal_type not in ('breakfast', 'lunch', 'dinner'):
        flash('无效的餐食类型', 'error')
        return redirect(url_for('main.dashboard'))

    today = date.today()
    skip_record = MealRecord.query.filter_by(
        user_id=current_user.id, meal_type=meal_type, skipped=True
    ).filter(
        MealRecord.created_at >= today.strftime('%Y-%m-%d')
    ).first()

    if skip_record:
        db.session.delete(skip_record)
        db.session.commit()
        type_labels = {'breakfast': '早餐', 'lunch': '午餐', 'dinner': '晚餐'}
        flash(f'已撤销{type_labels.get(meal_type, meal_type)}的跳过标记', 'success')
    else:
        flash('未找到跳过记录', 'info')

    return redirect(url_for('main.dashboard'))


@meal_bp.route('/meal-plan')
@login_required
def meal_plan():
    """Generate and view personalized meal plan"""
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

    # Get today's meals (excluding skipped)
    today = date.today()
    today_meals = MealRecord.query.filter_by(
        user_id=current_user.id, skipped=False
    ).filter(
        MealRecord.created_at >= today.strftime('%Y-%m-%d')
    ).all()

    # Generate plan
    targets = {'calories': 2000, 'protein': 60, 'fat': 65, 'carbs': 300}
    if current_user.goal == 'lose':
        targets['calories'] = 1600
    elif current_user.goal == 'gain':
        targets['calories'] = 2600

    plan = nutritionist.generate_meal_plan(
        current_user.id, user_info, today_meals, targets['calories']
    )

    # Save plan to DB
    today_plan = MealPlan.query.filter_by(
        user_id=current_user.id, date=today
    ).first()

    if not today_plan:
        for meal_type, meal_data in plan.get('meal_plan', {}).items():
            db_plan = MealPlan(
                user_id=current_user.id,
                date=today,
                meal_type=meal_type,
                foods=str(meal_data.get('foods', [])),
                nutrition_summary=str({'total_calories': meal_data.get('total_calories', 0)}),
                generated_by=f"AINutritionist-{ai_config['AI_MODE']}"
            )
            db.session.add(db_plan)
        db.session.commit()

    return render_template('meal_plan.html', plan=plan, targets=targets)
