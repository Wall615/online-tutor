import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Course, User, TeacherProfile, Review, Booking, Favorite, TimeSlot

course_bp = Blueprint('course', __name__, template_folder='../templates/course')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def save_cover_image(file):
    """Save uploaded cover image, return filename or None on error."""
    if not file or file.filename == '':
        return ''
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return None
    filename = f"course_{uuid.uuid4().hex[:12]}.{ext}"
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'covers')
    os.makedirs(upload_dir, exist_ok=True)
    file.save(os.path.join(upload_dir, filename))
    return filename


@course_bp.route('/')
def index():
    """Course listing with search/filter"""
    page = request.args.get('page', 1, type=int)
    subject = request.args.get('subject', '').strip()
    keyword = request.args.get('keyword', '').strip()
    sort = request.args.get('sort', 'newest')  # newest / price_low / price_high / rating

    query = Course.query.filter_by(status='active', approved=True)

    if subject:
        query = query.filter_by(subject=subject)
    if keyword:
        query = query.filter(Course.title.contains(keyword) | Course.description.contains(keyword))

    # Get all subjects for filter dropdown
    all_subjects = [row[0] for row in db.session.query(Course.subject).filter(Course.status == 'active').distinct().all()]

    # Sorting
    if sort == 'price_low':
        query = query.order_by(Course.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Course.price.desc())
    elif sort == 'rating':
        query = query.outerjoin(TeacherProfile, Course.teacher_id == TeacherProfile.user_id).order_by(TeacherProfile.rating_avg.desc().nullslast())
    else:  # newest
        query = query.order_by(Course.created_at.desc())

    courses = query.paginate(page=page, per_page=12, error_out=False)

    # Get favorited course IDs for current user
    favorited_ids = set()
    if current_user.is_authenticated:
        favorited_ids = {f.course_id for f in Favorite.query.filter_by(user_id=current_user.id).all()}

    return render_template('index.html',
                           courses=courses,
                           all_subjects=all_subjects,
                           current_subject=subject,
                           current_keyword=keyword,
                           current_sort=sort,
                           favorited_ids=favorited_ids)


@course_bp.route('/<int:course_id>')
def detail(course_id):
    """Course detail page"""
    course = db.session.get(Course, course_id)
    if not course:
        flash('课程不存在。', 'danger')
        return redirect(url_for('course.index'))

    teacher = db.session.get(User, course.teacher_id)
    reviews = Review.query.filter_by(teacher_id=teacher.id).order_by(Review.created_at.desc()).limit(10).all()

    # Check if current user can review this course (has completed booking)
    can_review = False
    review_count = 0
    if current_user.is_authenticated and current_user.is_student():
        completed_booking = Booking.query.filter_by(
            student_id=current_user.id,
            course_id=course_id,
            status='completed'
        ).first()
        if completed_booking:
            can_review = True
            review_count = Review.query.filter_by(booking_id=completed_booking.id).count()

    return render_template('detail.html', course=course, teacher=teacher, reviews=reviews, can_review=can_review, review_count=review_count)


@course_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Teacher creates a new course"""
    if not current_user.is_teacher():
        flash('只有教师可以发布课程。', 'danger')
        return redirect(url_for('course.index'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', 0, type=float)
        duration = request.form.get('duration', 60, type=int)

        if not title or not subject:
            flash('课程标题和科目为必填项。', 'danger')
            return render_template('create.html')

        if price < 0 or price > 99999.99:
            flash('价格需在 0 ~ 99999.99 之间。', 'danger')
            return render_template('create.html')

        if len(title) > 200:
            flash('课程标题不能超过200个字符。', 'danger')
            return render_template('create.html')

        if len(description) > 2000:
            flash('课程描述不能超过2000个字符。', 'danger')
            return render_template('create.html')

        # Handle cover image upload
        cover_image = ''
        if 'cover_image' in request.files:
            filename = save_cover_image(request.files['cover_image'])
            if filename is None:
                flash('封面图片格式不支持，请上传 png/jpg/gif/webp 格式。', 'danger')
                return render_template('create.html')
            cover_image = filename

        course = Course(
            teacher_id=current_user.id,
            title=title,
            subject=subject,
            description=description,
            price=price,
            duration=duration,
            cover_image=cover_image
        )
        db.session.add(course)
        db.session.commit()
        flash('课程已提交，等待管理员审核后公开展示。', 'success')
        return redirect(url_for('course.my_courses'))

    return render_template('create.html')


@course_bp.route('/my-courses')
@login_required
def my_courses():
    """Teacher's own course list"""
    if not current_user.is_teacher():
        flash('只有教师可以访问此页面。', 'danger')
        return redirect(url_for('course.index'))

    courses = Course.query.filter_by(teacher_id=current_user.id).order_by(Course.created_at.desc()).all()
    return render_template('my_courses.html', courses=courses)


@course_bp.route('/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(course_id):
    """Edit a course"""
    course = db.session.get(Course, course_id)
    if not course or course.teacher_id != current_user.id:
        flash('无权编辑此课程。', 'danger')
        return redirect(url_for('course.index'))

    if request.method == 'POST':
        course.title = request.form.get('title', '').strip()
        course.subject = request.form.get('subject', '').strip()
        course.description = request.form.get('description', '').strip()
        course.price = request.form.get('price', 0, type=float)
        course.duration = request.form.get('duration', 60, type=int)
        course.status = request.form.get('status', 'active')

        # Handle cover image upload
        if 'cover_image' in request.files:
            filename = save_cover_image(request.files['cover_image'])
            if filename is None:
                flash('封面图片格式不支持，请上传 png/jpg/gif/webp 格式。', 'danger')
                return render_template('edit.html', course=course)
            if filename:
                course.cover_image = filename

        db.session.commit()
        flash('课程已更新。', 'success')
        return redirect(url_for('course.my_courses'))

    return render_template('edit.html', course=course)


@course_bp.route('/edit-teacher-profile', methods=['GET', 'POST'])
@login_required
def edit_teacher_profile():
    """Teacher edits their profile"""
    if not current_user.is_teacher():
        flash('只有教师可以访问此页面。', 'danger')
        return redirect(url_for('course.index'))

    profile = current_user.teacher_profile
    if not profile:
        profile = TeacherProfile(user_id=current_user.id)
        db.session.add(profile)

    if request.method == 'POST':
        profile.subjects = request.form.get('subjects', '').strip()
        profile.bio = request.form.get('bio', '').strip()
        profile.hourly_rate = request.form.get('hourly_rate', 0, type=float)
        profile.education = request.form.get('education', '').strip()

        # Handle time slots — clear and recreate
        TimeSlot.query.filter_by(teacher_id=current_user.id).delete()
        days = request.form.getlist('slot_day')
        starts = request.form.getlist('slot_start')
        ends = request.form.getlist('slot_end')
        for i in range(len(days)):
            if i < len(starts) and i < len(ends) and starts[i] and ends[i]:
                slot = TimeSlot(
                    teacher_id=current_user.id,
                    day_of_week=int(days[i]),
                    start_time=starts[i],
                    end_time=ends[i]
                )
                db.session.add(slot)

        db.session.commit()
        flash('教师资料已更新。', 'success')
        return redirect(url_for('auth.profile'))

    slots = TimeSlot.query.filter_by(teacher_id=current_user.id).order_by(TimeSlot.day_of_week, TimeSlot.start_time).all()
    return render_template('edit_teacher_profile.html', profile=profile, slots=slots)


@course_bp.route('/favorites/toggle/<int:course_id>', methods=['POST'])
@login_required
def toggle_favorite(course_id):
    """Toggle favorite status for a course (AJAX)"""
    from flask import jsonify
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({'error': '课程不存在'}), 404

    existing = Favorite.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'status': 'removed'})
    else:
        fav = Favorite(user_id=current_user.id, course_id=course_id)
        db.session.add(fav)
        db.session.commit()
        return jsonify({'status': 'added'})


@course_bp.route('/favorites')
@login_required
def favorites():
    """Show user's favorite courses"""
    fav_ids = [f.course_id for f in Favorite.query.filter_by(user_id=current_user.id).all()]
    courses = Course.query.filter(Course.id.in_(fav_ids)).all() if fav_ids else []
    return render_template('favorites.html', courses=courses)
