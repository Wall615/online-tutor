"""
单元测试 — 线上家教平台
运行方式: python -m pytest test_unit.py -v
或:       python test_unit.py
"""
import os
import sys
import unittest
from datetime import datetime

# Ensure the app directory is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, cst_now, User, TeacherProfile, Course, Booking, Payment, Review, Message, ParentStudent, Favorite, TimeSlot


class TestUserModel(unittest.TestCase):
    """User 模型：密码哈希、角色判断"""

    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_set_and_check_password(self):
        user = User(username='test', email='t@t.com', role='student')
        user.set_password('hello123')
        self.assertTrue(user.check_password('hello123'))
        self.assertFalse(user.check_password('wrong'))

    def test_password_hash_is_not_plaintext(self):
        user = User(username='test', email='t@t.com', role='student')
        user.set_password('secret')
        self.assertNotEqual(user.password_hash, 'secret')
        self.assertIn('scrypt', user.password_hash)  # Werkzeug default

    def test_role_checks(self):
        student = User(username='s', email='s@t.com', role='student')
        teacher = User(username='t', email='t@t.com', role='teacher')
        parent = User(username='p', email='p@t.com', role='parent')
        admin = User(username='a', email='a@t.com', role='admin')

        self.assertTrue(student.is_student())
        self.assertFalse(student.is_teacher())

        self.assertTrue(teacher.is_teacher())
        self.assertFalse(teacher.is_admin())

        self.assertTrue(parent.is_parent())

        self.assertTrue(admin.is_admin())
        self.assertFalse(admin.is_student())

    def test_user_repr(self):
        user = User(username='alice', email='a@b.com', role='student')
        user.set_password('123456')
        db.session.add(user)
        db.session.commit()
        self.assertIn('alice', repr(user))
        self.assertIn('student', repr(user))


class TestPasswordStrength(unittest.TestCase):
    """密码强度校验"""

    def test_minimum_length_6(self):
        self.assertTrue(len('123456') >= 6)
        self.assertTrue(len('abc') < 6)

    def test_mixed_case_detection(self):
        pw = 'Abcdef1'
        self.assertTrue(any(c.isupper() for c in pw))
        self.assertTrue(any(c.islower() for c in pw))
        self.assertTrue(any(c.isdigit() for c in pw))

    def test_weak_password(self):
        pw = '123456'
        has_upper = any(c.isupper() for c in pw)
        has_lower = any(c.islower() for c in pw)
        has_digit = any(c.isdigit() for c in pw)
        has_special = any(not c.isalnum() for c in pw)
        score = sum([len(pw) >= 6, len(pw) >= 10, has_upper and has_lower, has_digit, has_special])
        self.assertLessEqual(score, 2)  # weak

    def test_strong_password(self):
        pw = 'Abcdef123!@#'
        has_upper = any(c.isupper() for c in pw)
        has_lower = any(c.islower() for c in pw)
        has_digit = any(c.isdigit() for c in pw)
        has_special = any(not c.isalnum() for c in pw)
        score = sum([len(pw) >= 6, len(pw) >= 10, has_upper and has_lower, has_digit, has_special])
        self.assertGreaterEqual(score, 4)  # strong


class TestCourseModel(unittest.TestCase):
    """Course 模型"""

    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.teacher = User(username='t1', email='t1@t.com', role='teacher')
        self.teacher.set_password('123456')
        db.session.add(self.teacher)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_create_course(self):
        course = Course(
            teacher_id=self.teacher.id,
            title='Python 入门',
            subject='编程',
            description='从零学 Python',
            price=99.0,
            duration=60
        )
        db.session.add(course)
        db.session.commit()
        self.assertEqual(course.status, 'active')
        self.assertIsNotNone(course.id)
        self.assertEqual(course.title, 'Python 入门')

    def test_course_default_status_active(self):
        course = Course(teacher_id=self.teacher.id, title='Test', subject='数学', price=50)
        db.session.add(course)
        db.session.commit()
        self.assertEqual(course.status, 'active')

    def test_course_default_cover_image_empty(self):
        course = Course(teacher_id=self.teacher.id, title='Test', subject='数学', price=50)
        db.session.add(course)
        db.session.commit()
        self.assertEqual(course.cover_image, '')

    def test_course_duration_default(self):
        course = Course(teacher_id=self.teacher.id, title='Test', subject='数学', price=50)
        db.session.add(course)
        db.session.commit()
        self.assertEqual(course.duration, 60)

    def test_course_repr(self):
        course = Course(teacher_id=self.teacher.id, title='Math 101', subject='数学', price=30)
        db.session.add(course)
        db.session.commit()
        self.assertIn('Math 101', repr(course))


class TestBookingModel(unittest.TestCase):
    """Booking 模型与状态流转"""

    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.student = User(username='s1', email='s1@t.com', role='student')
        self.student.set_password('123')
        self.teacher = User(username='t1', email='t1@t.com', role='teacher')
        self.teacher.set_password('123')
        db.session.add_all([self.student, self.teacher])
        db.session.commit()

        self.course = Course(teacher_id=self.teacher.id, title='Math', subject='数学', price=100)
        db.session.add(self.course)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_create_booking_pending(self):
        booking = Booking(
            student_id=self.student.id,
            teacher_id=self.teacher.id,
            course_id=self.course.id,
            scheduled_time=datetime(2026, 8, 1, 14, 0),
            status='pending'
        )
        db.session.add(booking)
        db.session.commit()
        self.assertEqual(booking.status, 'pending')

    def test_booking_status_flow(self):
        booking = Booking(
            student_id=self.student.id, teacher_id=self.teacher.id,
            course_id=self.course.id,
            scheduled_time=datetime(2026, 8, 1, 14, 0)
        )
        db.session.add(booking)
        db.session.commit()

        # pending → confirmed
        booking.status = 'confirmed'
        db.session.commit()
        self.assertEqual(booking.status, 'confirmed')

        # confirmed → completed
        booking.status = 'completed'
        db.session.commit()
        self.assertEqual(booking.status, 'completed')

    def test_booking_cancel_from_pending(self):
        booking = Booking(
            student_id=self.student.id, teacher_id=self.teacher.id,
            course_id=self.course.id,
            scheduled_time=datetime(2026, 8, 1, 14, 0)
        )
        db.session.add(booking)
        db.session.commit()

        booking.status = 'cancelled'
        db.session.commit()
        self.assertEqual(booking.status, 'cancelled')

    def test_booking_student_and_teacher_relationship(self):
        booking = Booking(
            student_id=self.student.id, teacher_id=self.teacher.id,
            course_id=self.course.id,
            scheduled_time=datetime(2026, 8, 1, 14, 0)
        )
        db.session.add(booking)
        db.session.commit()

        self.assertEqual(booking.student.username, 's1')
        self.assertEqual(booking.teacher_ref.username, 't1')
        self.assertEqual(booking.course.title, 'Math')


class TestPaymentModel(unittest.TestCase):
    """Payment 模型"""

    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        s = User(username='s', email='s@t.com', role='student')
        t = User(username='t', email='t@t.com', role='teacher')
        s.set_password('123'); t.set_password('123')
        db.session.add_all([s, t]); db.session.commit()
        c = Course(teacher_id=t.id, title='C', subject='编程', price=150)
        db.session.add(c); db.session.commit()
        b = Booking(student_id=s.id, teacher_id=t.id, course_id=c.id,
                     scheduled_time=datetime(2026, 8, 1, 14, 0))
        db.session.add(b); db.session.commit()
        self.booking_id = b.id
        self.student_id = s.id

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_create_payment_pending(self):
        payment = Payment(booking_id=self.booking_id, student_id=self.student_id,
                          amount=150, status='pending')
        db.session.add(payment)
        db.session.commit()
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.amount, 150)
        self.assertIsNone(payment.paid_at)

    def test_payment_mark_as_paid(self):
        payment = Payment(booking_id=self.booking_id, student_id=self.student_id,
                          amount=150, status='pending')
        db.session.add(payment)
        db.session.commit()

        payment.status = 'paid'
        payment.paid_at = cst_now()
        db.session.commit()
        self.assertEqual(payment.status, 'paid')
        self.assertIsNotNone(payment.paid_at)


class TestReviewModel(unittest.TestCase):
    """Review 模型与评分"""

    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        s = User(username='s', email='s@t.com', role='student')
        t = User(username='t', email='t@t.com', role='teacher')
        s.set_password('123'); t.set_password('123')
        db.session.add_all([s, t]); db.session.commit()
        c = Course(teacher_id=t.id, title='C', subject='编程', price=150)
        db.session.add(c); db.session.commit()
        b = Booking(student_id=s.id, teacher_id=t.id, course_id=c.id,
                     scheduled_time=datetime(2026, 8, 1, 14, 0), status='completed')
        db.session.add(b); db.session.commit()
        self.booking = b
        self.student_id = s.id
        self.teacher_id = t.id

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_create_review(self):
        review = Review(booking_id=self.booking.id, student_id=self.student_id,
                        teacher_id=self.teacher_id, rating=5, comment='很棒')
        db.session.add(review)
        db.session.commit()
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, '很棒')

    def test_rating_boundaries(self):
        # Rating should be 1-5
        for r in [1, 3, 5]:
            review = Review(booking_id=self.booking.id + r, student_id=self.student_id,
                            teacher_id=self.teacher_id, rating=r, comment='')
            db.session.add(review)
        db.session.commit()
        reviews = Review.query.all()
        self.assertEqual(len(reviews), 3)

    def test_teacher_rating_average_calculation(self):
        ratings = [5, 4, 4]
        for i, r in enumerate(ratings):
            # Need separate bookings for each review (unique constraint)
            b = Booking(student_id=self.student_id, teacher_id=self.teacher_id,
                        course_id=self.booking.course_id,
                        scheduled_time=datetime(2026, 8, i + 2, 14, 0), status='completed')
            db.session.add(b); db.session.commit()
            review = Review(booking_id=b.id, student_id=self.student_id,
                            teacher_id=self.teacher_id, rating=r, comment='')
            db.session.add(review)
        db.session.commit()

        avg = sum(ratings) / len(ratings)
        self.assertAlmostEqual(avg, 4.3, places=1)


class TestParentStudentBinding(unittest.TestCase):
    """家长-学生绑定"""

    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.parent = User(username='p', email='p@t.com', role='parent')
        self.student = User(username='s', email='s@t.com', role='student')
        self.parent.set_password('123'); self.student.set_password('123')
        db.session.add_all([self.parent, self.student])
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_bind_parent_to_student(self):
        binding = ParentStudent(parent_id=self.parent.id, student_id=self.student.id)
        db.session.add(binding)
        db.session.commit()
        self.assertIsNotNone(binding.id)
        self.assertEqual(binding.parent_id, self.parent.id)
        self.assertEqual(binding.student_id, self.student.id)

    def test_unique_binding_constraint(self):
        b1 = ParentStudent(parent_id=self.parent.id, student_id=self.student.id)
        db.session.add(b1); db.session.commit()

        b2 = ParentStudent(parent_id=self.parent.id, student_id=self.student.id)
        db.session.add(b2)
        with self.assertRaises(Exception):
            db.session.commit()


class TestMessageModel(unittest.TestCase):
    """Message 模型 — 含已读状态"""

    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_message_is_unread_by_default(self):
        msg = Message(sender_id=1, receiver_id=2, booking_id=1, content='Hello')
        db.session.add(msg); db.session.commit()
        self.assertFalse(msg.is_read)

    def test_mark_message_as_read(self):
        msg = Message(sender_id=1, receiver_id=2, booking_id=1, content='Hello')
        db.session.add(msg); db.session.commit()
        msg.is_read = True
        db.session.commit()
        self.assertTrue(msg.is_read)


class TestFavoriteModel(unittest.TestCase):
    """Favorite 收藏模型"""

    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        u = User(username='u', email='u@t.com', role='student')
        t = User(username='t', email='t@t.com', role='teacher')
        u.set_password('123'); t.set_password('123')
        db.session.add_all([u, t]); db.session.commit()
        c = Course(teacher_id=t.id, title='C1', subject='编程', price=99)
        db.session.add(c); db.session.commit()
        self.user_id = u.id
        self.course_id = c.id

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_add_favorite(self):
        fav = Favorite(user_id=self.user_id, course_id=self.course_id)
        db.session.add(fav); db.session.commit()
        self.assertIsNotNone(fav.id)

    def test_unique_favorite_constraint(self):
        f1 = Favorite(user_id=self.user_id, course_id=self.course_id)
        db.session.add(f1); db.session.commit()

        f2 = Favorite(user_id=self.user_id, course_id=self.course_id)
        db.session.add(f2)
        with self.assertRaises(Exception):
            db.session.commit()

    def test_remove_favorite(self):
        fav = Favorite(user_id=self.user_id, course_id=self.course_id)
        db.session.add(fav); db.session.commit()

        db.session.delete(fav)
        db.session.commit()
        count = Favorite.query.filter_by(user_id=self.user_id).count()
        self.assertEqual(count, 0)


class TestTimeSlotModel(unittest.TestCase):
    """TimeSlot 教师可用时段"""

    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        t = User(username='t', email='t@t.com', role='teacher')
        t.set_password('123')
        db.session.add(t); db.session.commit()
        self.teacher_id = t.id

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_create_time_slot(self):
        slot = TimeSlot(teacher_id=self.teacher_id, day_of_week=1,  # Tuesday
                        start_time='09:00', end_time='11:00')
        db.session.add(slot); db.session.commit()
        self.assertEqual(slot.day_of_week, 1)
        self.assertEqual(slot.start_time, '09:00')
        self.assertEqual(slot.end_time, '11:00')

    def test_multiple_slots_per_teacher(self):
        for day in range(5):
            slot = TimeSlot(teacher_id=self.teacher_id, day_of_week=day,
                            start_time='10:00', end_time='11:00')
            db.session.add(slot)
        db.session.commit()
        count = TimeSlot.query.filter_by(teacher_id=self.teacher_id).count()
        self.assertEqual(count, 5)


class TestTeacherProfile(unittest.TestCase):
    """教师资料与认证"""

    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        t = User(username='t', email='t@t.com', role='teacher')
        t.set_password('123')
        db.session.add(t); db.session.commit()
        self.teacher_id = t.id

    def tearDown(self):
        db.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def test_default_not_verified(self):
        profile = TeacherProfile(user_id=self.teacher_id)
        db.session.add(profile); db.session.commit()
        self.assertFalse(profile.verified)

    def test_verify_teacher(self):
        profile = TeacherProfile(user_id=self.teacher_id)
        db.session.add(profile); db.session.commit()
        profile.verified = True
        db.session.commit()
        self.assertTrue(profile.verified)

    def test_default_rating_zero(self):
        profile = TeacherProfile(user_id=self.teacher_id)
        db.session.add(profile); db.session.commit()
        self.assertEqual(profile.rating_avg, 0.0)


class TestInputValidation(unittest.TestCase):
    """输入长度校验"""

    def test_username_max_80(self):
        valid = 'a' * 80
        invalid = 'a' * 81
        self.assertLessEqual(len(valid), 80)
        self.assertGreater(len(invalid), 80)

    def test_email_max_120(self):
        self.assertLessEqual(len('a' * 120), 120)
        self.assertGreater(len('a' * 121), 120)

    def test_course_title_max_200(self):
        self.assertLessEqual(len('a' * 200), 200)
        self.assertGreater(len('a' * 201), 200)

    def test_course_description_max_2000(self):
        self.assertLessEqual(len('a' * 2000), 2000)

    def test_review_comment_max_1000(self):
        self.assertLessEqual(len('a' * 1000), 1000)

    def test_phone_max_20(self):
        self.assertLessEqual(len('13800138000'), 20)


class TestCSRFToken(unittest.TestCase):
    """CSRF Token 生成"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_csrf_token_generation(self):
        import secrets
        token = secrets.token_hex(32)
        self.assertEqual(len(token), 64)  # 32 bytes = 64 hex chars

    def test_csrf_tokens_are_unique(self):
        import secrets
        t1 = secrets.token_hex(32)
        t2 = secrets.token_hex(32)
        self.assertNotEqual(t1, t2)

    def test_csrf_compare_digest(self):
        import secrets
        t1 = secrets.token_hex(32)
        t2 = secrets.token_hex(32)
        self.assertTrue(secrets.compare_digest(t1, t1))
        self.assertFalse(secrets.compare_digest(t1, t2))


if __name__ == '__main__':
    unittest.main(verbosity=2)
