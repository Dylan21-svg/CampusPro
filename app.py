from flask import Flask, render_template, request, redirect, session, url_for, flash
from config import Config
from models import db, User, Course, Enrollment, Attendance, Result, Fee, Payment, Timetable, Notice, Message, ActivityLog
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import csv
import io
from flask import Response

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# RBAC Decorator
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You do not have permission to view this page.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Activity Logger
def log_activity(user_id, action):
    log = ActivityLog(user_id=user_id, action=action)
    db.session.add(log)
    db.session.commit()

# Email Notification Stub
def send_notification(user_id, subject, message):
    # This is a stub for future SMTP integration
    print(f"NOTIFICATION to User {user_id}: {subject} - {message}")
    log_activity(user_id, f"Notification sent: {subject}")

# CREATE DATABASE FUNCTION
def create_tables():
    with app.app_context():
        try:
            # Test query to check schema validity
            User.query.first()
            Fee.query.first() # New check for V2
        except Exception:
            # If schema is invalid, reset it
            db.drop_all()
            db.create_all()
            print("Database schema reset and recreated.")

        # create default admin
        admin = User.query.filter_by(email="admin@gmail.com").first()
        if admin:
            if not admin.password.startswith(('pbkdf2:sha256', 'scrypt', 'pbkdf2:sha512')):
                admin.password = generate_password_hash("admin123")
                db.session.commit()
        else:
            admin = User(
                name="Admin",
                email="admin@gmail.com",
                password=generate_password_hash("admin123"),
                role="admin"
            )
            db.session.add(admin)
            db.session.commit()

# --- AUTH ROUTES ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user:
            if user.password == password:
                user.password = generate_password_hash(password)
                db.session.commit()
                
            if check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["name"] = user.name
                session["role"] = user.role
                log_activity(user.id, "Logged in")
                
                if user.role == "admin":
                    return redirect(url_for("admin"))
                elif user.role == "teacher":
                    return redirect(url_for("teacher_dashboard"))
                elif user.role == "parent":
                    return redirect(url_for("parent_dashboard"))
                else:
                    return redirect(url_for("dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    if "user_id" in session:
        log_activity(session["user_id"], "Logged out")
    session.clear()
    return redirect(url_for("login"))

# --- DASHBOARDS ---
@app.route("/")
@role_required(["student"])
def dashboard():
    user = User.query.get(session["user_id"])
    enrollments = Enrollment.query.filter_by(student_id=user.id).all()
    courses = [enrollment.course_ref for enrollment in enrollments]
    all_courses = Course.query.all()
    notices = Notice.query.filter(Notice.target_role.in_(["all", "student"])).order_by(Notice.date_posted.desc()).all()
    
    # Simple attendance stats
    total_att = Attendance.query.filter_by(student_id=user.id).count()
    present_att = Attendance.query.filter_by(student_id=user.id, status="Present").count()
    attendance_data = [present_att, total_att - present_att] if total_att > 0 else [0, 0]
    
    return render_template("dashboard.html", user=user, courses=courses, all_courses=all_courses, notices=notices, attendance_data=attendance_data)

@app.route("/teacher")
@role_required(["teacher"])
def teacher_dashboard():
    user = User.query.get(session["user_id"])
    courses = Course.query.filter_by(teacher_id=user.id).all()
    notices = Notice.query.filter(Notice.target_role.in_(["all", "teacher"])).order_by(Notice.date_posted.desc()).all()
    
    # Class performance data
    perf_labels = [c.title for c in courses]
    perf_values = []
    for c in courses:
        marks = [r.marks for r in Result.query.filter_by(course_id=c.id).all()]
        avg = sum(marks) / len(marks) if marks else 0
        perf_values.append(avg)
        
    return render_template("teacher_dashboard.html", user=user, courses=courses, notices=notices, perf_labels=perf_labels, perf_values=perf_values)

@app.route("/admin")
@role_required(["admin"])
def admin():
    courses = Course.query.all()
    users = User.query.all()
    teachers = User.query.filter_by(role="teacher").all()
    parents = User.query.filter_by(role="parent").all()
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    # Enrollment growth over 4 weeks (mock logic based on date)
    growth_data = [5, 8, 12, Enrollment.query.count()] # Simplification
    
    return render_template("admin_dashboard.html", courses=courses, users=users, teachers=teachers, parents=parents, logs=logs, growth_data=growth_data)

@app.route("/parent")
@role_required(["parent"])
def parent_dashboard():
    user = User.query.get(session["user_id"])
    return render_template("parent_dashboard.html", user=user)

# --- FINANCIALS ---
@app.route("/admin/fees", methods=["GET", "POST"])
@role_required(["admin"])
def manage_fees():
    if request.method == "POST":
        fee = Fee(title=request.form["title"], amount=request.form["amount"], type=request.form["type"])
        db.session.add(fee)
        db.session.commit()
        log_activity(session["user_id"], f"Created fee: {fee.title}")
        return redirect(url_for("manage_fees"))
    fees = Fee.query.all()
    return render_template("admin_financials.html", fees=fees)

@app.route("/pay_fee/<int:fee_id>", methods=["POST"])
@role_required(["student"])
def pay_fee(fee_id):
    payment = Payment(student_id=session["user_id"], fee_id=fee_id, amount_paid=request.form["amount"])
    db.session.add(payment)
    db.session.commit()
    log_activity(session["user_id"], f"Paid fee ID: {fee_id}")
    flash("Payment recorded successfully!", "success")
    return redirect(url_for("dashboard"))

# --- SCHEDULING ---
@app.route("/admin/timetable", methods=["GET", "POST"])
@role_required(["admin"])
def manage_timetable():
    if request.method == "POST":
        entry = Timetable(
            course_id=request.form["course_id"],
            day=request.form["day"],
            start_time=request.form["start_time"],
            end_time=request.form["end_time"],
            room=request.form["room"]
        )
        db.session.add(entry)
        db.session.commit()
        log_activity(session["user_id"], "Updated timetable")
        return redirect(url_for("manage_timetable"))
    courses = Course.query.all()
    timetable = Timetable.query.all()
    return render_template("admin_timetable.html", courses=courses, timetable=timetable)

# --- COMMUNICATION ---
@app.route("/notices", methods=["GET", "POST"])
@role_required(["admin"])
def post_notice():
    if request.method == "POST":
        notice = Notice(title=request.form["title"], content=request.form["content"], target_role=request.form["target"])
        db.session.add(notice)
        db.session.commit()
        log_activity(session["user_id"], "Posted new notice")
    return redirect(url_for("admin"))

# --- CORE ACTIONS ---
@app.route("/add_course", methods=["POST"])
@role_required(["admin"])
def add_course():
    course = Course(title=request.form["title"], description=request.form["description"], teacher_id=request.form.get("teacher_id"))
    db.session.add(course)
    db.session.commit()
    log_activity(session["user_id"], f"Added course: {course.title}")
    return redirect(url_for("admin"))

@app.route("/add_user", methods=["POST"])
@role_required(["admin"])
def add_user():
    user = User(
        name=request.form["name"],
        email=request.form["email"],
        password=generate_password_hash(request.form["password"]),
        role=request.form["role"],
        phone=request.form.get("phone"),
        address=request.form.get("address"),
        parent_id=request.form.get("parent_id") if request.form.get("parent_id") else None
    )
    db.session.add(user)
    db.session.commit()
    log_activity(session["user_id"], f"Created user: {user.name} ({user.role})")
    return redirect(url_for("admin"))

# --- MESSAGING ---
@app.route("/messages", methods=["GET", "POST"])
def messages():
    if "user_id" not in session: return redirect(url_for("login"))
    user_id = session["user_id"]
    if request.method == "POST":
        msg = Message(sender_id=user_id, receiver_id=request.form["receiver_id"], content=request.form["content"])
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for("messages"))
    
    inbox = Message.query.filter_by(receiver_id=user_id).order_by(Message.timestamp.desc()).all()
    outbox = Message.query.filter_by(sender_id=user_id).order_by(Message.timestamp.desc()).all()
    users = User.query.filter(User.id != user_id).all()
    return render_template("messages.html", inbox=inbox, outbox=outbox, users=users)

# --- BULK DATA ---
@app.route("/admin/export_users")
@role_required(["admin"])
def export_users():
    users = User.query.all()
    def generate():
        data = io.StringIO()
        writer = csv.writer(data)
        writer.writerow(['Name', 'Email', 'Role', 'Phone', 'Address'])
        for u in users:
            writer.writerow([u.name, u.email, u.role, u.phone, u.address])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
    return Response(generate(), mimetype='text/csv', headers={"Content-disposition": "attachment; filename=users.csv"})

@app.route("/admin/import_users", methods=["POST"])
@role_required(["admin"])
def import_users():
    file = request.files['file']
    if not file: return redirect(url_for("admin"))
    
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.DictReader(stream)
    
    for row in csv_input:
        if not User.query.filter_by(email=row['Email']).first():
            user = User(
                name=row['Name'],
                email=row['Email'],
                password=generate_password_hash("student123"), # Default password
                role=row['Role'].lower(),
                phone=row.get('Phone'),
                address=row.get('Address')
            )
            db.session.add(user)
    db.session.commit()
    log_activity(session["user_id"], "Bulk imported users via CSV")
    return redirect(url_for("admin"))

@app.route("/enroll/<int:course_id>")
@role_required(["student"])
def enroll(course_id):
    if not Enrollment.query.filter_by(student_id=session["user_id"], course_id=course_id).first():
        db.session.add(Enrollment(student_id=session["user_id"], course_id=course_id))
        db.session.commit()
        log_activity(session["user_id"], f"Enrolled in course ID: {course_id}")
    return redirect(url_for("dashboard"))

@app.route("/mark_attendance/<int:course_id>", methods=["POST"])
@role_required(["teacher"])
def mark_attendance(course_id):
    att = Attendance(student_id=request.form["student_id"], course_id=course_id, status=request.form["status"])
    db.session.add(att)
    db.session.commit()
    return redirect(url_for("teacher_dashboard"))

if __name__ == "__main__":
    with app.app_context():
        create_tables()
    app.run(debug=True)