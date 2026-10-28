import csv
import io
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Employee, EmployeeAttendance, Payroll
from app.utils import log_audit

employees_bp = Blueprint("employees", __name__)

@employees_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        job_title = request.form.get("job_title")
        hire_date_str = request.form.get("hire_date")
        device_code = request.form.get("device_code")
        basic_salary = float(request.form.get("basic_salary", 0.0) or 0.0)
        notes = request.form.get("notes")

        hire_date = datetime.strptime(hire_date_str, "%Y-%m-%d").date() if hire_date_str else date.today()

        emp = Employee(
            full_name=full_name,
            phone=phone,
            job_title=job_title,
            hire_date=hire_date,
            device_code=device_code,
            basic_salary=basic_salary,
            notes=notes,
            is_active=True
        )
        db.session.add(emp)
        db.session.commit()
        log_audit("employees.create", target_type="employee", target_id=emp.id, details=f"إضافة موظف: {full_name}")
        flash(f"تم إضافة الموظف {full_name} بنجاح.", "success")
        return redirect(url_for("employees.index"))

    q = request.args.get("q", "").strip()
    query = Employee.query
    if q:
        query = query.filter((Employee.full_name.contains(q)) | (Employee.phone.contains(q)) | (Employee.job_title.contains(q)))
    employees_list = query.order_by(Employee.id.desc()).all()
    return render_template("employees/index.html", employees=employees_list, q=q)

@employees_bp.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    if request.method == "POST":
        emp_id = request.form.get("employee_id")
        direction = request.form.get("direction", "حضور")
        note = request.form.get("note")
        req_key = request.form.get("request_key")

        if req_key and EmployeeAttendance.query.filter_by(request_key=req_key).first():
            flash("تم تسجيل الحركة مسبقاً لمنع التكرار.", "info")
            return redirect(url_for("employees.attendance"))

        emp = Employee.query.get_or_404(int(emp_id))
        att = EmployeeAttendance(
            employee_id=emp.id,
            direction=direction,
            note=note,
            request_key=req_key
        )
        db.session.add(att)
        db.session.commit()
        log_audit("employees.attendance", target_type="employee_attendance", target_id=att.id, details=f"تسجيل {direction} للموظف {emp.full_name}")
        flash(f"تم تسجيل {direction} للموظف {emp.full_name}.", "success")
        return redirect(url_for("employees.attendance"))

    q = request.args.get("q", "").strip()
    query = EmployeeAttendance.query.join(Employee)
    if q:
        query = query.filter(Employee.full_name.contains(q))
    records = query.order_by(EmployeeAttendance.id.desc()).all()
    employees_list = Employee.query.filter_by(is_active=True).all()
    return render_template("employees/attendance.html", records=records, employees=employees_list, q=q)

@employees_bp.route("/attendance/import", methods=["POST"])
@login_required
def import_attendance():
    if "file" not in request.files:
        flash("لم يتم تحديد ملف للاستيراد.", "danger")
        return redirect(url_for("employees.attendance"))

    file = request.files["file"]
    if file.filename == "":
        flash("الملف المحدد فارغ.", "warning")
        return redirect(url_for("employees.attendance"))

    try:
        stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
        reader = csv.reader(stream)
        imported_count = 0
        for row in reader:
            if not row or len(row) < 2:
                continue
            # Typical biometric CSV: device_code, timestamp, direction (optional)
            dev_code = row[0].strip()
            time_str = row[1].strip()
            direction = row[2].strip() if len(row) > 2 else "حضور"

            emp = Employee.query.filter_by(device_code=dev_code).first()
            if emp:
                try:
                    check_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    check_time = datetime.utcnow()
                att = EmployeeAttendance(
                    employee_id=emp.id,
                    check_time=check_time,
                    direction=direction,
                    note="استيراد من جهاز البصمة"
                )
                db.session.add(att)
                imported_count += 1
        db.session.commit()
        log_audit("employees.import_csv", details=f"استيراد {imported_count} حركة حضور من CSV")
        flash(f"تم استيراد {imported_count} حركة بنجاح.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"حدث خطأ أثناء معالجة الملف: {e}", "danger")

    return redirect(url_for("employees.attendance"))

@employees_bp.route("/payroll", methods=["GET", "POST"])
@login_required
def payroll():
    current_month = date.today().strftime("%Y-%m")
    selected_month = request.args.get("month", current_month)

    employees_list = Employee.query.filter_by(is_active=True).all()
    
    # Generate payroll items if not exist
    for emp in employees_list:
        p = Payroll.query.filter_by(employee_id=emp.id, month=selected_month).first()
        if not p:
            p = Payroll(
                employee_id=emp.id,
                month=selected_month,
                basic_salary=emp.basic_salary,
                bonus=0.0,
                deductions=0.0,
                loan_deduction=0.0,
                net_salary=emp.basic_salary,
                status="مسودة"
            )
            db.session.add(p)
    db.session.commit()

    payroll_records = Payroll.query.filter_by(month=selected_month).join(Employee).all()

    total_basic = sum(r.basic_salary for r in payroll_records)
    total_bonus = sum(r.bonus for r in payroll_records)
    total_deductions = sum(r.deductions for r in payroll_records)
    total_loans = sum(r.loan_deduction for r in payroll_records)
    total_net = sum(r.net_salary for r in payroll_records)

    return render_template(
        "employees/payroll.html",
        records=payroll_records,
        month=selected_month,
        total_basic=total_basic,
        total_bonus=total_bonus,
        total_deductions=total_deductions,
        total_loans=total_loans,
        total_net=total_net
    )

@employees_bp.route("/payroll/<int:p_id>/update", methods=["POST"])
@login_required
def update_payroll_item(p_id):
    p = Payroll.query.get_or_404(p_id)
    p.bonus = float(request.form.get("bonus", 0.0) or 0.0)
    p.deductions = float(request.form.get("deductions", 0.0) or 0.0)
    p.loan_deduction = float(request.form.get("loan_deduction", 0.0) or 0.0)
    p.net_salary = p.basic_salary + p.bonus - p.deductions - p.loan_deduction
    p.status = "معتمد"
    db.session.commit()
    log_audit("payroll.update", target_type="payroll", target_id=p.id, details=f"تحديث مسير {p.employee.full_name} لشهر {p.month}")
    flash(f"تم تحديث راتب {p.employee.full_name}.", "success")
    return redirect(url_for("employees.payroll", month=p.month))
