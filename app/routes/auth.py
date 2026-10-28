from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User
from app.utils import log_audit

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember_me"))

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("هذا الحساب معطل، يرجى التواصل مع الإدارة.", "danger")
                return render_template("auth/login.html")

            login_user(user, remember=remember)
            log_audit("auth.login", target_type="user", target_id=user.id, details="تسجيل دخول ناجح")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))
        else:
            flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "danger")
            log_audit("auth.failed_login", target_type="user", details=f"محاولة فاشلة لاسم: {username}")

    return render_template("auth/login.html")

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_audit("auth.logout", target_type="user", target_id=current_user.id)
    logout_user()
    return redirect(url_for("auth.login"))

@auth_bp.route("/users", methods=["GET", "POST"])
@login_required
def users():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        username = request.form.get("username")
        role_id = request.form.get("role_id", "مدير النظام")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("كلمات المرور غير متطابقة.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("اسم المستخدم موجود بالفعل.", "warning")
        else:
            new_u = User(username=username, full_name=full_name, role_name=role_id, is_active=True)
            new_u.set_password(password)
            db.session.add(new_u)
            db.session.commit()
            log_audit("users.create", target_type="user", target_id=new_u.id, details=f"إنشاء مستخدم {username}")
            flash("تم إضافة المستخدم بنجاح.", "success")
            return redirect(url_for("auth.users"))

    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        query = query.filter((User.full_name.contains(q)) | (User.username.contains(q)))
    users_list = query.order_by(User.id.desc()).all()
    return render_template("auth/users.html", users=users_list, q=q)

@auth_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
def toggle_user_active(user_id):
    if user_id == current_user.id:
        flash("لا يمكنك تعطيل حسابك الشخصي الحالي.", "danger")
        return redirect(url_for("auth.users"))
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    log_audit("users.toggle_active", target_type="user", target_id=user.id, details=f"تغيير حالة المستخدم إلى {'نشط' if user.is_active else 'معطل'}")
    flash(f"تم تحديث حالة المستخدم {user.full_name}.", "success")
    return redirect(url_for("auth.users"))

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not current_user.check_password(old_password):
            flash("كلمة المرور الحالية غير صحيحة.", "danger")
        elif new_password != confirm_password:
            flash("كلمات المرور الجديدة غير متطابقة.", "danger")
        elif len(new_password) < 6:
            flash("كلمة المرور يجب أن تكون 6 أحرف على الأقل.", "warning")
        else:
            current_user.set_password(new_password)
            db.session.commit()
            log_audit("auth.change_password", target_type="user", target_id=current_user.id)
            flash("تم تحديث كلمة المرور بنجاح.", "success")
            return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html")
