from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date
import json

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    height = db.Column(db.Float, nullable=True)   # cm
    weight = db.Column(db.Float, nullable=True)   # kg
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), nullable=True)  # male / female
    goal = db.Column(db.String(20), nullable=True, default='maintain')  # lose / gain / maintain
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    meal_records = db.relationship('MealRecord', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    daily_goals = db.relationship('DailyGoal', backref='user', lazy='dynamic',
                                  cascade='all, delete-orphan')
    chat_history = db.relationship('ChatHistory', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    meal_plans = db.relationship('MealPlan', backref='user', lazy='dynamic',
                                 cascade='all, delete-orphan')

    def get_today_goals(self):
        today = date.today()
        goal = DailyGoal.query.filter_by(
            user_id=self.id, date=today
        ).first()
        if not goal:
            goal = DailyGoal(
                user_id=self.id,
                date=today,
                target_calories=2000,
                target_protein=60,
                target_fat=65,
                target_carbs=300
            )
            db.session.add(goal)
            db.session.commit()
        return goal


class MealRecord(db.Model):
    __tablename__ = 'meal_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)  # breakfast/lunch/dinner/snack
    image_path = db.Column(db.String(500), nullable=True)
    recognized_foods = db.Column(db.Text, nullable=True)  # JSON
    nutrition_data = db.Column(db.Text, nullable=True)    # JSON
    price = db.Column(db.Float, nullable=True)            # meal cost
    input_method = db.Column(db.String(20), default='photo')  # 'photo' or 'manual'
    skipped = db.Column(db.Boolean, default=False)        # skipped meal (oversleep etc)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_foods(self):
        if self.recognized_foods:
            return json.loads(self.recognized_foods)
        return []

    def get_nutrition(self):
        if self.nutrition_data:
            return json.loads(self.nutrition_data)
        return {}

    def set_foods(self, foods_list):
        self.recognized_foods = json.dumps(foods_list, ensure_ascii=False)

    def set_nutrition(self, nutrition_dict):
        self.nutrition_data = json.dumps(nutrition_dict, ensure_ascii=False)


class DailyGoal(db.Model):
    __tablename__ = 'daily_goals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    target_calories = db.Column(db.Float, default=2000)
    target_protein = db.Column(db.Float, default=60)
    target_fat = db.Column(db.Float, default=65)
    target_carbs = db.Column(db.Float, default=300)

    __table_args__ = (db.UniqueConstraint('user_id', 'date'),)


class ChatHistory(db.Model):
    __tablename__ = 'chat_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user / assistant
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MealPlan(db.Model):
    __tablename__ = 'meal_plans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)
    foods = db.Column(db.Text, nullable=True)         # JSON
    nutrition_summary = db.Column(db.Text, nullable=True)  # JSON
    generated_by = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_foods(self):
        if self.foods:
            return json.loads(self.foods)
        return []

    def get_nutrition(self):
        if self.nutrition_summary:
            return json.loads(self.nutrition_summary)
        return {}
