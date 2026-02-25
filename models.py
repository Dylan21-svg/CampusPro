from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # admin, teacher, student, parent
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # For student role
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id'), nullable=True) # For student role
    
    # Pro Features
    is_pro = db.Column(db.Boolean, default=False)
    pro_expiry_on = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    courses_taught = db.relationship('Course', backref='teacher_ref', lazy=True)
    enrollments = db.relationship('Enrollment', backref='student_ref', lazy=True)
    attendances = db.relationship('Attendance', backref='student_ref', lazy=True)
    results = db.relationship('Result', backref='student_ref', lazy=True)
    payments = db.relationship('Payment', backref='student_ref', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user_ref', lazy=True)
    children = db.relationship('User', backref=db.backref('parent_ref', remote_side=[id]), lazy=True)

class SchoolClass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    # Relationships
    courses = db.relationship('Course', backref='class_ref', lazy=True)
    students = db.relationship('User', foreign_keys='User.class_id', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id'), nullable=True)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='course_ref', lazy=True)
    attendances = db.relationship('Attendance', backref='course_ref', lazy=True)
    results = db.relationship('Result', backref='course_ref', lazy=True)
    timetable = db.relationship('Timetable', backref='course_ref', lazy=True)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date_enrolled = db.Column(db.DateTime, default=datetime.utcnow)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    status = db.Column(db.String(20), nullable=False) # Present, Absent, Late

class TeacherAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    status = db.Column(db.String(20), nullable=False) # Present, Absent, Leave

    # Relationships
    teacher_ref = db.relationship('User', backref=db.backref('teacher_attendances', lazy=True))

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    marks = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(5))
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)

class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), default="Tuition") # Tuition, Lab, Library, etc.
    payments = db.relationship('Payment', backref='fee_ref', lazy=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fee_id = db.Column(db.Integer, db.ForeignKey('fee.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Paid") # Paid, Partial, Pending

class ProTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, default=100.0)
    payment_method = db.Column(db.String(50)) # stripe, paypal, mo-mo, orange, bank
    transaction_id = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default="Pending") # Pending, Completed, Failed
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='pro_transactions', lazy=True)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    day = db.Column(db.String(20), nullable=False) # Monday, Tuesday, etc.
    start_time = db.Column(db.String(10), nullable=False) # 08:00
    end_time = db.Column(db.String(10), nullable=False) # 10:00
    room = db.Column(db.String(50))

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    target_role = db.Column(db.String(20), default="all") # all, student, teacher
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(50), default="Event") # Event, Holiday, Exam
    is_read = db.Column(db.Boolean, default=False)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
