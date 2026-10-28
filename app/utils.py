from flask import request
from flask_login import current_user
from app.models import db, AuditLog

def log_audit(action, target_type=None, target_id=None, details=None):
    try:
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        username = current_user.username if current_user and current_user.is_authenticated else "anonymous"
        ip = request.remote_addr or "127.0.0.1"
        audit = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            details=details,
            ip_address=ip
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Failed to log audit: {e}")
