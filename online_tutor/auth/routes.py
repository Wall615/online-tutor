from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, TeacherProfile

auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('course.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'student')

        # Validation
        if not username or not email or not password:
            flash('所有字段都必须填写。', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('密码长度至少为6位。', 'danger')
            return render_template('register.html')

        if len(username) > 80:
            flash('用户名不能超过80个字符。', 'danger')
            return render_template('register.html')

        if len(email) > 120:
            flash('邮箱不能超过120个字符。', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('用户名已被注册。', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册。', 'danger')
            return render_template('register.html')

        if role not in ('student', 'teacher', 'parent'):
            flash('无效的角色选择。', 'danger')
            return render_template('register.html')

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Get user.id

        # Create teacher profile if registering as teacher
        if role == 'teacher':
            profile = TeacherProfile(user_id=user.id)
            db.session.add(profile)

        db.session.commit()
        flash('注册成功！请登录。', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('course.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash('用户名或密码错误。', 'danger')
            return render_template('login.html')

        login_user(user)
        current_app.logger.info(f'User login: {user.username} ({user.role})')
        flash(f'欢迎回来，{user.username}！', 'success')

        # Redirect based on role
        if user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('course.index'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已成功退出登录。', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.phone = request.form.get('phone', '').strip()
        current_user.email = request.form.get('email', '').strip()
        db.session.commit()
        flash('个人资料已更新。', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('profile.html')


@auth_bp.route('/teacher/<int:user_id>')
def teacher_detail(user_id):
    """Public teacher profile page"""
    teacher = db.session.get(User, user_id)
    if not teacher or not teacher.is_teacher():
        flash('教师不存在。', 'danger')
        return redirect(url_for('course.index'))
    return render_template('teacher_detail.html', teacher=teacher)
