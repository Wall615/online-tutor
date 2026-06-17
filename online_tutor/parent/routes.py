from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, ParentStudent, Booking, Payment

parent_bp = Blueprint('parent', __name__, template_folder='../templates/parent')


@parent_bp.route('/')
@login_required
def dashboard():
    """Parent dashboard showing bound students' learning records"""
    if not current_user.is_parent():
        flash('只有家长可以访问此页面。', 'danger')
        return redirect(url_for('course.index'))

    bindings = ParentStudent.query.filter_by(parent_id=current_user.id).all()
    students = [db.session.get(User, b.student_id) for b in bindings]

    return render_template('parent_dashboard.html', students=students, bindings=bindings)


@parent_bp.route('/bind', methods=['GET', 'POST'])
@login_required
def bind_student():
    """Parent binds a student account"""
    if not current_user.is_parent():
        flash('只有家长可以访问此页面。', 'danger')
        return redirect(url_for('course.index'))

    if request.method == 'POST':
        student_username = request.form.get('student_username', '').strip()

        student = User.query.filter_by(username=student_username, role='student').first()
        if not student:
            flash('未找到该学生账号，请确认用户名是否正确。', 'danger')
            return render_template('bind_student.html')

        existing = ParentStudent.query.filter_by(parent_id=current_user.id, student_id=student.id).first()
        if existing:
            flash('你已经绑定过该学生。', 'warning')
            return redirect(url_for('parent.dashboard'))

        binding = ParentStudent(parent_id=current_user.id, student_id=student.id)
        db.session.add(binding)
        db.session.commit()
        flash(f'成功绑定学生 {student.username}！', 'success')
        return redirect(url_for('parent.dashboard'))

    # GET: show existing bindings
    bindings = ParentStudent.query.filter_by(parent_id=current_user.id).all()
    students = [db.session.get(User, b.student_id) for b in bindings]
    return render_template('bind_student.html', students=students)


@parent_bp.route('/student/<int:student_id>/bookings')
@login_required
def student_bookings(student_id):
    """Parent views a bound student's bookings"""
    if not current_user.is_parent():
        flash('只有家长可以访问此页面。', 'danger')
        return redirect(url_for('course.index'))

    # Verify binding
    binding = ParentStudent.query.filter_by(parent_id=current_user.id, student_id=student_id).first()
    if not binding:
        flash('未绑定该学生，请先绑定。', 'danger')
        return redirect(url_for('parent.bind_student'))

    student = db.session.get(User, student_id)
    bookings = Booking.query.filter_by(student_id=student_id).order_by(Booking.created_at.desc()).all()

    return render_template('student_bookings.html', student=student, bookings=bookings)


@parent_bp.route('/student/<int:student_id>/payments')
@login_required
def student_payments(student_id):
    """Parent views a bound student's payment records"""
    if not current_user.is_parent():
        flash('只有家长可以访问此页面。', 'danger')
        return redirect(url_for('course.index'))

    binding = ParentStudent.query.filter_by(parent_id=current_user.id, student_id=student_id).first()
    if not binding:
        flash('未绑定该学生，请先绑定。', 'danger')
        return redirect(url_for('parent.bind_student'))

    student = db.session.get(User, student_id)
    payments = Payment.query.filter_by(student_id=student_id).order_by(Payment.paid_at.desc()).all()

    return render_template('student_payments.html', student=student, payments=payments)
