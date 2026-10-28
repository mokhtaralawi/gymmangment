from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from app.models import db, Member, Subscription, Plan, Shift, PaymentMethod, Voucher, Account, MemberAttendance
from sqlalchemy import func

reports_bp = Blueprint("reports", __name__)

@reports_bp.route("/")
@login_required
def index():
    period = request.args.get("period", "today")
    today = date.today()

    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if period == "today":
        start_date = today
        end_date = today
    elif period == "weekly":
        # Past 7 days
        start_date = today - timedelta(days=6)
        end_date = today
    elif period == "monthly":
        # First day of current month to today
        start_date = today.replace(day=1)
        end_date = today
    elif period == "custom" and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = today
            end_date = today
    else:
        start_date = today
        end_date = today

    # Convert to datetimes for timestamped queries
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # 1. New Members in period
    new_members = Member.query.filter(Member.created_at >= start_dt, Member.created_at <= end_dt).all()
    new_members_count = len(new_members)

    # 2. Subscriptions created in period
    subs_in_period = Subscription.query.filter(Subscription.start_date >= start_date, Subscription.start_date <= end_date).all()
    subs_count = len(subs_in_period)

    # Total subscription revenue and remaining debts
    sub_total_value = sum(s.total_amount if s.total_amount else s.price_paid for s in subs_in_period)
    sub_paid_value = sum(s.paid_amount if s.paid_amount is not None else s.price_paid for s in subs_in_period)
    sub_remaining_debts = sum(s.remaining_amount or 0.0 for s in subs_in_period)

    # 3. Financial Vouchers (Income vs Expenses)
    income_vouchers = Voucher.query.filter(
        Voucher.voucher_type == "قبض",
        Voucher.voucher_date >= start_date,
        Voucher.voucher_date <= end_date
    ).order_by(Voucher.voucher_date.desc()).all()
    total_income = sum(v.amount for v in income_vouchers)

    expense_vouchers = Voucher.query.filter(
        Voucher.voucher_type == "صرف",
        Voucher.voucher_date >= start_date,
        Voucher.voucher_date <= end_date
    ).order_by(Voucher.voucher_date.desc()).all()
    total_expenses = sum(v.amount for v in expense_vouchers)

    net_profit = total_income - total_expenses

    # 4. Attendances count in period
    attendance_count = MemberAttendance.query.filter(
        MemberAttendance.check_in_time >= start_dt,
        MemberAttendance.check_in_time <= end_dt
    ).count()

    # 5. Breakdown by Payment Method
    all_methods = PaymentMethod.query.all()
    payment_breakdown = []
    for m in all_methods:
        method_subs = [s for s in subs_in_period if s.payment_method_id == m.id]
        collected = sum(s.paid_amount if s.paid_amount is not None else s.price_paid for s in method_subs)
        if len(method_subs) > 0 or collected > 0:
            payment_breakdown.append({
                "method": m,
                "count": len(method_subs),
                "total_collected": collected
            })

    # 6. Breakdown by Subscription Plan
    all_plans = Plan.query.all()
    plan_breakdown = []
    for p in all_plans:
        plan_subs = [s for s in subs_in_period if s.plan_id == p.id]
        if len(plan_subs) > 0:
            plan_breakdown.append({
                "plan": p,
                "count": len(plan_subs),
                "total_revenue": sum(s.paid_amount if s.paid_amount is not None else s.price_paid for s in plan_subs)
            })

    # 7. Breakdown by Training Shifts
    all_shifts = Shift.query.all()
    shift_breakdown = []
    for sh in all_shifts:
        sh_subs = [s for s in subs_in_period if s.shift_id == sh.id]
        shift_breakdown.append({
            "shift": sh,
            "count": len(sh_subs)
        })

    return render_template(
        "reports/index.html",
        period=period,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        today=today.strftime("%Y-%m-%d"),
        new_members_count=new_members_count,
        subs_count=subs_count,
        sub_total_value=sub_total_value,
        sub_paid_value=sub_paid_value,
        sub_remaining_debts=sub_remaining_debts,
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=net_profit,
        attendance_count=attendance_count,
        income_vouchers=income_vouchers,
        expense_vouchers=expense_vouchers,
        payment_breakdown=payment_breakdown,
        plan_breakdown=plan_breakdown,
        shift_breakdown=shift_breakdown
    )

@reports_bp.route("/daily-balance")
@login_required
def daily_balance():
    d_str = request.args.get("date")
    if d_str:
        try:
            target_date = datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    # Vouchers for the day
    income_vouchers = Voucher.query.filter_by(voucher_type="قبض", voucher_date=target_date).order_by(Voucher.id.desc()).all()
    expense_vouchers = Voucher.query.filter_by(voucher_type="صرف", voucher_date=target_date).order_by(Voucher.id.desc()).all()

    total_income = sum(v.amount for v in income_vouchers)
    total_expenses = sum(v.amount for v in expense_vouchers)
    net_balance = total_income - total_expenses

    # Subscriptions created on this day
    subs_today = Subscription.query.filter_by(start_date=target_date).all()
    total_subs_paid = sum(s.paid_amount if s.paid_amount is not None else s.price_paid for s in subs_today)
    total_subs_remaining = sum(s.remaining_amount or 0.0 for s in subs_today)

    # Cash method vouchers vs electronic/bank
    cash_acc = Account.query.filter_by(code="1101").first()
    cash_income = sum(v.amount for v in income_vouchers if cash_acc and v.account_id == cash_acc.id)
    cash_expense = sum(v.amount for v in expense_vouchers if cash_acc and v.account_id == cash_acc.id)
    cash_net = cash_income - cash_expense

    electronic_income = total_income - cash_income

    return render_template(
        "reports/daily_balance.html",
        target_date=target_date,
        target_date_str=target_date.strftime("%Y-%m-%d"),
        income_vouchers=income_vouchers,
        expense_vouchers=expense_vouchers,
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=net_balance,
        subs_today=subs_today,
        total_subs_paid=total_subs_paid,
        total_subs_remaining=total_subs_remaining,
        cash_income=cash_income,
        cash_expense=cash_expense,
        cash_net=cash_net,
        electronic_income=electronic_income
    )

@reports_bp.route("/daily-balance/thermal")
@login_required
def daily_balance_thermal():
    d_str = request.args.get("date")
    if d_str:
        try:
            target_date = datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    income_vouchers = Voucher.query.filter_by(voucher_type="قبض", voucher_date=target_date).all()
    expense_vouchers = Voucher.query.filter_by(voucher_type="صرف", voucher_date=target_date).all()

    total_income = sum(v.amount for v in income_vouchers)
    total_expenses = sum(v.amount for v in expense_vouchers)
    net_balance = total_income - total_expenses

    subs_today = Subscription.query.filter_by(start_date=target_date).all()
    auto_print = request.args.get("auto_print", "1") == "1"

    now = datetime.now()

    return render_template(
        "reports/daily_balance_thermal.html",
        target_date=target_date,
        income_vouchers=income_vouchers,
        expense_vouchers=expense_vouchers,
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=net_balance,
        subs_today=subs_today,
        auto_print=auto_print,
        now=now
    )
