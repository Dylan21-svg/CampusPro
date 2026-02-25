from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from models import db, User, SchoolClass
from utils.decorators import role_required, pro_required
from werkzeug.security import generate_password_hash
import io
import csv

students_bp = Blueprint('students', __name__)

@students_bp.route("/admin/students")
@role_required(["admin"])
def list_students():
    search = request.args.get('search', '')
    query = User.query.filter_by(role="student")
    if search:
        query = query.filter(User.name.like(f"%{search}%") | User.email.like(f"%{search}%"))
    
    students = query.order_by(User.name.asc()).all()
    classes = SchoolClass.query.all()
    parents = User.query.filter_by(role="parent").all()
    return render_template("management/students.html", students=students, classes=classes, parents=parents, search=search)

@students_bp.route("/admin/students/add", methods=["POST"])
@role_required(["admin"])
def add_student():
    admin_user = User.query.get(session["user_id"])
    student_count = User.query.filter_by(role="student").count()
    if not admin_user.is_pro and student_count >= 10:
        flash("Free tier limit reached (10 students). Upgrade to Pro for unlimited enrollment!", "warning")
        return redirect(url_for('upgrade.upgrade_page'))

    name = request.form.get("name")
    email = request.form.get("email")
    password = generate_password_hash(request.form.get("password") or "student123")
    
    if User.query.filter_by(email=email).first():
        flash("Email already registered.", "danger")
        return redirect(url_for('students.list_students'))
        
    student = User(
        name=name, email=email, password=password, role="student",
        phone=request.form.get("phone"),
        address=request.form.get("address"),
        class_id=request.form.get("class_id"),
        parent_id=request.form.get("parent_id")
    )
    db.session.add(student)
    db.session.commit()
    flash(f"Student {name} registered successfully.", "success")
    return redirect(url_for('students.list_students'))

@students_bp.route("/admin/students/edit/<int:id>", methods=["POST"])
@role_required(["admin"])
def edit_student(id):
    student = User.query.get_or_404(id)
    student.name = request.form.get("name")
    student.email = request.form.get("email")
    student.class_id = request.form.get("class_id")
    student.parent_id = request.form.get("parent_id")
    db.session.commit()
    flash("Student record updated.", "success")
    return redirect(url_for('students.list_students'))

@students_bp.route("/admin/students/delete/<int:id>")
@role_required(["admin"])
def delete_student(id):
    student = User.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    flash("Student record deleted.", "info")
    return redirect(url_for('students.list_students'))

@students_bp.route("/admin/students/export")
@role_required(["admin"])
@pro_required
def export_students():
    students = User.query.filter_by(role="student").all()
    def generate():
        data = io.StringIO()
        writer = csv.writer(data)
        writer.writerow(['ID', 'Name', 'Email', 'Class', 'Parent'])
        for s in students:
            writer.writerow([s.id, s.name, s.email, s.class_ref.name if s.class_ref else 'N/A', s.parent_ref.name if s.parent_ref else 'N/A'])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
    return Response(generate(), mimetype='text/csv', headers={"Content-disposition": "attachment; filename=students_export.csv"})
