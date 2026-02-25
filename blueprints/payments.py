from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from models import db, User, ProTransaction
from utils.decorators import role_required
from datetime import datetime, timedelta
import secrets

payments_bp = Blueprint('upgrade', __name__)

@payments_bp.route("/upgrade")
def upgrade_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    return render_template("upgrade.html", user=user)

@payments_bp.route("/process_payment", methods=["POST"])
def process_payment():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    method = request.form.get("payment_method")
    
    # In a real app, you'd integrate with Stripe/PayPal APIs here.
    # We'll simulate success for Stripe/PayPal/MoMo and handle Bank separately.
    
    transaction_id = f"TXN-{secrets.token_hex(8).upper()}"
    
    if method == "bank_transfer":
        transaction = ProTransaction(
            user_id=user_id,
            payment_method="bank_transfer",
            transaction_id=transaction_id,
            status="Pending"
        )
        db.session.add(transaction)
        db.session.commit()
        flash("Bank transfer initiated. Please upload your receipt for verification.", "info")
        return redirect(url_for("upgrade.upgrade_page"))
    
    # Simulated instant success for other methods
    transaction = ProTransaction(
        user_id=user_id,
        payment_method=method,
        transaction_id=transaction_id,
        status="Completed"
    )
    db.session.add(transaction)
    
    user = User.query.get(user_id)
    user.is_pro = True
    user.pro_expiry_on = datetime.utcnow() + timedelta(days=30)
    
    db.session.commit()
    
    flash(f"Payment successful via {method.replace('_', ' ').title()}! Welcome to Pro.", "success")
    return redirect(url_for("login"))

@payments_bp.route("/admin/verify_payment/<int:txn_id>")
@role_required(["admin"])
def verify_payment(txn_id):
    txn = ProTransaction.query.get(txn_id)
    if txn and txn.status == "Pending":
        txn.status = "Completed"
        user = User.query.get(txn.user_id)
        user.is_pro = True
        user.pro_expiry_on = datetime.utcnow() + timedelta(days=365)
        db.session.commit()
        flash(f"Payment for User {user.name} verified successfully.", "success")
    return redirect(url_for("admin"))
