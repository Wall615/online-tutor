from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Message, Booking, User

chat_bp = Blueprint('chat', __name__, template_folder='../templates/chat')


@chat_bp.route('/')
@login_required
def chat_list():
    """List all chat-able bookings"""
    if current_user.is_student():
        bookings = Booking.query.filter_by(student_id=current_user.id)\
            .filter(Booking.status.in_(['confirmed', 'completed'])).order_by(Booking.created_at.desc()).all()
    elif current_user.is_teacher():
        bookings = Booking.query.filter_by(teacher_id=current_user.id)\
            .filter(Booking.status.in_(['confirmed', 'completed'])).order_by(Booking.created_at.desc()).all()
    else:
        bookings = []

    # Calculate unread count per booking
    unread_map = {}
    if bookings:
        for b in bookings:
            count = Message.query.filter_by(
                booking_id=b.id, receiver_id=current_user.id, is_read=False
            ).count()
            if count > 0:
                unread_map[b.id] = count

    return render_template('chat_list.html', bookings=bookings, unread_map=unread_map)


@chat_bp.route('/<int:booking_id>')
@login_required
def chat_room(booking_id):
    """Chat room for a specific booking"""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash('预约不存在。', 'danger')
        return redirect(url_for('chat.chat_list'))

    if current_user.id not in (booking.student_id, booking.teacher_id):
        flash('无权访问此聊天。', 'danger')
        return redirect(url_for('chat.chat_list'))

    # Determine the other party
    other_user_id = booking.teacher_id if current_user.id == booking.student_id else booking.student_id
    other_user = db.session.get(User, other_user_id)

    # Mark received messages as read
    Message.query.filter_by(booking_id=booking_id, receiver_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()

    messages = Message.query.filter_by(booking_id=booking_id).order_by(Message.sent_at.asc()).all()

    return render_template('chat_room.html', booking=booking, other_user=other_user, messages=messages)


@chat_bp.route('/<int:booking_id>/send', methods=['POST'])
@login_required
def send_message(booking_id):
    """Send a message in a booking chat"""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return jsonify({'error': '预约不存在'}), 404

    if current_user.id not in (booking.student_id, booking.teacher_id):
        return jsonify({'error': '无权操作'}), 403

    content = request.form.get('content', '').strip()
    if not content:
        return jsonify({'error': '消息不能为空'}), 400

    receiver_id = booking.teacher_id if current_user.id == booking.student_id else booking.student_id

    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        booking_id=booking_id,
        content=content
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({
        'id': message.id,
        'content': message.content,
        'sender_id': message.sender_id,
        'sent_at': message.sent_at.strftime('%H:%M')
    })


@chat_bp.route('/<int:booking_id>/messages')
@login_required
def get_messages(booking_id):
    """Get messages for a booking (polling endpoint)"""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return jsonify({'error': '预约不存在'}), 404

    if current_user.id not in (booking.student_id, booking.teacher_id):
        return jsonify({'error': '无权操作'}), 403

    # Get the last message id to only return newer ones
    last_id = request.args.get('after', 0, type=int)

    messages = Message.query.filter_by(booking_id=booking_id)\
        .filter(Message.id > last_id)\
        .order_by(Message.sent_at.asc()).all()

    return jsonify([{
        'id': m.id,
        'content': m.content,
        'sender_id': m.sender_id,
        'sender_name': db.session.get(User, m.sender_id).username,
        'sent_at': m.sent_at.strftime('%H:%M')
    } for m in messages])
