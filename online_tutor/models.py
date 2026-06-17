from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

def cst_now():
    return datetime.now(CST)

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # student/teacher/parent/admin
    phone = db.Column(db.String(20), default='')
    avatar = db.Column(db.String(256), default='default.png')
    created_at = db.Column(db.DateTime, default=cst_now)

    # Relationships
    teacher_profile = db.relationship('TeacherProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    courses = db.relationship('Course', backref='teacher', lazy='dynamic', foreign_keys='Course.teacher_id')
    bookings_as_student = db.relationship('Booking', backref='student', lazy='dynamic', foreign_keys='Booking.student_id')
    bookings_as_teacher = db.relationship('Booking', backref='teacher_ref', lazy='dynamic', foreign_keys='Booking.teacher_id')
    sent_messages = db.relationship('Message', backref='sender', lazy='dynamic', foreign_keys='Message.sender_id')
    received_messages = db.relationship('Message', backref='receiver', lazy='dynamic', foreign_keys='Message.receiver_id')
    reviews_given = db.relationship('Review', backref='student', lazy='dynamic', foreign_keys='Review.student_id')
    reviews_received = db.relationship('Review', backref='teacher', lazy='dynamic', foreign_keys='Review.teacher_id')
    parent_bindings = db.relationship('ParentStudent', backref='parent', lazy='dynamic', foreign_keys='ParentStudent.parent_id')
    student_bindings = db.relationship('ParentStudent', backref='student', lazy='dynamic', foreign_keys='ParentStudent.student_id')
    payments = db.relationship('Payment', backref='student', lazy='dynamic', foreign_keys='Payment.student_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    def is_parent(self):
        return self.role == 'parent'

    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class TeacherProfile(db.Model):
    __tablename__ = 'teacher_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    subjects = db.Column(db.String(256), default='')  # comma-separated
    bio = db.Column(db.Text, default='')
    hourly_rate = db.Column(db.Float, default=0.0)
    education = db.Column(db.String(256), default='')
    verified = db.Column(db.Boolean, default=False)
    rating_avg = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f'<TeacherProfile user_id={self.user_id} verified={self.verified}>'


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, default='')
    price = db.Column(db.Float, nullable=False, default=0.0)
    duration = db.Column(db.Integer, nullable=False, default=60)  # minutes
    status = db.Column(db.String(20), default='active')  # active / inactive
    cover_image = db.Column(db.String(256), default='')
    created_at = db.Column(db.DateTime, default=cst_now)

    # Relationships
    bookings = db.relationship('Booking', backref='course', lazy='dynamic')

    def __repr__(self):
        return f'<Course {self.title} by teacher_id={self.teacher_id}>'


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending/confirmed/cancelled/completed
    created_at = db.Column(db.DateTime, default=cst_now)

    # Relationships
    messages = db.relationship('Message', backref='booking', lazy='dynamic')
    review = db.relationship('Review', backref='booking', uselist=False, cascade='all, delete-orphan')
    payment = db.relationship('Payment', backref='booking', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Booking {self.id} status={self.status}>'


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, index=True)
    sent_at = db.Column(db.DateTime, default=cst_now)

    def __repr__(self):
        return f'<Message {self.id} from={self.sender_id} to={self.receiver_id}>'


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=cst_now)

    def __repr__(self):
        return f'<Review booking={self.booking_id} rating={self.rating}>'


class ParentStudent(db.Model):
    __tablename__ = 'parent_students'

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bound_at = db.Column(db.DateTime, default=cst_now)

    __table_args__ = (
        db.UniqueConstraint('parent_id', 'student_id', name='uq_parent_student'),
    )

    def __repr__(self):
        return f'<ParentStudent parent={self.parent_id} student={self.student_id}>'


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending/paid/refunded
    paid_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Payment booking={self.booking_id} amount={self.amount} status={self.status}>'


class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=cst_now)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', name='uq_user_course_favorite'),
    )

    course = db.relationship('Course', backref='favorited_by')

    def __repr__(self):
        return f'<Favorite user={self.user_id} course={self.course_id}>'


class TimeSlot(db.Model):
    __tablename__ = 'time_slots'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Mon ... 6=Sun
    start_time = db.Column(db.String(5), nullable=False)  # "HH:MM"
    end_time = db.Column(db.String(5), nullable=False)    # "HH:MM"

    teacher = db.relationship('User', backref=db.backref('time_slots', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<TimeSlot teacher={self.teacher_id} day={self.day_of_week} {self.start_time}-{self.end_time}>'
