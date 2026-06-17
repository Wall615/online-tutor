import random
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, TeacherProfile

auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')


def _captcha():
    """Generate captcha numbers for registration form."""
    a, b = random.randint(1, 9), random.randint(1, 9)
    return a, b, a + b


def _render_register():
    """Render register page with captcha."""
    a, b, _ = _captcha()
    return render_template('register.html', captcha_a=a, captcha_b=b)


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
            return _render_register()

        # Username validation: 2-10 chars, Chinese/English/dots only
        import re
        if len(username) < 2 or len(username) > 10:
            flash('用户名长度需在2到10个字符之间。', 'danger')
            return _render_register()
        if not re.match(r'^[一-鿿\a-zA-Z.]+$', username):
            flash('用户名只能包含汉字、英文字母和点号(.)。', 'danger')
            return _render_register()

        if len(password) < 6:
            flash('密码长度至少为6位。', 'danger')
            return _render_register()

        # Arithmetic CAPTCHA
        captcha_answer = request.form.get('captcha_answer', '').strip()
        captcha_a = request.form.get('captcha_a', '')
        captcha_b = request.form.get('captcha_b', '')
        expected = int(captcha_a) + int(captcha_b) if captcha_a and captcha_b else None
        if expected is None or captcha_answer != str(expected):
            flash('验证码计算错误，请重试。', 'danger')
            return _render_register()

        if len(email) > 120:
            flash('邮箱不能超过120个字符。', 'danger')
            return _render_register()

        if User.query.filter_by(username=username).first():
            flash('用户名已被注册。', 'danger')
            return _render_register()

        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册。', 'danger')
            return _render_register()

        if role not in ('student', 'teacher', 'parent'):
            flash('无效的角色选择。', 'danger')
            return _render_register()

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Get user.id

        # Create teacher profile if registering as teacher
        if role == 'teacher':
            profile = TeacherProfile(user_id=user.id)
            db.session.add(profile)

        db.session.commit()
        login_user(user)
        flash(f'注册成功！欢迎加入师说，{user.username}。', 'success')

        if role == 'teacher':
            flash('请先完善教师资料后再发布课程。', 'info')
            return redirect(url_for('course.edit_teacher_profile'))
        elif role == 'parent':
            flash('请先绑定学生账号以查看学习情况。', 'info')
            return redirect(url_for('parent.bind_student'))
        return redirect(url_for('course.index'))

    return _render_register()


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


@auth_bp.route('/delete-account')
@login_required
def delete_account():
    """User deletes their own account"""
    user_id = current_user.id
    username = current_user.username
    logout_user()
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        current_app.logger.info(f'User self-deleted: {username} (id={user_id})')
    flash('你的账号已成功注销。', 'info')
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
