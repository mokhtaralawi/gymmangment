from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, MemberAttendance, Member, Subscription
from app.utils import log_audit

attendance_bp = Blueprint("attendance", __name__)

@attendance_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        member_id = request.form.get("member_id")
        note = request.form.get("note")
        req_key = request.form.get("request_key")

        # Double submit check
        if req_key and MemberAttendance.query.filter_by(request_key=req_key).first():
            flash("تم تسجيل هذه الحركة مسبقاً لمنع التكرار.", "info")
            return redirect(url_for("attendance.index"))

        member = Member.query.get_or_404(int(member_id))
        active_sub = member.active_subscription

        att = MemberAttendance(
            member_id=member.id,
            subscription_id=active_sub.id if active_sub else None,
            note=note,
            request_key=req_key
        )
        db.session.add(att)
        db.session.commit()
        log_audit("member_attendance.check_in", target_type="attendance", target_id=att.id, details=f"حضور المشترك: {member.full_name}")

        if active_sub:
            flash(f"تم تسجيل حضور المشترك {member.full_name} بنجاح (الاشتراك ساري، متبقي {active_sub.remaining_days} يوم).", "success")
        else:
            flash(f"تنبيه: تم تسجيل حضور {member.full_name} ولكن لا يوجد اشتراك ساري!", "warning")

        return redirect(url_for("attendance.index"))

    q = request.args.get("q", "").strip()
    query = MemberAttendance.query.join(Member)
    if q:
        query = query.filter((Member.full_name.contains(q)) | (Member.member_code.contains(q)))

    attendances = query.order_by(MemberAttendance.id.desc()).all()
    members = Member.query.filter_by(status="نشط").all()
    return render_template("attendance/index.html", attendances=attendances, members=members, q=q)
