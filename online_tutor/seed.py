"""Seed the database with demo data for presentation."""
from app import create_app
from models import db, User, TeacherProfile, Course, Booking, Payment, Review, Message, ParentStudent
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    # Clear existing data
    db.drop_all()
    db.create_all()

    # ===== Create users =====
    # Admin
    admin = User(username='admin', email='admin@tutor.com', role='admin')
    admin.set_password('admin123')

    # Teachers
    teacher1 = User(username='teacher_wang', email='wang@tutor.com', role='teacher')
    teacher1.set_password('123456')
    teacher2 = User(username='teacher_li', email='li@tutor.com', role='teacher')
    teacher2.set_password('123456')

    # Students
    student1 = User(username='student_xiao', email='xiao@tutor.com', role='student')
    student1.set_password('123456')
    student2 = User(username='student_ming', email='ming@tutor.com', role='student')
    student2.set_password('123456')

    # Parent
    parent1 = User(username='parent_zhang', email='zhang@tutor.com', role='parent')
    parent1.set_password('123456')

    db.session.add_all([admin, teacher1, teacher2, student1, student2, parent1])
    db.session.flush()

    # ===== Teacher Profiles =====
    profile1 = TeacherProfile(
        user_id=teacher1.id,
        subjects='数学,物理,编程',
        bio='10年教学经验，擅长高中数学和物理，曾辅导多名学生考入985高校。教学风格幽默风趣，注重培养学生的思维能力。',
        hourly_rate=150.00,
        education='清华大学 计算机科学 硕士',
        verified=True,
        rating_avg=4.8
    )
    profile2 = TeacherProfile(
        user_id=teacher2.id,
        subjects='英语,语文',
        bio='英语专业八级，5年英语家教经验。擅长英语口语和写作辅导，曾留学英国。',
        hourly_rate=120.00,
        education='北京外国语大学 英语 学士',
        verified=True,
        rating_avg=4.5
    )
    db.session.add_all([profile1, profile2])

    # ===== Courses =====
    course1 = Course(
        teacher_id=teacher1.id,
        title='高中数学一对一辅导',
        subject='数学',
        description='针对高中各年级的数学辅导，包括函数、几何、概率统计等。因材施教，查漏补缺。',
        price=150.00,
        duration=60,
        status='active'
    )
    course2 = Course(
        teacher_id=teacher1.id,
        title='Python编程入门到精通',
        subject='编程',
        description='从零开始学Python，适合零基础学员。涵盖基础语法、数据结构、项目实战。',
        price=200.00,
        duration=90,
        status='active'
    )
    course3 = Course(
        teacher_id=teacher2.id,
        title='英语口语强化训练',
        subject='英语',
        description='全英文授课环境，提升口语流利度和听力水平。模拟日常对话和面试场景。',
        price=120.00,
        duration=60,
        status='active'
    )
    course4 = Course(
        teacher_id=teacher2.id,
        title='高中英语写作专项',
        subject='英语',
        description='系统讲解英语写作技巧，包括议论文、说明文、应用文等文体。',
        price=100.00,
        duration=60,
        status='active'
    )
    db.session.add_all([course1, course2, course3, course4])
    db.session.flush()

    # ===== Bookings =====
    now = datetime.utcnow()

    # Booking 1: confirmed (student1 booked course1)
    booking1 = Booking(
        student_id=student1.id,
        teacher_id=teacher1.id,
        course_id=course1.id,
        scheduled_time=now + timedelta(days=2),
        status='confirmed'
    )

    # Booking 2: completed with review (student1 booked course3)
    booking2 = Booking(
        student_id=student1.id,
        teacher_id=teacher2.id,
        course_id=course3.id,
        scheduled_time=now - timedelta(days=3),
        status='completed'
    )

    # Booking 3: pending payment (student2 booked course2)
    booking3 = Booking(
        student_id=student2.id,
        teacher_id=teacher1.id,
        course_id=course2.id,
        scheduled_time=now + timedelta(days=5),
        status='pending'
    )

    db.session.add_all([booking1, booking2, booking3])
    db.session.flush()

    # ===== Payments =====
    payment1 = Payment(booking_id=booking1.id, student_id=student1.id, amount=150.00, status='paid', paid_at=now)
    payment2 = Payment(booking_id=booking2.id, student_id=student1.id, amount=120.00, status='paid', paid_at=now - timedelta(days=4))
    payment3 = Payment(booking_id=booking3.id, student_id=student2.id, amount=200.00, status='pending')
    db.session.add_all([payment1, payment2, payment3])
    db.session.flush()

    # ===== Reviews =====
    review1 = Review(
        booking_id=booking2.id,
        student_id=student1.id,
        teacher_id=teacher2.id,
        rating=5,
        comment='老师非常耐心，英语口语很地道，一节课下来感觉收获很大！'
    )
    db.session.add(review1)

    # ===== Messages (for booking1 chat) =====
    msg1 = Message(sender_id=student1.id, receiver_id=teacher1.id, booking_id=booking1.id,
                   content='王老师您好，我数学基础比较薄弱，希望能重点讲解函数部分。', sent_at=now - timedelta(hours=2))
    msg2 = Message(sender_id=teacher1.id, receiver_id=student1.id, booking_id=booking1.id,
                   content='没问题！我会根据你的情况调整教学内容。请提前准备好最近考试的试卷，我可以帮你分析薄弱点。',
                   sent_at=now - timedelta(hours=1))
    msg3 = Message(sender_id=student1.id, receiver_id=teacher1.id, booking_id=booking1.id,
                   content='好的，谢谢老师！', sent_at=now - timedelta(minutes=30))
    db.session.add_all([msg1, msg2, msg3])

    # ===== Parent-Student Binding =====
    binding1 = ParentStudent(parent_id=parent1.id, student_id=student2.id)
    db.session.add(binding1)

    db.session.commit()

    print("=" * 50)
    print("种子数据创建成功！")
    print("=" * 50)
    print("\n演示账号：")
    print(f"  管理员: admin / admin123")
    print(f"  教师1: teacher_wang / 123456 (已认证, 4.8★)")
    print(f"  教师2: teacher_li / 123456 (已认证, 4.5★)")
    print(f"  学生1: student_xiao / 123456")
    print(f"  学生2: student_ming / 123456 (已绑定家长)")
    print(f"  家长: parent_zhang / 123456")
    print("\n演示场景：")
    print("  1. student_xiao 已预约 teacher_wang 的数学课(已确认+已支付)")
    print("  2. student_xiao 已完成 teacher_li 的英语课(已评价5星)")
    print("  3. student_ming 预约了 teacher_wang 的Python课(待支付)")
    print("  4. parent_zhang 绑定了 student_ming")
    print("  5. teacher_wang 和 student_xiao 有聊天记录")
