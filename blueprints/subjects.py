from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Course, User, SchoolClass
from utils.decorators import role_required

subjects_bp = Blueprint('subjects', __name__)

@subjects_bp.route("/admin/subjects")
@role_required(["admin"])
def list_subjects():
    subjects = Course.query.all()
    teachers = User.query.filter_by(role="teacher").all()
    classes = SchoolClass.query.all()
    return render_template("management/subjects.html", subjects=subjects, teachers=teachers, classes=classes)

@subjects_bp.route("/admin/subjects/add", methods=["POST"])
@role_required(["admin"])
def add_subject():
    title = request.form.get("title")
    description = request.form.get("description")
    teacher_id = request.form.get("teacher_id")
    class_id = request.form.get("class_id")
    
    subject = Course(title=title, description=description, teacher_id=teacher_id, class_id=class_id)
    db.session.add(subject)
    db.session.commit()
    flash(f"Subject {title} registered.", "success")
    return redirect(url_for('subjects.list_subjects'))

@subjects_bp.route("/admin/subjects/edit/<int:id>", methods=["POST"])
@role_required(["admin"])
def edit_subject(id):
    subject = Course.query.get_or_404(id)
    subject.title = request.form.get("title")
    subject.description = request.form.get("description")
    subject.teacher_id = request.form.get("teacher_id")
    subject.class_id = request.form.get("class_id")
    db.session.commit()
    flash("Subject details updated.", "success")
    return redirect(url_for('subjects.list_subjects'))

@subjects_bp.route("/admin/subjects/delete/<int:id>")
@role_required(["admin"])
def delete_subject(id):
    subject = Course.query.get_or_404(id)
    db.session.delete(subject)
    db.session.commit()
    flash("Subject removed.", "info")
    return redirect(url_for('subjects.list_subjects'))
