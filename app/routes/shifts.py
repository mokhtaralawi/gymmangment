from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Shift, Employee, Subscription
from app.utils import log_audit

shifts_bp = Blueprint("shifts", __name__)

@shifts_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        name = request.form.get("name")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        supervisor_name = request.form.get("supervisor_name")
        emp_id_str = request.form.get("employee_id")
        notes = request.form.get("notes")

        emp_id = int(emp_id_str) if emp_id_str and emp_id_str.isdigit() else None

        shift = Shift(
            name=name,
            start_time=start_time,
            end_time=end_time,
            supervisor_name=supervisor_name,
            employee_id=emp_id,
            notes=notes,
            is_active=True
        )
        db.session.add(shift)
        db.session.commit()
        log_audit("shifts.create", target_type="shift", target_id=shift.id, details=f"إنشاء فترة تمرين: {name} ({start_time} - {end_time})")
        flash(f"تم إضافة فترة {name} بنجاح.", "success")
        return redirect(url_for("shifts.index"))

    all_shifts = Shift.query.order_by(Shift.id.asc()).all()
    employees_list = Employee.query.filter_by(is_active=True).all()

    # Calculate subscribers per shift
    shift_stats = {}
    for s in all_shifts:
        count = Subscription.query.filter_by(shift_id=s.id, status="ساري").count()
        shift_stats[s.id] = count

    return render_template("shifts/index.html", shifts=all_shifts, employees=employees_list, stats=shift_stats)

@shifts_bp.route("/<int:shift_id>/toggle-active", methods=["POST"])
@login_required
def toggle_active(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    shift.is_active = not shift.is_active
    db.session.commit()
    log_audit("shifts.toggle", target_type="shift", target_id=shift.id, details=f"تحديث حالة فترة {shift.name} إلى {'مفعلة' if shift.is_active else 'معطلة'}")
    flash(f"تم تحديث حالة فترة {shift.name}.", "success")
    return redirect(url_for("shifts.index"))

@shifts_bp.route("/<int:shift_id>/edit", methods=["POST"])
@login_required
def edit(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    shift.name = request.form.get("name", shift.name)
    shift.start_time = request.form.get("start_time", shift.start_time)
    shift.end_time = request.form.get("end_time", shift.end_time)
    shift.supervisor_name = request.form.get("supervisor_name", shift.supervisor_name)
    emp_id_str = request.form.get("employee_id")
    shift.employee_id = int(emp_id_str) if emp_id_str and emp_id_str.isdigit() else None
    shift.notes = request.form.get("notes", shift.notes)

    db.session.commit()
    log_audit("shifts.edit", target_type="shift", target_id=shift.id, details=f"تعديل بيانات فترة {shift.name}")
    flash(f"تم حفظ تعديلات فترة {shift.name} بنجاح.", "success")
    return redirect(url_for("shifts.index"))
