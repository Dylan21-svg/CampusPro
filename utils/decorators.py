from functools import wraps
from flask import session, redirect, url_for, flash
from models import User

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            
            user = User.query.get(session["user_id"])
            if not user or user.role not in roles:
                if not user: session.clear()
                flash("Unauthorized access. Please login with appropriate credentials.", "danger")
                return redirect(url_for("login"))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def pro_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        
        user = User.query.get(session["user_id"])
        if not user or not user.is_pro:
            flash("This feature is available for Pro users only. Upgrade now to unlock!", "warning")
            return redirect(url_for("upgrade.upgrade_page"))
        
        return f(*args, **kwargs)
    return decorated_function
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function
