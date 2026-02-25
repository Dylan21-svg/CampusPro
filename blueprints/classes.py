from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, SchoolClass, User
from utils.decorators import role_required

classes_bp = Blueprint('classes', __name__)

@classes_bp.route("/admin/classes")
@role_required(["admin"])
def list_classes():
    classes = SchoolClass.query.all()
    # For the add form
    teachers = User.query.filter_by(role="teacher").all()
    return render_template("management/classes.html", classes=classes, teachers=teachers)

@classes_bp.route("/admin/classes/add", methods=["POST"])
@role_required(["admin"])
def add_class():
    name = request.form.get("name")
    description = request.form.get("description")
    
    new_class = SchoolClass(name=name, description=description)
    db.session.add(new_class)
    db.session.commit()
    flash(f"Class {name} created successfully.", "success")
    return redirect(url_for('classes.list_classes'))

@classes_bp.route("/admin/classes/edit/<int:id>", methods=["POST"])
@role_required(["admin"])
def edit_class(id):
    school_class = SchoolClass.query.get_or_404(id)
    school_class.name = request.form.get("name")
    school_class.description = request.form.get("description")
    db.session.commit()
    flash("Class updated.", "success")
    return redirect(url_for('classes.list_classes'))

@classes_bp.route("/admin/classes/delete/<int:id>")
@role_required(["admin"])
def delete_class(id):
    school_class = SchoolClass.query.get_or_404(id)
    # Check if students are in this class
    if User.query.filter_by(class_id=id).first():
        flash("Cannot delete class with active students. Move students first.", "danger")
        return redirect(url_for('classes.list_classes'))
        
    db.session.delete(school_class)
    db.session.commit()
    flash("Class removed.", "info")
    return redirect(url_for('classes.list_classes'))
