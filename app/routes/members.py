import uuid
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Member, Subscription, Plan, Shift, PaymentMethod, Voucher, Account
from app.utils import log_audit

members_bp = Blueprint("members", __name__)

@members_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        gender = request.form.get("gender", "ذكر")
        birth_date_str = request.form.get("birth_date")
        initial_plan_id = request.form.get("initial_plan_id")
        shift_id = request.form.get("shift_id")
        subscription_start_date_str = request.form.get("subscription_start_date")
        emergency_name = request.form.get("emergency_contact_name")
        emergency_phone = request.form.get("emergency_contact_phone")
        address = request.form.get("address")
        notes = request.form.get("notes")

        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date() if birth_date_str else None
        code = f"MBR-{uuid.uuid4().hex[:8].upper()}"

        member = Member(
            member_code=code,
            full_name=full_name,
            phone=phone,
            gender=gender,
            birth_date=birth_date,
            emergency_contact_name=emergency_name or "غير مسجل",
            emergency_contact_phone=emergency_phone or "غير مسجل",
            address=address or "غير مسجل",
            notes=notes,
            status="نشط"
        )
        db.session.add(member)
        db.session.flush()

        # If an initial plan was selected, create subscription immediately!
        if initial_plan_id and initial_plan_id.isdigit():
            plan = Plan.query.get(int(initial_plan_id))
            if plan:
                if subscription_start_date_str and subscription_start_date_str.strip():
                    try:
                        start_d = datetime.strptime(subscription_start_date_str.strip(), "%Y-%m-%d").date()
                    except ValueError:
                        start_d = date.today()
                else:
                    start_d = date.today()

                end_d = start_d + timedelta(days=plan.duration_days)
                sub_code = f"SUB-{uuid.uuid4().hex[:8].upper()}"
                s_id = int(shift_id) if shift_id and shift_id.isdigit() else None

                # Payment & Debt tracking
                total_amount = float(plan.price)
                paid_str = request.form.get("paid_amount")
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

                pm_id_str = request.form.get("payment_method_id")
                pm_id = int(pm_id_str) if pm_id_str and pm_id_str.isdigit() else None
                if not pm_id:
                    default_pm = PaymentMethod.query.filter_by(is_active=True).first()
                    pm_id = default_pm.id if default_pm else None

                sub = Subscription(
                    subscription_code=sub_code,
                    member_id=member.id,
                    plan_id=plan.id,
                    shift_id=s_id,
                    start_date=start_d,
                    end_date=end_d,
                    price_paid=paid_amount,
                    total_amount=total_amount,
                    paid_amount=paid_amount,
                    remaining_amount=remaining_amount,
                    payment_method_id=pm_id,
                    payment_status=payment_status,
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
                            voucher_date=start_d,
                            amount=paid_amount,
                            account_id=target_acc_id,
                            contra_account_id=contra_acc_id,
                            description=desc,
                            status="مرحل"
                        )
                        db.session.add(v)

        db.session.commit()
        log_audit("members.create", target_type="member", target_id=member.id, details=f"إضافة مشترك: {full_name}")
        flash(f"تم إضافة المشترك {full_name} بنجاح.", "success")
        return redirect(url_for("members.show", member_id=member.id))

    q = request.args.get("q", "").strip()
    query = Member.query
    if q:
        query = query.filter((Member.full_name.contains(q)) | (Member.phone.contains(q)) | (Member.member_code.contains(q)))
    members_list = query.order_by(Member.id.desc()).all()
    plans = Plan.query.filter_by(is_active=True).all()
    shifts = Shift.query.filter_by(is_active=True).all()
    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()

    today_str = date.today().strftime("%Y-%m-%d")
    return render_template("members/index.html", members=members_list, plans=plans, shifts=shifts, payment_methods=payment_methods, q=q, today=today_str)

@members_bp.route("/<int:member_id>")
@login_required
def show(member_id):
    member = Member.query.get_or_404(member_id)
    plans = Plan.query.filter_by(is_active=True).all()
    shifts = Shift.query.filter_by(is_active=True).all()
    payment_methods = PaymentMethod.query.filter_by(is_active=True).all()
    return render_template("members/show.html", member=member, plans=plans, shifts=shifts, payment_methods=payment_methods)

@members_bp.route("/<int:member_id>/edit", methods=["POST"])
@login_required
def edit(member_id):
    member = Member.query.get_or_404(member_id)
    member.full_name = request.form.get("full_name", member.full_name)
    member.phone = request.form.get("phone", member.phone)
    member.gender = request.form.get("gender", member.gender)
    birth_date_str = request.form.get("birth_date")
    if birth_date_str:
        member.birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
    member.emergency_contact_name = request.form.get("emergency_contact_name", member.emergency_contact_name)
    member.emergency_contact_phone = request.form.get("emergency_contact_phone", member.emergency_contact_phone)
    member.address = request.form.get("address", member.address)
    member.notes = request.form.get("notes", member.notes)
    
    db.session.commit()
    log_audit("members.edit", target_type="member", target_id=member.id, details=f"تعديل بيانات {member.full_name}")
    flash("تم حفظ التعديلات بنجاح.", "success")
    return redirect(url_for("members.show", member_id=member.id))
