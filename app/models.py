from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role_name = db.Column(db.String(50), default="مدير النظام")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Member(db.Model):
    __tablename__ = "members"
    id = db.Column(db.Integer, primary_key=True)
    member_code = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    gender = db.Column(db.String(20), default="ذكر")
    birth_date = db.Column(db.Date, nullable=True)
    address = db.Column(db.String(255), default="غير مسجل")
    emergency_contact_name = db.Column(db.String(150), default="غير مسجل")
    emergency_contact_phone = db.Column(db.String(50), default="غير مسجل")
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default="نشط")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subscriptions = db.relationship("Subscription", backref="member", lazy=True, cascade="all, delete-orphan")
    attendances = db.relationship("MemberAttendance", backref="member", lazy=True, cascade="all, delete-orphan")

    @property
    def active_subscription(self):
        for sub in self.subscriptions:
            if sub.is_active_now:
                return sub
        return None

class Plan(db.Model):
    __tablename__ = "plans"
    id = db.Column(db.Integer, primary_key=True)
    plan_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class Subscription(db.Model):
    __tablename__ = "subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    subscription_code = db.Column(db.String(50), unique=True, nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=False)
    price_paid = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="ساري")
    cancel_reason = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    plan = db.relationship("Plan", backref="subscriptions")

    @property
    def is_active_now(self):
        return self.status == "ساري" and self.end_date >= date.today()

    @property
    def remaining_days(self):
        delta = (self.end_date - date.today()).days
        return max(0, delta)

class MemberAttendance(db.Model):
    __tablename__ = "member_attendances"
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id"), nullable=True)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(255), nullable=True)
    request_key = db.Column(db.String(100), nullable=True)

class Employee(db.Model):
    __tablename__ = "employees"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    hire_date = db.Column(db.Date, default=date.today)
    device_code = db.Column(db.String(50), nullable=True)
    basic_salary = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendances = db.relationship("EmployeeAttendance", backref="employee", lazy=True)
    payrolls = db.relationship("Payroll", backref="employee", lazy=True)

class EmployeeAttendance(db.Model):
    __tablename__ = "employee_attendances"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    check_time = db.Column(db.DateTime, default=datetime.utcnow)
    direction = db.Column(db.String(20), default="حضور")
    note = db.Column(db.String(255), nullable=True)
    request_key = db.Column(db.String(100), nullable=True)

class Payroll(db.Model):
    __tablename__ = "payrolls"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    month = db.Column(db.String(10), nullable=False)
    basic_salary = db.Column(db.Float, default=0.0)
    bonus = db.Column(db.Float, default=0.0)
    deductions = db.Column(db.Float, default=0.0)
    loan_deduction = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="مسودة")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Account(db.Model):
    __tablename__ = "accounts"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=True)
    node_type = db.Column(db.String(30), default="فرعي")
    is_postable = db.Column(db.Boolean, default=True)
    balance = db.Column(db.Float, default=0.0)

    children = db.relationship("Account", backref=db.backref("parent", remote_side=[id]), lazy=True)

class Voucher(db.Model):
    __tablename__ = "vouchers"
    id = db.Column(db.Integer, primary_key=True)
    voucher_number = db.Column(db.String(50), unique=True, nullable=False)
    voucher_type = db.Column(db.String(20), nullable=False)
    voucher_date = db.Column(db.Date, default=date.today)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    contra_account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), default="مرحل")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship("Account", foreign_keys=[account_id])
    contra_account = db.relationship("Account", foreign_keys=[contra_account_id])

class JournalEntry(db.Model):
    __tablename__ = "journal_entries"
    id = db.Column(db.Integer, primary_key=True)
    entry_number = db.Column(db.String(50), unique=True, nullable=False)
    entry_date = db.Column(db.Date, default=date.today)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lines = db.relationship("JournalEntryLine", backref="entry", lazy=True, cascade="all, delete-orphan")

class JournalEntryLine(db.Model):
    __tablename__ = "journal_entry_lines"
    id = db.Column(db.Integer, primary_key=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey("journal_entries.id"), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    debit = db.Column(db.Float, default=0.0)
    credit = db.Column(db.Float, default=0.0)
    description = db.Column(db.String(255), nullable=True)

    account = db.relationship("Account")

class NotificationRule(db.Model):
    __tablename__ = "notification_rules"
    id = db.Column(db.Integer, primary_key=True)
    days_before = db.Column(db.Integer, default=7)
    days_after = db.Column(db.Integer, default=30)
    is_enabled = db.Column(db.Boolean, default=True)

class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default="اشتراكات")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    username = db.Column(db.String(80), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), default="127.0.0.1")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
