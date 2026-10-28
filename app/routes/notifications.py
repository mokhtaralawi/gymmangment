from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, NotificationRule, Notification, Subscription, Member
from app.utils import log_audit

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/")
@login_required
def index():
    # Scan for expiring subscriptions if rule is enabled
    rule = NotificationRule.query.first()
    if rule and rule.is_enabled:
        today = date.today()
        threshold = today + timedelta(days=rule.days_before)
        expiring_subs = Subscription.query.filter(
            Subscription.status == "ساري",
            Subscription.end_date <= threshold,
            Subscription.end_date >= today
        ).all()

        for s in expiring_subs:
            notif_title = f"اقتراب انتهاء اشتراك: {s.member.full_name}"
            existing = Notification.query.filter_by(title=notif_title).first()
            if not existing:
                n = Notification(
                    title=notif_title,
                    message=f"الاشتراك {s.subscription_code} للباقة ({s.plan.name}) سينتهي بتاريخ {s.end_date}.",
                    category="اشتراكات"
                )
                db.session.add(n)
        db.session.commit()

    all_notifs = Notification.query.order_by(Notification.id.desc()).all()
    return render_template("notifications/index.html", notifications=all_notifs)

@notifications_bp.route("/rules", methods=["GET", "POST"])
@login_required
def rules():
    rule = NotificationRule.query.first()
    if not rule:
        rule = NotificationRule(days_before=7, days_after=30, is_enabled=True)
        db.session.add(rule)
        db.session.commit()

    if request.method == "POST":
        rule.days_before = int(request.form.get("days_before", 7))
        rule.days_after = int(request.form.get("days_after", 30))
        rule.is_enabled = bool(request.form.get("is_enabled"))
        db.session.commit()
        log_audit("notifications.update_rules", details="تحديث قواعد تنبيهات انتهاء الاشتراك")
        flash("تم حفظ إعدادات قواعد التنبيه بنجاح.", "success")
        return redirect(url_for("notifications.rules"))

    return render_template("notifications/rules.html", rule=rule)
