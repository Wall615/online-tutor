from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Review, Booking, TeacherProfile, User

review_bp = Blueprint('review', __name__, template_folder='../templates/review')


@review_bp.route('/create/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def create(booking_id):
    """Student creates a review for a completed booking"""
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.student_id != current_user.id:
        flash('无权评价此预约。', 'danger')
        return redirect(url_for('booking.my_bookings'))

    if booking.status != 'completed':
        flash('只能评价已完成的课程。', 'danger')
        return redirect(url_for('booking.my_bookings'))

    existing = Review.query.filter_by(booking_id=booking_id).first()
    if existing:
        flash('您已评价过此课程。', 'warning')
        return redirect(url_for('review.teacher_reviews', teacher_id=booking.teacher_id))

    if request.method == 'POST':
        rating = request.form.get('rating', 5, type=int)
        comment = request.form.get('comment', '').strip()

        if rating < 1 or rating > 5:
            flash('评分必须在 1-5 之间。', 'danger')
            return render_template('review_create.html', booking=booking)

        review = Review(
            booking_id=booking_id,
            student_id=current_user.id,
            teacher_id=booking.teacher_id,
            rating=rating,
            comment=comment
        )
        db.session.add(review)

        # Update teacher's average rating
        teacher_profile = TeacherProfile.query.filter_by(user_id=booking.teacher_id).first()
        if teacher_profile:
            all_ratings = Review.query.filter_by(teacher_id=booking.teacher_id).all()
            avg = sum(r.rating for r in all_ratings) / len(all_ratings)
            teacher_profile.rating_avg = round(avg, 1)
            db.session.add(teacher_profile)

        db.session.commit()
        flash('评价提交成功！', 'success')
        return redirect(url_for('review.teacher_reviews', teacher_id=booking.teacher_id))

    return render_template('review_create.html', booking=booking)


@review_bp.route('/teacher/<int:teacher_id>')
def teacher_reviews(teacher_id):
    """View all reviews for a teacher"""
    teacher = db.session.get(User, teacher_id)
    if not teacher:
        flash('教师不存在。', 'danger')
        return redirect(url_for('course.index'))

    reviews = Review.query.filter_by(teacher_id=teacher_id).order_by(Review.created_at.desc()).all()
    return render_template('teacher_reviews.html', teacher=teacher, reviews=reviews)


@review_bp.route('/my-reviews')
@login_required
def my_reviews():
    """Student views reviews they have written"""
    reviews = Review.query.filter_by(student_id=current_user.id).order_by(Review.created_at.desc()).all()
    return render_template('my_reviews.html', reviews=reviews)
