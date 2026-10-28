import uuid
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Account, Voucher, JournalEntry, JournalEntryLine
from app.utils import log_audit

accounting_bp = Blueprint("accounting", __name__)

@accounting_bp.route("/vouchers", methods=["GET", "POST"])
@login_required
def vouchers():
    if request.method == "POST":
        voucher_type = request.form.get("voucher_type", "قبض")
        voucher_date_str = request.form.get("voucher_date")
        amount = float(request.form.get("amount", 0.0) or 0.0)
        account_id = int(request.form.get("account_id"))
        contra_account_id = int(request.form.get("contra_account_id"))
        description = request.form.get("description")

        voucher_date = datetime.strptime(voucher_date_str, "%Y-%m-%d").date() if voucher_date_str else date.today()
        v_num = f"VCH-{uuid.uuid4().hex[:8].upper()}"

        v = Voucher(
            voucher_number=v_num,
            voucher_type=voucher_type,
            voucher_date=voucher_date,
            amount=amount,
            account_id=account_id,
            contra_account_id=contra_account_id,
            description=description,
            status="مرحل"
        )
        db.session.add(v)

        # Update account balances and create journal entry
        acc1 = Account.query.get(account_id)
        acc2 = Account.query.get(contra_account_id)

        j_entry = JournalEntry(
            entry_number=f"JRN-{uuid.uuid4().hex[:8].upper()}",
            entry_date=voucher_date,
            description=f"سند {voucher_type}: {description or ''}"
        )
        db.session.add(j_entry)
        db.session.flush()

        if voucher_type == "قبض":
            # Cash increases (Debit), Revenue/Source credited
            acc1.balance += amount
            acc2.balance += amount
            line1 = JournalEntryLine(journal_entry_id=j_entry.id, account_id=acc1.id, debit=amount, credit=0.0, description=description)
            line2 = JournalEntryLine(journal_entry_id=j_entry.id, account_id=acc2.id, debit=0.0, credit=amount, description=description)
        else:
            # Expense debited, Cash decreases (Credit)
            acc2.balance += amount
            acc1.balance -= amount
            line1 = JournalEntryLine(journal_entry_id=j_entry.id, account_id=acc2.id, debit=amount, credit=0.0, description=description)
            line2 = JournalEntryLine(journal_entry_id=j_entry.id, account_id=acc1.id, debit=0.0, credit=amount, description=description)

        db.session.add(line1)
        db.session.add(line2)
        db.session.commit()

        log_audit("accounting.voucher", target_type="voucher", target_id=v.id, details=f"إنشاء سند {voucher_type} بمبلغ {amount}")
        flash(f"تم تسجيل وترحيل سند {voucher_type} رقم {v_num} بنجاح.", "success")
        return redirect(url_for("accounting.vouchers"))

    q = request.args.get("q", "").strip()
    v_type = request.args.get("type", "")
    query = Voucher.query
    if q:
        query = query.filter((Voucher.voucher_number.contains(q)) | (Voucher.description.contains(q)))
    if v_type:
        query = query.filter(Voucher.voucher_type == v_type)

    all_vouchers = query.order_by(Voucher.id.desc()).all()
    cash_accounts = Account.query.filter(Account.node_type.in_(["صندوق", "بنك"])).all()
    all_postable_accounts = Account.query.filter_by(is_postable=True).all()

    total_receipts = sum(v.amount for v in all_vouchers if v.voucher_type == "قبض")
    total_payments = sum(v.amount for v in all_vouchers if v.voucher_type == "صرف")

    return render_template(
        "accounting/vouchers.html",
        vouchers=all_vouchers,
        cash_accounts=cash_accounts,
        postable_accounts=all_postable_accounts,
        total_receipts=total_receipts,
        total_payments=total_payments,
        q=q,
        type=v_type
    )

@accounting_bp.route("/accounts", methods=["GET"])
@login_required
def accounts():
    root_accounts = Account.query.filter_by(parent_id=None).order_by(Account.code.asc()).all()
    all_accounts = Account.query.order_by(Account.code.asc()).all()
    return render_template("accounting/accounts.html", root_accounts=root_accounts, all_accounts=all_accounts)

@accounting_bp.route("/accounts/create", methods=["POST"])
@login_required
def create_account():
    code = request.form.get("code")
    name = request.form.get("name")
    parent_id = request.form.get("parent_id")
    node_type = request.form.get("node_type", "فرعي")
    is_postable = bool(request.form.get("is_postable"))

    if Account.query.filter_by(code=code).first():
        flash("رقم الحساب موجود مسبقاً في الدليل.", "danger")
        return redirect(url_for("accounting.accounts"))

    p_id = int(parent_id) if parent_id and parent_id.isdigit() else None
    acc = Account(code=code, name=name, parent_id=p_id, node_type=node_type, is_postable=is_postable, balance=0.0)
    db.session.add(acc)
    db.session.commit()
    log_audit("accounting.create_account", target_type="account", target_id=acc.id, details=f"إضافة حساب {code} - {name}")
    flash(f"تم إضافة الحساب {name} بنجاح.", "success")
    return redirect(url_for("accounting.accounts"))

@accounting_bp.route("/journal", methods=["GET"])
@login_required
def journal():
    q = request.args.get("q", "").strip()
    query = JournalEntry.query
    if q:
        query = query.filter((JournalEntry.entry_number.contains(q)) | (JournalEntry.description.contains(q)))
    entries = query.order_by(JournalEntry.id.desc()).all()
    return render_template("accounting/journal.html", entries=entries, q=q)

@accounting_bp.route("/ledger", methods=["GET"])
@login_required
def ledger():
    account_id = request.args.get("account_id")
    postable_accounts = Account.query.filter_by(is_postable=True).order_by(Account.code.asc()).all()
    selected_account = None
    lines = []

    if account_id and account_id.isdigit():
        selected_account = Account.query.get(int(account_id))
        if selected_account:
            lines = JournalEntryLine.query.filter_by(account_id=selected_account.id).join(JournalEntry).order_by(JournalEntry.entry_date.asc(), JournalEntryLine.id.asc()).all()

    total_debit = sum(l.debit for l in lines)
    total_credit = sum(l.credit for l in lines)
    net_balance = total_debit - total_credit

    return render_template(
        "accounting/ledger.html",
        accounts=postable_accounts,
        selected_account=selected_account,
        lines=lines,
        total_debit=total_debit,
        total_credit=total_credit,
        net_balance=net_balance
    )
