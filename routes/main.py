from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import MealRecord, DailyGoal, ChatHistory, MealPlan
from datetime import date, timedelta
from ai.nutrition_analysis import NutritionAnalyzer
from ai.ai_nutritionist import AINutritionist
from config import Config

main_bp = Blueprint('main', __name__)


def get_ai_config():
    return {
        'AI_MODE': Config.AI_MODE,
        'LLM_API_KEY': Config.LLM_API_KEY,
        'LLM_API_BASE': Config.LLM_API_BASE,
        'LLM_MODEL': Config.LLM_MODEL,
        'VISION_MODEL': Config.VISION_MODEL,
    }


def _get_meal_status(today_meals):
    """Calculate meal status for breakfast/lunch/dinner.
    Returns dict with status: 'recorded', 'skipped', 'missing'
    """
    status = {
        'breakfast': {'status': 'missing', 'record': None},
        'lunch': {'status': 'missing', 'record': None},
        'dinner': {'status': 'missing', 'record': None},
        'snack': {'status': 'missing', 'record': None},
    }

    for meal in today_meals:
        mt = meal.meal_type
        if mt in status:
            if meal.skipped:
                status[mt]['status'] = 'skipped'
            else:
                status[mt]['status'] = 'recorded'
                status[mt]['record'] = meal

    # Count real meals (not skipped, not snack)
    real_meals = sum(1 for mt in ['breakfast', 'lunch', 'dinner']
                     if status[mt]['status'] == 'recorded')
    skipped_meals = sum(1 for mt in ['breakfast', 'lunch', 'dinner']
                        if status[mt]['status'] == 'skipped')
    status['real_count'] = real_meals
    status['skipped_count'] = skipped_meals
    status['total_expected'] = 3  # breakfast, lunch, dinner
    status['completion_rate'] = round(
        real_meals / max(status['total_expected'] - skipped_meals, 1) * 100
    ) if (status['total_expected'] - skipped_meals) > 0 else 100

    return status


@main_bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    all_today = MealRecord.query.filter_by(
        user_id=current_user.id
    ).filter(
        MealRecord.created_at >= today.strftime('%Y-%m-%d')
    ).order_by(MealRecord.created_at.desc()).all()

    # Separate real records from skipped
    meals_today = [m for m in all_today if not m.skipped]
    meal_status = _get_meal_status(all_today)

    # Calculate today's totals
    analyzer = NutritionAnalyzer(mode=Config.AI_MODE)
    daily_analysis = analyzer.analyze_daily_summary(meals_today)

    # Add price
    daily_price = sum(m.price or 0 for m in meals_today)
    daily_analysis['total_price'] = round(daily_price, 2)

    user_info = {
        'height': current_user.height,
        'weight': current_user.weight,
        'age': current_user.age,
        'gender': current_user.gender,
        'goal': current_user.goal,
    }

    # Recent 7 days data for chart
    week_data = {
        'labels': [], 'calories': [], 'protein': [], 'fat': [], 'carbs': [],
        'price': []
    }
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        week_data['labels'].append(d.strftime('%m/%d'))
        day_meals = MealRecord.query.filter_by(
            user_id=current_user.id, skipped=False
        ).filter(
            MealRecord.created_at >= d.strftime('%Y-%m-%d'),
            MealRecord.created_at < (d + timedelta(days=1)).strftime('%Y-%m-%d')
        ).all()

        day_cal = sum(m.get_nutrition().get('calories', 0) for m in day_meals)
        day_protein = sum(m.get_nutrition().get('protein', 0) for m in day_meals)
        day_fat = sum(m.get_nutrition().get('fat', 0) for m in day_meals)
        day_carbs = sum(m.get_nutrition().get('carbs', 0) for m in day_meals)
        day_price = sum(m.price or 0 for m in day_meals)

        week_data['calories'].append(round(day_cal))
        week_data['protein'].append(round(day_protein, 1))
        week_data['fat'].append(round(day_fat, 1))
        week_data['carbs'].append(round(day_carbs, 1))
        week_data['price'].append(round(day_price, 1))

    # Meal plan for today
    today_plan = MealPlan.query.filter_by(
        user_id=current_user.id, date=today
    ).first()

    return render_template(
        'dashboard.html',
        meals_today=meals_today,
        meal_status=meal_status,
        daily_analysis=daily_analysis,
        daily_price=daily_price,
        week_data=week_data,
        today_plan=today_plan,
        user_info=user_info
    )


@main_bp.route('/nutritionist')
@login_required
def nutritionist():
    """AI Nutritionist chat page"""
    chat_history = ChatHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(ChatHistory.created_at.desc()).limit(30).all()
    chat_history = list(reversed(chat_history))

    return render_template('nutritionist.html', chat_history=chat_history)


@main_bp.route('/report')
@login_required
def report():
    """Nutrition trend report"""
    today = date.today()

    # 30-day data
    month_data = {
        'labels': [], 'calories': [], 'protein': [], 'fat': [], 'carbs': [],
        'price': []
    }
    meal_completion = {'recorded': 0, 'skipped': 0, 'missing': 0, 'total_days': 0}

    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        month_data['labels'].append(d.strftime('%m/%d'))

        day_meals = MealRecord.query.filter_by(
            user_id=current_user.id, skipped=False
        ).filter(
            MealRecord.created_at >= d.strftime('%Y-%m-%d'),
            MealRecord.created_at < (d + timedelta(days=1)).strftime('%Y-%m-%d')
        ).all()

        day_all = MealRecord.query.filter_by(
            user_id=current_user.id
        ).filter(
            MealRecord.created_at >= d.strftime('%Y-%m-%d'),
            MealRecord.created_at < (d + timedelta(days=1)).strftime('%Y-%m-%d')
        ).all()

        day_cal = sum(m.get_nutrition().get('calories', 0) for m in day_meals)
        day_protein = sum(m.get_nutrition().get('protein', 0) for m in day_meals)
        day_fat = sum(m.get_nutrition().get('fat', 0) for m in day_meals)
        day_carbs = sum(m.get_nutrition().get('carbs', 0) for m in day_meals)
        day_price = sum(m.price or 0 for m in day_meals)

        month_data['calories'].append(round(day_cal))
        month_data['protein'].append(round(day_protein, 1))
        month_data['fat'].append(round(day_fat, 1))
        month_data['carbs'].append(round(day_carbs, 1))
        month_data['price'].append(round(day_price, 1))

        # Meal completion stats (only for days that have some data)
        if day_all:
            meal_completion['total_days'] += 1
            for mt in ['breakfast', 'lunch', 'dinner']:
                mt_records = [m for m in day_all if m.meal_type == mt]
                if any(m.skipped for m in mt_records):
                    meal_completion['skipped'] += 1
                elif any(not m.skipped for m in mt_records):
                    meal_completion['recorded'] += 1
                else:
                    meal_completion['missing'] += 1

    # Calculate averages for days with data
    days_with_data = sum(1 for c in month_data['calories'] if c > 0)
    if days_with_data > 0:
        avg_calories = round(sum(month_data['calories']) / days_with_data)
        avg_protein = round(sum(month_data['protein']) / days_with_data, 1)
        avg_fat = round(sum(month_data['fat']) / days_with_data, 1)
        avg_carbs = round(sum(month_data['carbs']) / days_with_data, 1)
        avg_price = round(sum(month_data['price']) / days_with_data, 1)
        total_spending = round(sum(month_data['price']), 1)
    else:
        avg_calories = avg_protein = avg_fat = avg_carbs = avg_price = total_spending = 0

    averages = {
        'calories': avg_calories,
        'protein': avg_protein,
        'fat': avg_fat,
        'carbs': avg_carbs,
        'price': avg_price,
        'total_spending': total_spending,
        'days_with_data': days_with_data,
    }

    # Meal type distribution (7 days)
    meal_type_stats = {'breakfast': 0, 'lunch': 0, 'dinner': 0, 'snack': 0}
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_meals = MealRecord.query.filter_by(
            user_id=current_user.id, skipped=False
        ).filter(
            MealRecord.created_at >= d.strftime('%Y-%m-%d'),
            MealRecord.created_at < (d + timedelta(days=1)).strftime('%Y-%m-%d')
        ).all()
        for m in day_meals:
            if m.meal_type in meal_type_stats:
                meal_type_stats[m.meal_type] += 1

    # Per-meal-type price stats (30 days)
    meal_price_stats = {'breakfast': 0, 'lunch': 0, 'dinner': 0, 'snack': 0}
    meal_count_stats = {'breakfast': 0, 'lunch': 0, 'dinner': 0, 'snack': 0}
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        day_meals = MealRecord.query.filter_by(
            user_id=current_user.id, skipped=False
        ).filter(
            MealRecord.created_at >= d.strftime('%Y-%m-%d'),
            MealRecord.created_at < (d + timedelta(days=1)).strftime('%Y-%m-%d')
        ).all()
        for m in day_meals:
            if m.meal_type in meal_price_stats:
                meal_price_stats[m.meal_type] += m.price or 0
                meal_count_stats[m.meal_type] += 1

    # Calculate average price per meal type
    avg_meal_price = {}
    for mt in meal_price_stats:
        if meal_count_stats[mt] > 0:
            avg_meal_price[mt] = round(meal_price_stats[mt] / meal_count_stats[mt], 1)
        else:
            avg_meal_price[mt] = 0

    return render_template(
        'report.html',
        month_data=month_data,
        averages=averages,
        meal_type_stats=meal_type_stats,
        meal_completion=meal_completion,
        avg_meal_price=avg_meal_price,
    )
