import csv
import io

from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from models import MealRecord, DailyGoal, ChatHistory, MealPlan
from datetime import date, datetime, timedelta
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
    # Support date navigation via query param
    date_str = request.args.get('date', '')
    if date_str:
        try:
            view_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            view_date = date.today()
    else:
        view_date = date.today()

    today = view_date
    is_today = (view_date == date.today())

    all_today = MealRecord.query.filter_by(
        user_id=current_user.id
    ).filter(
        MealRecord.created_at >= today.strftime('%Y-%m-%d'),
        MealRecord.created_at < (today + timedelta(days=1)).strftime('%Y-%m-%d')
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
        view_date=view_date,
        view_date_str=view_date.strftime('%Y-%m-%d'),
        is_today=is_today,
        prev_date=(view_date - timedelta(days=1)).strftime('%Y-%m-%d'),
        next_date=(view_date + timedelta(days=1)).strftime('%Y-%m-%d')
        if not is_today else None,
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


@main_bp.route('/report/export')
@login_required
def report_export():
    """Export 30-day nutrition report as CSV."""
    today = date.today()
    start_date = today - timedelta(days=29)

    # Build 30-day data
    day_rows = []
    calories_all = []
    protein_all = []
    fat_all = []
    carbs_all = []
    price_all = []

    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        label = d.strftime('%Y-%m-%d')

        day_meals = MealRecord.query.filter_by(
            user_id=current_user.id, skipped=False
        ).filter(
            MealRecord.created_at >= d.strftime('%Y-%m-%d'),
            MealRecord.created_at < (d + timedelta(days=1)).strftime('%Y-%m-%d')
        ).all()

        day_cal = round(sum(m.get_nutrition().get('calories', 0) for m in day_meals))
        day_protein = round(sum(m.get_nutrition().get('protein', 0) for m in day_meals), 1)
        day_fat = round(sum(m.get_nutrition().get('fat', 0) for m in day_meals), 1)
        day_carbs = round(sum(m.get_nutrition().get('carbs', 0) for m in day_meals), 1)
        day_price = round(sum(m.price or 0 for m in day_meals), 1)

        calories_all.append(day_cal)
        protein_all.append(day_protein)
        fat_all.append(day_fat)
        carbs_all.append(day_carbs)
        price_all.append(day_price)

        # Per-meal-type calories
        meal_cal = {'breakfast': 0, 'lunch': 0, 'dinner': 0, 'snack': 0}
        meal_count = 0
        for m in day_meals:
            mt = m.meal_type
            if mt in meal_cal:
                meal_cal[mt] += m.get_nutrition().get('calories', 0)
                meal_count += 1

        day_rows.append({
            'date': label,
            'calories': day_cal, 'protein': day_protein, 'fat': day_fat,
            'carbs': day_carbs, 'price': day_price,
            'meal_count': meal_count,
            'breakfast_cal': round(meal_cal['breakfast']),
            'lunch_cal': round(meal_cal['lunch']),
            'dinner_cal': round(meal_cal['dinner']),
            'snack_cal': round(meal_cal['snack']),
        })

    # Averages
    days_with_data = sum(1 for c in calories_all if c > 0)
    if days_with_data > 0:
        avg_cal = round(sum(calories_all) / days_with_data)
        avg_protein = round(sum(protein_all) / days_with_data, 1)
        avg_fat = round(sum(fat_all) / days_with_data, 1)
        avg_carbs = round(sum(carbs_all) / days_with_data, 1)
        avg_price = round(sum(price_all) / days_with_data, 1)
        total_spend = round(sum(price_all), 1)
    else:
        avg_cal = avg_protein = avg_fat = avg_carbs = avg_price = total_spend = 0

    # Meal type stats
    meal_type_stats = {'breakfast': 0, 'lunch': 0, 'dinner': 0, 'snack': 0}
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
            mt = m.meal_type
            if mt in meal_type_stats:
                meal_type_stats[mt] += 1
                meal_price_stats[mt] += m.price or 0
                meal_count_stats[mt] += 1

    avg_mp = {}
    for mt in meal_price_stats:
        avg_mp[mt] = round(meal_price_stats[mt] / meal_count_stats[mt], 1) if meal_count_stats[mt] > 0 else 0

    # Write CSV
    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel
    w = csv.writer(output)

    w.writerow(['NutriSnap 营养报告 - 30日每日明细'])
    w.writerow(['日期范围', f'{start_date.strftime("%Y-%m-%d")} 至 {today.strftime("%Y-%m-%d")}'])
    w.writerow([])
    w.writerow(['日期', '热量(千卡)', '蛋白质(g)', '脂肪(g)', '碳水(g)', '消费(元)',
                '餐食数', '早餐热量', '午餐热量', '晚餐热量', '加餐热量'])
    for d in day_rows:
        w.writerow([d['date'], d['calories'], d['protein'], d['fat'], d['carbs'],
                    d['price'], d['meal_count'],
                    d['breakfast_cal'], d['lunch_cal'], d['dinner_cal'], d['snack_cal']])

    w.writerow([])
    w.writerow([])
    w.writerow(['汇总统计'])
    w.writerow(['指标', '数值'])
    w.writerow(['有效天数', days_with_data])
    w.writerow(['日均热量(千卡)', avg_cal])
    w.writerow(['日均蛋白质(g)', avg_protein])
    w.writerow(['日均脂肪(g)', avg_fat])
    w.writerow(['日均碳水(g)', avg_carbs])
    w.writerow(['日均消费(元)', avg_price])
    w.writerow(['30日总消费(元)', total_spend])

    w.writerow([])
    w.writerow([])
    w.writerow(['餐次分析'])
    w.writerow(['餐次', '记录次数', '平均价格(元)'])
    type_labels = {'breakfast': '早餐', 'lunch': '午餐', 'dinner': '晚餐', 'snack': '加餐'}
    for mt in ['breakfast', 'lunch', 'dinner', 'snack']:
        w.writerow([type_labels[mt], meal_type_stats[mt], avg_mp.get(mt, 0)])

    w.writerow([])
    w.writerow([])
    w.writerow(['用户信息'])
    w.writerow(['用户名', current_user.username])
    w.writerow(['身高(cm)', current_user.height or '未设置'])
    w.writerow(['体重(kg)', current_user.weight or '未设置'])
    w.writerow(['年龄', current_user.age or '未设置'])
    goal_map = {'lose': '减重', 'gain': '增肌', 'maintain': '维持体重'}
    w.writerow(['目标', goal_map.get(current_user.goal, '未设置')])

    filename = f'NutriSnap_Report_{start_date.strftime("%Y%m%d")}_{today.strftime("%Y%m%d")}.csv'
    output.seek(0)

    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'text/csv; charset=utf-8-sig'
        }
    )
