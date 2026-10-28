import uuid
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Subscription, Plan, Member, Shift, PaymentMethod, Voucher, Account
from app.utils import log_audit

subscriptions_bp = Blueprint("subscriptions", __name__)

@subscriptions_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        member_id = request.form.get("member_id")
        plan_id = request.form.get("plan_id")
        shift_id = request.form.get("shift_id")
        start_date_str = request.form.get("start_date")
        payment_method_id = request.form.get("payment_method_id")
        paid_str = request.form.get("paid_amount")
        notes = request.form.get("notes")

        member = Member.query.get_or_404(int(member_id))
        plan = Plan.query.get_or_404(int(plan_id))

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else date.today()
        end_date = start_date + timedelta(days=plan.duration_days)
        code = f"SUB-{uuid.uuid4().hex[:8].upper()}"
        s_id = int(shift_id) if shift_id and shift_id.isdigit() else None

        # Payment & Debt tracking
        total_amount = float(plan.price)
        if paid_str is not None and paid_str.strip() != "":
            try:
                paid_amount = float(paid_str.strip())
            except ValueError:
                paid_amount = total_amount
        else:
            paid_amount = total_amount

        paid_amount = max(0.0, paid_amount)
        remaining_amount = max(0.0, total_amount - paid_amount)
        if remaining_amount <= 0.0001:
            remaining_amount = 0.0
            payment_status = "مدفوع بالكامل"
        elif paid_amount > 0:
            payment_status = "مدفوع جزئياً"
        else:
            payment_status = "غير مدفوع (آجل)"

        pm_id = int(payment_method_id) if payment_method_id and payment_method_id.isdigit() else None
        if not pm_id:
            default_pm = PaymentMethod.query.filter_by(is_active=True).first()
            pm_id = default_pm.id if default_pm else None

        sub = Subscription(
            subscription_code=code,
            member_id=member.id,
            plan_id=plan.id,
            shift_id=s_id,
            start_date=start_date,
            end_date=end_date,
            price_paid=paid_amount,
            total_amount=total_amount,
            paid_amount=paid_amount,
            remaining_amount=remaining_amount,
            payment_method_id=pm_id,
            payment_status=payment_status,
            notes=notes,
            status="ساري"
        )
        db.session.add(sub)
        db.session.flush()

        # Generate automated receipt voucher if paid_amount > 0
        if paid_amount > 0:
            pm = PaymentMethod.query.get(pm_id) if pm_id else None
            cash_acc = Account.query.filter_by(code="1101").first()
            rev_acc = Account.query.filter_by(code="4101").first()
            target_acc_id = pm.account_id if (pm and pm.account_id) else (cash_acc.id if cash_acc else None)
            contra_acc_id = rev_acc.id if rev_acc else target_acc_id

            if target_acc_id and contra_acc_id:
                v_num = f"VCH-{uuid.uuid4().hex[:8].upper()}"
                pm_name = pm.name if pm else "كاش"
                desc = f"تحصيل اشتراك ({plan.name}) للمشترك {member.full_name} عبر {pm_name}"
                if remaining_amount > 0:
                    desc += f" (دفعة مقدمة - المتبقي عليه: {remaining_amount:,.2f} ر.ي)"
                v = Voucher(
                    voucher_number=v_num,
                    voucher_type="قبض",
                    voucher_date=start_date,
                    amount=paid_amount,
                    account_id=target_acc_id,
                    contra_account_id=contra_acc_id,
                    description=desc,
                    status="مرحل"
                )
                db.session.add(v)

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
    shifts = Shift.query.filter_by(is_active=True).all()
    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
    return render_template("subscriptions/index.html", subscriptions=subs, members=members, plans=plans, shifts=shifts, payment_methods=payment_methods, q=q, status_filter=status_filter)

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

@subscriptions_bp.route("/<int:sub_id>/pay-remaining", methods=["POST"])
@login_required
def pay_remaining(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    pay_amount_str = request.form.get("pay_amount", "0")
    try:
        pay_amount = float(pay_amount_str.strip() or 0.0)
    except ValueError:
        pay_amount = 0.0

    pm_id_str = request.form.get("payment_method_id")
    pm_id = int(pm_id_str) if pm_id_str and pm_id_str.isdigit() else sub.payment_method_id
    pm = PaymentMethod.query.get(pm_id) if pm_id else PaymentMethod.query.filter_by(is_active=True).first()

    if pay_amount <= 0:
        flash("يرجى إدخال مبلغ سداد صحيح أكبر من الصفر.", "danger")
        return redirect(request.referrer or url_for("members.show", member_id=sub.member_id))

    if pay_amount > (sub.remaining_amount or 0.0):
        pay_amount = float(sub.remaining_amount)

    sub.paid_amount = (sub.paid_amount or 0.0) + pay_amount
    sub.remaining_amount = max(0.0, (sub.remaining_amount or 0.0) - pay_amount)
    sub.price_paid = sub.paid_amount

    if sub.remaining_amount <= 0.0001:
        sub.remaining_amount = 0.0
        sub.payment_status = "مدفوع بالكامل"
    else:
        sub.payment_status = "مدفوع جزئياً"

    # Create receipt voucher for the payment
    cash_acc = Account.query.filter_by(code="1101").first()
    rev_acc = Account.query.filter_by(code="4101").first()
    target_acc_id = pm.account_id if (pm and pm.account_id) else (cash_acc.id if cash_acc else None)
    contra_acc_id = rev_acc.id if rev_acc else target_acc_id

    if target_acc_id and contra_acc_id:
        v_num = f"VCH-{uuid.uuid4().hex[:8].upper()}"
        pm_name = pm.name if pm else "كاش"
        desc = f"سداد متبقي اشتراك ({sub.plan.name if sub.plan else ''}) للمشترك {sub.member.full_name} عبر {pm_name}"
        v = Voucher(
            voucher_number=v_num,
            voucher_type="قبض",
            voucher_date=date.today(),
            amount=pay_amount,
            account_id=target_acc_id,
            contra_account_id=contra_acc_id,
            description=desc,
            status="مرحل"
        )
        db.session.add(v)

    db.session.commit()
    log_audit("subscriptions.pay_remaining", target_type="subscription", target_id=sub.id, details=f"سداد متبقي بمبلغ {pay_amount:,.2f} ر.ي لاشتراك {sub.subscription_code} للمشترك {sub.member.full_name}")
    flash(f"تم تسجيل سداد مبلغ {pay_amount:,.2f} ر.ي بنجاح. المتبقي الحالي: {sub.remaining_amount:,.2f} ر.ي", "success")
    return redirect(request.referrer or url_for("members.show", member_id=sub.member_id))
