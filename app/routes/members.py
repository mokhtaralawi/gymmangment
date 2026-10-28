import uuid
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Member, Subscription, Plan
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
                start_d = date.today()
                end_d = start_d + timedelta(days=plan.duration_days)
                sub_code = f"SUB-{uuid.uuid4().hex[:8].upper()}"
                sub = Subscription(
                    subscription_code=sub_code,
                    member_id=member.id,
                    plan_id=plan.id,
                    start_date=start_d,
                    end_date=end_d,
                    price_paid=plan.price,
                    status="ساري"
                )
                db.session.add(sub)

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

    return render_template("members/index.html", members=members_list, plans=plans, q=q)

@members_bp.route("/<int:member_id>")
@login_required
def show(member_id):
    member = Member.query.get_or_404(member_id)
    plans = Plan.query.filter_by(is_active=True).all()
    return render_template("members/show.html", member=member, plans=plans)

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
