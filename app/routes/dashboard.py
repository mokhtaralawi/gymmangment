from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Member, Subscription, MemberAttendance, Voucher, Plan

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@login_required
def index():
    today = date.today()
    active_members_count = Member.query.filter_by(status="نشط").count()
    active_subs_count = Subscription.query.filter(Subscription.status == "ساري", Subscription.end_date >= today).count()
    today_attendances_count = MemberAttendance.query.filter(db_cast_date(MemberAttendance.check_in_time) == today).count() if hasattr(MemberAttendance, 'check_in_time') else 0
    
    # Calculate revenue & expenses
    vouchers = Voucher.query.all()
    total_receipts = sum(v.amount for v in vouchers if v.voucher_type == "قبض")
    total_payments = sum(v.amount for v in vouchers if v.voucher_type == "صرف")

    recent_members = Member.query.order_by(Member.id.desc()).limit(5).all()
    recent_subs = Subscription.query.order_by(Subscription.id.desc()).limit(5).all()

    return render_template(
        "dashboard/index.html",
        active_members_count=active_members_count,
        active_subs_count=active_subs_count,
        today_attendances_count=today_attendances_count,
        total_receipts=total_receipts,
        total_payments=total_payments,
        recent_members=recent_members,
        recent_subs=recent_subs
    )

def db_cast_date(col):
    from sqlalchemy import func
    return func.date(col)
