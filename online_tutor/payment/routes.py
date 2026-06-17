from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
from models import db, cst_now, Booking, Payment, ParentStudent

payment_bp = Blueprint('payment', __name__, template_folder='../templates/payment')


@payment_bp.route('/pay/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def pay(booking_id):
    """Simulated payment page"""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash('预约不存在。', 'danger')
        return redirect(url_for('booking.my_bookings'))

    # Allow student who made the booking, or parent of that student
    if booking.student_id == current_user.id:
        pass  # Student owns this booking
    elif current_user.is_parent():
        binding = ParentStudent.query.filter_by(parent_id=current_user.id, student_id=booking.student_id).first()
        if not binding:
            flash('无权访问。', 'danger')
            return redirect(url_for('booking.my_bookings'))
    else:
        flash('无权访问。', 'danger')
        return redirect(url_for('booking.my_bookings'))

    payment = Payment.query.filter_by(booking_id=booking_id).first()
    if not payment:
        flash('支付记录不存在。', 'danger')
        return redirect(url_for('booking.my_bookings'))

    if payment.status == 'paid':
        flash('该预约已支付。', 'info')
        return redirect(url_for('booking.my_bookings'))

    if request.method == 'POST':
        # Simulate payment — mark as paid immediately
        payment.status = 'paid'
        payment.paid_at = cst_now()
        db.session.commit()
        current_app.logger.info(f'Payment success: booking={booking_id} amount={payment.amount}')
        flash('支付成功！等待教师确认预约。', 'success')
        return redirect(url_for('booking.my_bookings'))

    return render_template('pay.html', booking=booking, payment=payment)


@payment_bp.route('/my-payments')
@login_required
def my_payments():
    """Student views their payment history, or parent views children's payments"""
    if not current_user.is_student() and not current_user.is_parent():
        flash('只有学生或家长可以访问此页面。', 'danger')
        return redirect(url_for('course.index'))

    if current_user.is_parent():
        bindings = ParentStudent.query.filter_by(parent_id=current_user.id).all()
        student_ids = [b.student_id for b in bindings]
        payments = Payment.query.filter(Payment.student_id.in_(student_ids)).order_by(Payment.paid_at.desc()).all() if student_ids else []
    else:
        payments = Payment.query.filter_by(student_id=current_user.id).order_by(Payment.paid_at.desc()).all()

    return render_template('my_payments.html', payments=payments)
