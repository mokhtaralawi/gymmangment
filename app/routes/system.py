import os
import shutil
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for, current_app
from flask_login import login_required
from app.models import AuditLog
from app.utils import log_audit

system_bp = Blueprint("system", __name__)

@system_bp.route("/audit")
@login_required
def audit():
    q = request.args.get("q", "").strip()
    query = AuditLog.query
    if q:
        query = query.filter(
            (AuditLog.action.contains(q)) |
            (AuditLog.username.contains(q)) |
            (AuditLog.details.contains(q)) |
            (AuditLog.ip_address.contains(q))
        )
    logs = query.order_by(AuditLog.id.desc()).limit(100).all()
    return render_template("system/audit.html", logs=logs, q=q)

@system_bp.route("/backup")
@login_required
def backup():
    backup_dir = os.path.join(current_app.root_path, "..", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backups_list = []
    for f in os.listdir(backup_dir):
        if f.endswith(".db"):
            fp = os.path.join(backup_dir, f)
            backups_list.append({
                "filename": f,
                "size": f"{os.path.getsize(fp) / 1024:.1f} KB",
                "date": datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
            })
    return render_template("system/backup.html", backups=backups_list)

@system_bp.route("/backup/create", methods=["POST"])
@login_required
def create_backup():
    db_path = os.path.join(current_app.root_path, "..", "nadi.db")
    backup_dir = os.path.join(current_app.root_path, "..", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"nadi_backup_{timestamp}.db"
    dest_path = os.path.join(backup_dir, backup_filename)

    if os.path.exists(db_path):
        shutil.copy2(db_path, dest_path)
        log_audit("system.backup", details=f"إنشاء نسخة احتياطية: {backup_filename}")
        flash(f"تم إنشاء النسخة الاحتياطية بنجاح: {backup_filename}", "success")
    else:
        flash("ملف قاعدة البيانات غير متوفر لإنشاء النسخة.", "danger")

    return redirect(url_for("system.backup"))

@system_bp.route("/backup/download/<filename>")
@login_required
def download_backup(filename):
    backup_dir = os.path.join(current_app.root_path, "..", "backups")
    file_path = os.path.join(backup_dir, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    flash("الملف غير موجود.", "danger")
    return redirect(url_for("system.backup"))
