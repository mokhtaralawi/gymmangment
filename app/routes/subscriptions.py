import uuid
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Subscription, Plan, Member
from app.utils import log_audit

subscriptions_bp = Blueprint("subscriptions", __name__)

@subscriptions_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        member_id = request.form.get("member_id")
        plan_id = request.form.get("plan_id")
        start_date_str = request.form.get("start_date")
        notes = request.form.get("notes")

        member = Member.query.get_or_404(int(member_id))
        plan = Plan.query.get_or_404(int(plan_id))

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else date.today()
        end_date = start_date + timedelta(days=plan.duration_days)
        code = f"SUB-{uuid.uuid4().hex[:8].upper()}"

        sub = Subscription(
            subscription_code=code,
            member_id=member.id,
            plan_id=plan.id,
            start_date=start_date,
            end_date=end_date,
            price_paid=plan.price,
            notes=notes,
            status="ساري"
        )
        db.session.add(sub)
        db.session.commit()
        log_audit("subscriptions.create", target_type="subscription", target_id=sub.id, details=f"اشتراك جديد {code} للمشترك {member.full_name}")
        flash(f"تم إنشاء الاشتراك بنجاح ({plan.name} - {member.full_name}).", "success")
        return redirect(url_for("subscriptions.index"))

    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "")
    query = Subscription.query.join(Member)
    if q:
        query = query.filter((Member.full_name.contains(q)) | (Subscription.subscription_code.contains(q)))
    if status_filter:
        query = query.filter(Subscription.status == status_filter)

    subs = query.order_by(Subscription.id.desc()).all()
    members = Member.query.filter_by(status="نشط").all()
    plans = Plan.query.filter_by(is_active=True).all()
    return render_template("subscriptions/index.html", subscriptions=subs, members=members, plans=plans, q=q, status_filter=status_filter)

@subscriptions_bp.route("/<int:sub_id>/cancel", methods=["POST"])
@login_required
def cancel(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    reason = request.form.get("reason", "تم الإلغاء بواسطة الإدارة")
    sub.status = "ملغي"
    sub.cancel_reason = reason
    db.session.commit()
    log_audit("subscriptions.cancel", target_type="subscription", target_id=sub.id, details=f"إلغاء اشتراك {sub.subscription_code} لسبب: {reason}")
    flash(f"تم إلغاء الاشتراك {sub.subscription_code}.", "warning")
    return redirect(request.referrer or url_for("subscriptions.index"))

@subscriptions_bp.route("/plans", methods=["GET", "POST"])
@login_required
def plans():
    if request.method == "POST":
        name = request.form.get("name")
        duration_days = int(request.form.get("duration_days", 30))
        price = float(request.form.get("price", 0.0))
        description = request.form.get("description")
        code = f"PLN-{uuid.uuid4().hex[:10].upper()}"

        plan = Plan(plan_code=code, name=name, duration_days=duration_days, price=price, description=description, is_active=True)
        db.session.add(plan)
        db.session.commit()
        log_audit("plans.create", target_type="plan", target_id=plan.id, details=f"إنشاء باقة: {name}")
        flash(f"تم إضافة باقة {name} بنجاح.", "success")
        return redirect(url_for("subscriptions.plans"))

    q = request.args.get("q", "").strip()
    query = Plan.query
    if q:
        query = query.filter(Plan.name.contains(q))
    all_plans = query.order_by(Plan.id.desc()).all()
    return render_template("subscriptions/plans.html", plans=all_plans, q=q)

@subscriptions_bp.route("/plans/<int:plan_id>/toggle-active", methods=["POST"])
@login_required
def toggle_plan(plan_id):
    plan = Plan.query.get_or_404(plan_id)
    plan.is_active = not plan.is_active
    db.session.commit()
    log_audit("plans.toggle", target_type="plan", target_id=plan.id, details=f"تغيير حالة باقة {plan.name} إلى {'مفعلة' if plan.is_active else 'معطلة'}")
    flash(f"تم تحديث حالة باقة {plan.name}.", "success")
    return redirect(url_for("subscriptions.plans"))
