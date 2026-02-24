from flask import Flask, render_template, request, redirect, session, url_for, flash
from config import Config
from models import db, User, Course, Enrollment, Attendance, Result
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

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

# CREATE DATABASE FUNCTION
def create_tables():
    with app.app_context():
        try:
            # Test query to check schema validity
            User.query.first()
            Course.query.first()
        except Exception:
            # If schema is invalid (e.g. missing columns), reset it
            db.drop_all()
            db.create_all()
            print("Database schema reset and recreated.")

        # create default admin or migrate legacy password
        admin = User.query.filter_by(email="admin@gmail.com").first()
        if admin:
            # Check if password is in plain text (legacy)
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

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user:
            # Plain text check (migration)
            if user.password == password:
                user.password = generate_password_hash(password)
                db.session.commit()
                
            if check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["name"] = user.name
                session["role"] = user.role
                
                if user.role == "admin":
                    return redirect(url_for("admin"))
                elif user.role == "teacher":
                    return redirect(url_for("teacher_dashboard"))
                else:
                    return redirect(url_for("dashboard"))
            else:
                flash("Invalid credentials", "danger")
        else:
            flash("Invalid credentials", "danger")

    return render_template("login.html")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# STUDENT DASHBOARD
@app.route("/")
@role_required(["student"])
def dashboard():
    user = User.query.get(session["user_id"])
    enrollments = Enrollment.query.filter_by(student_id=user.id).all()
    courses = [enrollment.course_ref for enrollment in enrollments]
    all_courses = Course.query.all()
    return render_template("dashboard.html", user=user, courses=courses, all_courses=all_courses)

# TEACHER DASHBOARD
@app.route("/teacher")
@role_required(["teacher"])
def teacher_dashboard():
    user = User.query.get(session["user_id"])
    courses = Course.query.filter_by(teacher_id=user.id).all()
    return render_template("teacher_dashboard.html", user=user, courses=courses)

# ADMIN DASHBOARD
@app.route("/admin")
@role_required(["admin"])
def admin():
    courses = Course.query.all()
    users = User.query.all()
    teachers = User.query.filter_by(role="teacher").all()
    return render_template(
        "admin_dashboard.html",
        courses=courses,
        users=users,
        teachers=teachers
    )

# ADMIN: ADD COURSE
@app.route("/add_course", methods=["POST"])
@role_required(["admin"])
def add_course():
    title = request.form["title"]
    description = request.form["description"]
    teacher_id = request.form.get("teacher_id")

    course = Course(
        title=title,
        description=description,
        teacher_id=teacher_id if teacher_id else None
    )
    db.session.add(course)
    db.session.commit()
    return redirect(url_for("admin"))

# ADMIN: ADD USER (STUDENT/TEACHER)
@app.route("/add_user", methods=["POST"])
@role_required(["admin"])
def add_user():
    role = request.form["role"]
    password = generate_password_hash(request.form["password"])
    user = User(
        name=request.form["name"],
        email=request.form["email"],
        password=password,
        role=role
    )
    db.session.add(user)
    db.session.commit()
    return redirect(url_for("admin"))

# STUDENT: ENROLL IN COURSE
@app.route("/enroll/<int:course_id>")
@role_required(["student"])
def enroll(course_id):
    student_id = session["user_id"]
    existing = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
    if not existing:
        enrollment = Enrollment(student_id=student_id, course_id=course_id)
        db.session.add(enrollment)
        db.session.commit()
        flash("Enrolled successfully!", "success")
    return redirect(url_for("dashboard"))

# TEACHER: MARK ATTENDANCE
@app.route("/mark_attendance/<int:course_id>", methods=["POST"])
@role_required(["teacher"])
def mark_attendance(course_id):
    student_id = request.form["student_id"]
    status = request.form["status"]
    attendance = Attendance(student_id=student_id, course_id=course_id, status=status)
    db.session.add(attendance)
    db.session.commit()
    return redirect(url_for("teacher_dashboard"))

# RUN APP
if __name__ == "__main__":
    with app.app_context():
        create_tables()
    app.run(debug=True)