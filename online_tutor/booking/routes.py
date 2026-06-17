from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from flask import current_app
from models import db, cst_now, Booking, Course, Payment, User, ParentStudent

booking_bp = Blueprint('booking', __name__, template_folder='../templates/booking')


@booking_bp.route('/create/<int:course_id>', methods=['GET', 'POST'])
@login_required
def create(course_id):
    """Student or parent creates a booking for a course"""
    if not current_user.is_student() and not current_user.is_parent():
        flash('只有学生或家长可以预约课程。', 'danger')
        return redirect(url_for('course.index'))

    course = db.session.get(Course, course_id)
    if not course or course.status != 'active':
        flash('课程不可预约。', 'danger')
        return redirect(url_for('course.index'))

    # For parents, get bound students for the selection dropdown
    bound_students = []
    if current_user.is_parent():
        bindings = ParentStudent.query.filter_by(parent_id=current_user.id).all()
        bound_students = [db.session.get(User, b.student_id) for b in bindings]
        if not bound_students:
            flash('请先绑定学生账号后再预约课程。', 'warning')
            return redirect(url_for('parent.bind_student'))

    if request.method == 'POST':
        scheduled_time_str = request.form.get('scheduled_time', '').strip()
        if not scheduled_time_str:
            flash('请选择上课时间。', 'danger')
            return render_template('booking_create.html', course=course, bound_students=bound_students)

        # Determine the actual student for this booking
        if current_user.is_parent():
            student_id_str = request.form.get('student_id', '').strip()
            if not student_id_str:
                flash('请选择上课的学生。', 'danger')
                return render_template('booking_create.html', course=course, bound_students=bound_students)
            student_id = int(student_id_str)
            # Validate this student is bound to this parent
            binding = ParentStudent.query.filter_by(parent_id=current_user.id, student_id=student_id).first()
            if not binding:
                flash('无效的学生选择。', 'danger')
                return render_template('booking_create.html', course=course, bound_students=bound_students)
        else:
            student_id = current_user.id

        try:
            scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('时间格式不正确。', 'danger')
            return render_template('booking_create.html', course=course, bound_students=bound_students)

        if scheduled_time <= cst_now():
            flash('上课时间必须在当前时间之后。', 'danger')
            return render_template('booking_create.html', course=course, bound_students=bound_students)

        booking = Booking(
            student_id=student_id,
            teacher_id=course.teacher_id,
            course_id=course_id,
            scheduled_time=scheduled_time,
            status='pending'
        )
        db.session.add(booking)
        db.session.flush()  # Get booking.id

        # Create pending payment
        payment = Payment(
            booking_id=booking.id,
            student_id=student_id,
            amount=course.price,
            status='pending'
        )
        db.session.add(payment)
        db.session.commit()

        current_app.logger.info(f'Booking created: id={booking.id} student={student_id} course={course_id}')
        flash('预约已提交，请完成支付。', 'success')
        return redirect(url_for('payment.pay', booking_id=booking.id))

    return render_template('booking_create.html', course=course, bound_students=bound_students)


@booking_bp.route('/my-bookings')
@login_required
def my_bookings():
    """Student views their bookings, or parent views all children's bookings"""
    if not current_user.is_student() and not current_user.is_parent():
        flash('只有学生或家长可以访问此页面。', 'danger')
        return redirect(url_for('course.index'))

    if current_user.is_parent():
        # Get all bound student IDs
        bindings = ParentStudent.query.filter_by(parent_id=current_user.id).all()
        student_ids = [b.student_id for b in bindings]
        bookings = Booking.query.filter(Booking.student_id.in_(student_ids)).order_by(Booking.created_at.desc()).all() if student_ids else []
        # Build student lookup dict for template
        students_map = {}
        if student_ids:
            students = User.query.filter(User.id.in_(student_ids)).all()
            students_map = {u.id: u for u in students}
        return render_template('my_bookings.html', bookings=bookings, students_map=students_map, is_parent=True)
    else:
        bookings = Booking.query.filter_by(student_id=current_user.id).order_by(Booking.created_at.desc()).all()
        return render_template('my_bookings.html', bookings=bookings)


@booking_bp.route('/teacher')
@login_required
def teacher_bookings():
    """Teacher views bookings for their courses"""
    if not current_user.is_teacher():
        flash('只有教师可以访问此页面。', 'danger')
        return redirect(url_for('course.index'))

    bookings = Booking.query.filter_by(teacher_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('teacher_bookings.html', bookings=bookings)


@booking_bp.route('/<int:booking_id>/confirm')
@login_required
def confirm(booking_id):
    """Teacher confirms a booking"""
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.teacher_id != current_user.id:
        flash('无权操作。', 'danger')
        return redirect(url_for('booking.teacher_bookings'))

    if booking.status != 'pending':
        flash('只能确认待处理的预约。', 'warning')
        return redirect(url_for('booking.teacher_bookings'))

    # Check if payment is paid
    if booking.payment and booking.payment.status == 'paid':
        booking.status = 'confirmed'
        db.session.commit()
        flash('预约已确认。', 'success')
    else:
        flash('学生尚未完成支付，无法确认。', 'warning')

    return redirect(url_for('booking.teacher_bookings'))


@booking_bp.route('/<int:booking_id>/cancel')
@login_required
def cancel(booking_id):
    """Student or teacher cancels a booking"""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash('预约不存在。', 'danger')
        return redirect(url_for('course.index'))

    if current_user.id not in (booking.student_id, booking.teacher_id):
        # Also allow parent of the student to cancel
        if current_user.is_parent():
            binding = ParentStudent.query.filter_by(parent_id=current_user.id, student_id=booking.student_id).first()
            if not binding:
                flash('无权操作。', 'danger')
                return redirect(url_for('course.index'))
        else:
            flash('无权操作。', 'danger')
            return redirect(url_for('course.index'))

    if booking.status in ('cancelled', 'completed'):
        flash('此预约无法取消。', 'warning')
    else:
        booking.status = 'cancelled'
        if booking.payment:
            booking.payment.status = 'refunded'
        db.session.commit()
        flash('预约已取消。', 'info')

    if current_user.is_student() or current_user.is_parent():
        return redirect(url_for('booking.my_bookings'))
    return redirect(url_for('booking.teacher_bookings'))


@booking_bp.route('/<int:booking_id>/complete')
@login_required
def complete(booking_id):
    """Teacher marks a booking as completed"""
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.teacher_id != current_user.id:
        flash('无权操作。', 'danger')
        return redirect(url_for('booking.teacher_bookings'))

    if booking.status == 'confirmed':
        booking.status = 'completed'
        db.session.commit()
        flash('课程已标记为完成。', 'success')
    else:
        flash('只能完成已确认的预约。', 'warning')

    return redirect(url_for('booking.teacher_bookings'))


@booking_bp.route('/calendar')
@login_required
def calendar():
    """Calendar view of bookings — server-rendered month grid"""
    import calendar as cal_mod
    year = request.args.get('year', cst_now().year, type=int)
    month = request.args.get('month', cst_now().month, type=int)

    # Clamp month
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    # Get bookings for this month
    if current_user.is_student():
        bookings = Booking.query.filter_by(student_id=current_user.id).all()
    elif current_user.is_teacher():
        bookings = Booking.query.filter_by(teacher_id=current_user.id).all()
    elif current_user.is_parent():
        bindings = ParentStudent.query.filter_by(parent_id=current_user.id).all()
        student_ids = [b.student_id for b in bindings]
        bookings = Booking.query.filter(Booking.student_id.in_(student_ids)).all() if student_ids else []
    else:
        bookings = []

    # Build day → list of bookings map
    from collections import defaultdict
    day_bookings = defaultdict(list)
    for b in bookings:
        if b.scheduled_time.year == year and b.scheduled_time.month == month:
            day_bookings[b.scheduled_time.day].append(b)

    # Build calendar grid
    month_cal = cal_mod.monthcalendar(year, month)
    weeks = []
    for week in month_cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                week_data.append({
                    'day': day,
                    'bookings': day_bookings.get(day, []),
                    'is_today': (day == cst_now().day and month == cst_now().month and year == cst_now().year)
                })
        weeks.append(week_data)

    month_names = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月']
    return render_template('calendar.html',
                           weeks=weeks,
                           year=year,
                           month=month,
                           month_name=month_names[month - 1],
                           prev_month=month - 1 if month > 1 else 12,
                           prev_year=year if month > 1 else year - 1,
                           next_month=month + 1 if month < 12 else 1,
                           next_year=year if month < 12 else year + 1)


@booking_bp.route('/calendar/events')
@login_required
def calendar_events():
    """Return booking events as JSON for FullCalendar"""
    if current_user.is_student():
        bookings = Booking.query.filter_by(student_id=current_user.id).all()
    elif current_user.is_teacher():
        bookings = Booking.query.filter_by(teacher_id=current_user.id).all()
    elif current_user.is_parent():
        bindings = ParentStudent.query.filter_by(parent_id=current_user.id).all()
        student_ids = [b.student_id for b in bindings]
        bookings = Booking.query.filter(Booking.student_id.in_(student_ids)).all() if student_ids else []
    else:
        bookings = []

    status_colors = {
        'pending': '#D4A853',
        'confirmed': '#4A6FA5',
        'completed': '#7BA07B',
        'cancelled': '#C46B6B'
    }

    events = []
    for b in bookings:
        events.append({
            'id': b.id,
            'title': b.course.title,
            'start': b.scheduled_time.strftime('%Y-%m-%dT%H:%M'),
            'backgroundColor': status_colors.get(b.status, '#6B5E53'),
            'borderColor': status_colors.get(b.status, '#6B5E53'),
            'extendedProps': {
                'status': b.status,
                'student': b.student.username,
                'teacher': b.teacher_ref.username
            }
        })
    return jsonify(events)
