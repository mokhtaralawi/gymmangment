from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, PaymentMethod, Account, Subscription
from app.utils import log_audit

payments_bp = Blueprint("payments", __name__)

@payments_bp.route("/methods", methods=["GET", "POST"])
@login_required
def methods():
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        acc_id_str = request.form.get("account_id")
        notes = request.form.get("notes")

        acc_id = int(acc_id_str) if acc_id_str and acc_id_str.isdigit() else None

        method = PaymentMethod(
            name=name,
            code=code,
            account_id=acc_id,
            notes=notes,
            is_active=True
        )
        db.session.add(method)
        db.session.commit()
        log_audit("payments.create_method", target_type="payment_method", target_id=method.id, details=f"إضافة نوع دفع جديد: {name}")
        flash(f"تم إضافة طريقة الدفع {name} بنجاح.", "success")
        return redirect(url_for("payments.methods"))

    all_methods = PaymentMethod.query.order_by(PaymentMethod.id.asc()).all()
    cash_accounts = Account.query.filter(Account.node_type.in_(["صندوق", "بنك"])).all()

    # Calculate statistics for each method
    stats = {}
    for m in all_methods:
        subs = Subscription.query.filter_by(payment_method_id=m.id).all()
        total_collected = sum(s.paid_amount for s in subs if s.paid_amount)
        stats[m.id] = {
            "subs_count": len(subs),
            "total_collected": total_collected
        }

    return render_template("payment_methods/index.html", methods=all_methods, accounts=cash_accounts, stats=stats)

@payments_bp.route("/methods/<int:method_id>/toggle", methods=["POST"])
@login_required
def toggle_method(method_id):
    method = PaymentMethod.query.get_or_404(method_id)
    method.is_active = not method.is_active
    db.session.commit()
    log_audit("payments.toggle_method", target_type="payment_method", target_id=method.id, details=f"تغيير حالة طريقة الدفع {method.name} إلى {'مفعلة' if method.is_active else 'معطلة'}")
    flash(f"تم تحديث حالة طريقة الدفع {method.name}.", "success")
    return redirect(url_for("payments.methods"))

@payments_bp.route("/methods/<int:method_id>/edit", methods=["POST"])
@login_required
def edit_method(method_id):
    method = PaymentMethod.query.get_or_404(method_id)
    method.name = request.form.get("name", method.name)
    method.code = request.form.get("code", method.code)
    acc_id_str = request.form.get("account_id")
    method.account_id = int(acc_id_str) if acc_id_str and acc_id_str.isdigit() else None
    method.notes = request.form.get("notes", method.notes)

    db.session.commit()
    log_audit("payments.edit_method", target_type="payment_method", target_id=method.id, details=f"تعديل طريقة الدفع {method.name}")
    flash(f"تم حفظ تعديلات طريقة الدفع {method.name}.", "success")
    return redirect(url_for("payments.methods"))
