from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    if not username or not password:
        flash('请输入用户名和密码', 'error')
        return redirect(url_for('auth.index'))

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        flash(f'欢迎回来，{user.username}！', 'success')
        return redirect(url_for('main.dashboard'))

    flash('用户名或密码错误', 'error')
    return redirect(url_for('auth.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return render_template('register.html')

    # POST
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    password2 = request.form.get('password2', '')
    height = request.form.get('height', type=float)
    weight = request.form.get('weight', type=float)
    age = request.form.get('age', type=int)
    gender = request.form.get('gender', '')
    goal = request.form.get('goal', 'maintain')

    # Validation
    if not username or not email or not password:
        flash('请填写所有必填字段', 'error')
        return render_template('register.html')

    if password != password2:
        flash('两次密码输入不一致', 'error')
        return render_template('register.html')

    if len(password) < 6:
        flash('密码至少6位', 'error')
        return render_template('register.html')

    if User.query.filter_by(username=username).first():
        flash('用户名已存在', 'error')
        return render_template('register.html')

    if User.query.filter_by(email=email).first():
        flash('邮箱已被注册', 'error')
        return render_template('register.html')

    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        height=height,
        weight=weight,
        age=age,
        gender=gender,
        goal=goal
    )
    db.session.add(user)
    db.session.commit()

    flash('注册成功！请登录', 'success')
    return redirect(url_for('auth.index'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('auth.index'))
