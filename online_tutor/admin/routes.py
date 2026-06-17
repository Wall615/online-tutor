from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from sqlalchemy import extract, func
from models import db, cst_now, User, TeacherProfile, Course, Booking, Payment

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('需要管理员权限。', 'danger')
            return redirect(url_for('course.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard with statistics"""
    stats = {
        'total_users': User.query.count(),
        'total_teachers': User.query.filter_by(role='teacher').count(),
        'total_students': User.query.filter_by(role='student').count(),
        'total_parents': User.query.filter_by(role='parent').count(),
        'total_courses': Course.query.count(),
        'active_courses': Course.query.filter_by(status='active').count(),
        'total_bookings': Booking.query.count(),
        'completed_bookings': Booking.query.filter_by(status='completed').count(),
        'total_revenue': db.session.query(db.func.sum(Payment.amount)).filter(Payment.status == 'paid').scalar() or 0,
        'pending_verifications': TeacherProfile.query.filter_by(verified=False).count(),
    }

    # Monthly revenue for current year (line chart)
    current_year = cst_now().year
    monthly_revenue = []
    for month in range(1, 13):
        result = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'paid',
            extract('year', Payment.paid_at) == current_year,
            extract('month', Payment.paid_at) == month
        ).scalar()
        monthly_revenue.append(float(result) if result else 0.0)

    # Booking status counts (bar chart)
    booking_status = db.session.query(
        Booking.status, func.count(Booking.id)
    ).group_by(Booking.status).all()
    booking_status_map = {s: c for s, c in booking_status}

    # Recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    return render_template('admin_dashboard.html',
                           stats=stats,
                           recent_users=recent_users,
                           monthly_revenue=monthly_revenue,
                           booking_status_map=booking_status_map)


@admin_bp.route('/verify-teachers')
@admin_required
def verify_teachers():
    """List teachers pending verification"""
    profiles = TeacherProfile.query.order_by(TeacherProfile.verified.asc()).all()
    return render_template('verify_teachers.html', profiles=profiles)


@admin_bp.route('/verify-teacher/<int:profile_id>/<action>')
@admin_required
def verify_teacher(profile_id, action):
    """Verify or reject a teacher"""
    profile = db.session.get(TeacherProfile, profile_id)
    if not profile:
        flash('教师资料不存在。', 'danger')
        return redirect(url_for('admin.verify_teachers'))

    if action == 'approve':
        profile.verified = True
        db.session.commit()
        flash(f'已通过教师 {profile.user.username} 的审核。', 'success')
    elif action == 'reject':
        profile.verified = False
        db.session.commit()
        flash(f'已驳回教师 {profile.user.username} 的审核。', 'warning')

    return redirect(url_for('admin.verify_teachers'))


@admin_bp.route('/users')
@admin_required
def user_list():
    """List all users"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('user_list.html', users=users)


@admin_bp.route('/delete-user/<int:user_id>')
@admin_required
def delete_user(user_id):
    """Admin deletes a user"""
    if user_id == current_user.id:
        flash('不能删除自己的账号。', 'danger')
        return redirect(url_for('admin.user_list'))

    user = db.session.get(User, user_id)
    if not user:
        flash('用户不存在。', 'danger')
        return redirect(url_for('admin.user_list'))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    current_app.logger.info(f'Admin deleted user: {username} (id={user_id})')
    flash(f'已删除用户 {username}。', 'success')
    return redirect(url_for('admin.user_list'))


@admin_bp.route('/approve-courses')
@admin_required
def approve_courses():
    """List courses pending approval"""
    pending = Course.query.filter_by(approved=False).order_by(Course.created_at.desc()).all()
    approved = Course.query.filter_by(approved=True).order_by(Course.created_at.desc()).limit(10).all()
    return render_template('approve_courses.html', pending=pending, approved=approved)


@admin_bp.route('/approve-course/<int:course_id>')
@admin_required
def approve_course(course_id):
    """Approve a course"""
    course = db.session.get(Course, course_id)
    if not course:
        flash('课程不存在。', 'danger')
        return redirect(url_for('admin.approve_courses'))

    course.approved = True
    db.session.commit()
    current_app.logger.info(f'Admin approved course: {course.title} (id={course_id})')
    flash(f'已通过课程《{course.title}》的审核。', 'success')
    return redirect(url_for('admin.approve_courses'))
