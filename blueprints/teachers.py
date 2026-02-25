from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from models import db, User
from utils.decorators import role_required, pro_required
from werkzeug.security import generate_password_hash
import io
import csv

teachers_bp = Blueprint('teachers', __name__)

@teachers_bp.route("/admin/teachers")
@role_required(["admin"])
def list_teachers():
    search = request.args.get('search', '')
    query = User.query.filter_by(role="teacher")
    if search:
        query = query.filter(User.name.like(f"%{search}%") | User.email.like(f"%{search}%"))
    
    teachers = query.order_by(User.name.asc()).all()
    return render_template("management/teachers.html", teachers=teachers, search=search)

@teachers_bp.route("/admin/teachers/add", methods=["POST"])
@role_required(["admin"])
def add_teacher():
    # Check for free tier limit if not pro
    admin_user = User.query.get(session["user_id"])
    teacher_count = User.query.filter_by(role="teacher").count()
    if not admin_user.is_pro and teacher_count >= 5:
        flash("Free tier limit reached (5 teachers). Upgrade to Pro for unlimited faculty members!", "warning")
        return redirect(url_for('upgrade.upgrade_page'))

    name = request.form.get("name")
    email = request.form.get("email")
    password = generate_password_hash(request.form.get("password") or "teacher123")
    
    if User.query.filter_by(email=email).first():
        flash("Email already registered.", "danger")
        return redirect(url_for('teachers.list_teachers'))
        
    teacher = User(name=name, email=email, password=password, role="teacher", 
                  phone=request.form.get("phone"), address=request.form.get("address"))
    db.session.add(teacher)
    db.session.commit()
    flash(f"Teacher {name} added successfully.", "success")
    return redirect(url_for('teachers.list_teachers'))

@teachers_bp.route("/admin/teachers/edit/<int:id>", methods=["POST"])
@role_required(["admin"])
def edit_teacher(id):
    teacher = User.query.get_or_404(id)
    teacher.name = request.form.get("name")
    teacher.email = request.form.get("email")
    teacher.phone = request.form.get("phone")
    teacher.address = request.form.get("address")
    db.session.commit()
    flash("Teacher updated successfully.", "success")
    return redirect(url_for('teachers.list_teachers'))

@teachers_bp.route("/admin/teachers/delete/<int:id>")
@role_required(["admin"])
def delete_teacher(id):
    teacher = User.query.get_or_404(id)
    db.session.delete(teacher)
    db.session.commit()
    flash("Teacher records removed.", "info")
    return redirect(url_for('teachers.list_teachers'))

@teachers_bp.route("/admin/teachers/export")
@role_required(["admin"])
@pro_required
def export_teachers():
    teachers = User.query.filter_by(role="teacher").all()
    def generate():
        data = io.StringIO()
        writer = csv.writer(data)
        writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Address'])
        for t in teachers:
            writer.writerow([t.id, t.name, t.email, t.phone, t.address])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
    return Response(generate(), mimetype='text/csv', headers={"Content-disposition": "attachment; filename=teachers_export.csv"})
