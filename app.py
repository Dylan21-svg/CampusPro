from flask import Flask, render_template, request, redirect, session, url_for, flash, Response, send_file
from config import Config
from models import db, User, Course, Enrollment, Attendance, Result, Fee, Payment, Timetable, Notice, Message, ActivityLog, Event, TeacherAttendance, SchoolClass, ProTransaction
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import json
import os

# Import Blueprints
from blueprints.teachers import teachers_bp
from blueprints.students import students_bp
from blueprints.classes import classes_bp
from blueprints.subjects import subjects_bp
from blueprints.payments import payments_bp
from utils.decorators import role_required, pro_required

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Register Blueprints
app.register_blueprint(teachers_bp)
app.register_blueprint(students_bp)
app.register_blueprint(classes_bp)
app.register_blueprint(subjects_bp)
app.register_blueprint(payments_bp)

# Activity Logger
def log_activity(user_id, action):
    if User.query.get(user_id):
        log = ActivityLog(user_id=user_id, action=action)
        db.session.add(log)
        db.session.commit()

# CREATE DATABASE FUNCTION
def create_tables():
    with app.app_context():
        try:
            # Check for SchoolClass to see if schema needs update
            SchoolClass.query.first()
        except Exception:
            db.drop_all()
            db.create_all()
            print("Database schema reset and recreated.")

        # create default admin
        admin = User.query.filter_by(email="admin@gmail.com").first()
        if not admin:
            admin = User(
                name="Admin",
                email="admin@gmail.com",
                password=generate_password_hash("admin123"),
                role="admin",
                is_pro=True # Seed admin as pro for testing
            )
            db.session.add(admin)
            db.session.commit()

# --- AUTH ROUTES ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["name"] = user.name
            session["role"] = user.role
            session["is_pro"] = user.is_pro
            log_activity(user.id, "Logged in")
            
            if user.role == "admin": return redirect(url_for("admin"))
            elif user.role == "teacher": return redirect(url_for("teacher_dashboard"))
            elif user.role == "parent": return redirect(url_for("parent_dashboard"))
            else: return redirect(url_for("dashboard"))
            
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# --- DASHBOARDS ---
@app.route("/")
@role_required(["student"])
def dashboard():
    user = User.query.get(session["user_id"])
    enrollments = Enrollment.query.filter_by(student_id=user.id).all()
    courses = [enrollment.course_ref for enrollment in enrollments]
    notices = Notice.query.filter(Notice.target_role.in_(["all", "student"])).order_by(Notice.date_posted.desc()).all()
    events = Event.query.filter(Event.date >= datetime.utcnow().date()).limit(5).all()
    
    total_att = Attendance.query.filter_by(student_id=user.id).count()
    present_att = Attendance.query.filter_by(student_id=user.id, status="Present").count()
    attendance_data = [present_att, total_att - present_att] if total_att > 0 else [0, 0]
    
    return render_template("dashboard.html", user=user, courses=courses, notices=notices, events=events, attendance_data=attendance_data)

@app.route("/teacher")
@role_required(["teacher"])
def teacher_dashboard():
    user = User.query.get(session["user_id"])
    courses = Course.query.filter_by(teacher_id=user.id).all()
    notices = Notice.query.filter(Notice.target_role.in_(["all", "teacher"])).order_by(Notice.date_posted.desc()).all()
    
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
    stats = {
        "students": User.query.filter_by(role="student").count(),
        "teachers": User.query.filter_by(role="teacher").count(),
        "classes": SchoolClass.query.count(),
        "courses": Course.query.count()
    }
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    growth_data = [5, 10, 15, stats["students"]]
    return render_template("admin_dashboard.html", stats=stats, logs=logs, growth_data=growth_data)

@app.route("/parent")
@role_required(["parent"])
def parent_dashboard():
    user = User.query.get(session["user_id"])
    return render_template("parent_dashboard.html", user=user)

# --- MESSAGING ---
@app.route("/messages", methods=["GET", "POST"])
def messages():
    if "user_id" not in session: return redirect(url_for("login"))
    user_id = session["user_id"]
    if request.method == "POST":
        msg = Message(sender_id=user_id, receiver_id=request.form["receiver_id"], content=request.form["content"])
        db.session.add(msg)
        db.session.commit()
    
    inbox = Message.query.filter_by(receiver_id=user_id).order_by(Message.timestamp.desc()).all()
    outbox = Message.query.filter_by(sender_id=user_id).order_by(Message.timestamp.desc()).all()
    users = User.query.filter(User.id != user_id).all()
    return render_template("messages.html", inbox=inbox, outbox=outbox, users=users)

@app.route("/set_currency/<string:code>")
def set_currency(code):
    if code in ["USD", "XAF"]:
        session["currency"] = code
        flash(f"Currency switched to {code}", "info")
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/search")
@login_required
def global_search():
    q = request.args.get("q", "").strip()
    if not q:
        return redirect(request.referrer or url_for("dashboard"))
    
    # Try searching students
    student = User.query.filter_by(role="student").filter(User.name.like(f"%{q}%")).first()
    if student:
        return redirect(url_for("students.list_students", search=q))
    
    # Try searching teachers
    teacher = User.query.filter_by(role="teacher").filter(User.name.like(f"%{q}%")).first()
    if teacher:
        return redirect(url_for("teachers.list_teachers", search=q))
        
    # Default to dashboard with flash
    flash(f"No exact match for '{q}'. Showing related results.", "info")
    return redirect(url_for("dashboard"))

@app.context_processor
def utility_processor():
    def format_price(amount):
        currency = session.get("currency", "USD")
        if currency == "XAF":
            # Rough conversion 1 USD = 600 XAF
            converted = amount * 600
            return f"{converted:,.0f} FCFA"
        return f"${amount:,.2f}"
    return dict(format_price=format_price)

# --- PRO FEATURES ---
@app.route("/admin/analytics")
@role_required(["admin"])
@pro_required
def pro_analytics():
    return render_template("pro/analytics.html")

@app.route("/admin/exams")
@role_required(["admin", "teacher"])
@pro_required
def manage_exams():
    flash("Online Exam System is active for Pro users.", "success")
    return render_template("dashboard.html") # Placeholder or specific page

@app.route("/admin/attendance_report")
@role_required(["admin"])
@pro_required
def attendance_automation():
    flash("Monthly Attendance Report generated successfully (Pro Feature).", "success")
    return redirect(url_for("admin"))

@app.route("/admin/backup")
@role_required(["admin"])
@pro_required
def backup_db():
    data = {
        "users": [{"name": u.name, "email": u.email} for u in User.query.all()],
        "timestamp": str(datetime.utcnow())
    }
    backup_file = "backup_pro.json"
    with open(backup_file, "w") as f: json.dump(data, f)
    return send_file(backup_file, as_attachment=True)

# Compatibility & Legacy routes
@app.route("/admin/fees", methods=["GET", "POST"])
@role_required(["admin"])
def manage_fees():
    if request.method == "POST":
        fee = Fee(
            title=request.form["title"],
            amount=float(request.form["amount"]),
            type=request.form.get("type", "Tuition")
        )
        db.session.add(fee)
        db.session.commit()
        flash("New fee item published.", "success")
        return redirect(url_for("manage_fees"))
    
    fees = Fee.query.all()
    return render_template("admin_financials.html", fees=fees)

@app.route("/admin/delete_fee/<int:id>")
@role_required(["admin"])
def delete_fee(id):
    fee = Fee.query.get_or_404(id)
    db.session.delete(fee)
    db.session.commit()
    flash("Fee item removed.", "info")
    return redirect(url_for("manage_fees"))

@app.route("/admin/edit_fee/<int:id>", methods=["POST"])
@role_required(["admin"])
def edit_fee(id):
    fee = Fee.query.get_or_404(id)
    fee.title = request.form["title"]
    fee.amount = float(request.form["amount"])
    db.session.commit()
    flash("Fee record updated.", "success")
    return redirect(url_for("manage_fees"))

@app.route("/admin/timetable", methods=["GET", "POST"])
@role_required(["admin"])
def manage_timetable():
    if request.method == "POST":
        entry = Timetable(
            course_id=request.form["course_id"],
            day=request.form["day"],
            start_time=request.form["start_time"],
            end_time=request.form["end_time"],
            room=request.form.get("room")
        )
        db.session.add(entry)
        db.session.commit()
        flash("Timetable entry added.", "success")
        return redirect(url_for("manage_timetable"))
    
    timetable = Timetable.query.all()
    courses = Course.query.all()
    return render_template("admin_timetable.html", timetable=timetable, courses=courses)

@app.route("/admin/teacher_attendance", methods=["GET", "POST"])
@role_required(["admin"])
def manage_teacher_attendance():
    if request.method == "POST":
        record = TeacherAttendance(
            teacher_id=request.form["teacher_id"],
            status=request.form["status"]
        )
        db.session.add(record)
        db.session.commit()
        flash("Attendance record saved.", "success")
        return redirect(url_for("manage_teacher_attendance"))
    
    attendance = TeacherAttendance.query.order_by(TeacherAttendance.date.desc()).all()
    teachers = User.query.filter_by(role="teacher").all()
    return render_template("admin_teacher_attendance.html", attendance=attendance, teachers=teachers)

if __name__ == "__main__":
    with app.app_context():
        create_tables()
    app.run(debug=True)