import os
from datetime import date
from app import create_app, db
from app.models import User, Member, Plan, Shift, PaymentMethod, Subscription, Voucher, Account

app = create_app()
app.config["WTF_CSRF_ENABLED"] = False

client = app.test_client()

with app.app_context():
    # Login as admin
    with client.session_transaction() as sess:
        user = User.query.filter_by(username="admin").first()
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True

    # 1. Test GET /payments/methods
    res = client.get("/payments/methods")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "إدارة أنواع وطرق الدفع".encode("utf-8") in res.data
    assert "محفظة الكريمي".encode("utf-8") in res.data
    assert "محفظة جيب".encode("utf-8") in res.data
    print("✅ 1. GET /payments/methods passed.")

    # 2. Test POST /payments/methods
    res = client.post("/payments/methods", data={
        "name": "محفظة سبأفون كاش",
        "code": "SABACASH",
        "account_id": "",
        "notes": "محفظة إلكترونية تجريبية"
    }, follow_redirects=True)
    assert res.status_code == 200
    new_method = PaymentMethod.query.filter_by(code="SABACASH").first()
    assert new_method is not None
    print(f"✅ 2. POST /payments/methods passed: Created {new_method.name}.")

    # 3. Test Member Creation with Partial Payment and Shift
    kurimi = PaymentMethod.query.filter_by(code="KURIMI").first()
    plan_monthly = Plan.query.filter_by(name="شهري").first()
    shift_morning = Shift.query.filter(Shift.name.contains("صباح")).first()

    member_data = {
        "full_name": "سلطان كمال الأجسام",
        "phone": "771122334",
        "gender": "ذكر",
        "initial_plan_id": str(plan_monthly.id),
        "shift_id": str(shift_morning.id),
        "subscription_start_date": str(date.today()),
        "payment_method_id": str(kurimi.id),
        "paid_amount": "4000.0", # Monthly price is 6000, paid 4000, remaining 2000!
        "address": "صنعاء - حدة",
        "emergency_contact_name": "الأخ",
        "emergency_contact_phone": "770000000",
        "notes": "بطل كمال أجسام جديد"
    }

    res = client.post("/members/", data=member_data, follow_redirects=True)
    assert res.status_code == 200
    member = Member.query.filter_by(phone="771122334").first()
    assert member is not None
    print(f"✅ 3. Member created: {member.full_name} (ID: {member.id})")

    # Verify subscription details
    sub = member.active_subscription
    assert sub is not None, "Member has no active subscription!"
    assert sub.shift_id == shift_morning.id
    assert sub.total_amount == 6000.0, f"Expected total 6000, got {sub.total_amount}"
    assert sub.paid_amount == 4000.0, f"Expected paid 4000, got {sub.paid_amount}"
    assert sub.remaining_amount == 2000.0, f"Expected remaining 2000, got {sub.remaining_amount}"
    assert sub.payment_method_id == kurimi.id
    assert sub.payment_status == "مدفوع جزئياً"
    assert member.total_debt == 2000.0, f"Expected debt 2000, got {member.total_debt}"
    print(f"✅ 3b. Subscription payment & debt: Total {sub.total_amount}, Paid {sub.paid_amount}, Remaining {sub.remaining_amount}, Member Debt {member.total_debt}")

    # Verify receipt voucher
    voucher = Voucher.query.filter(Voucher.description.contains(member.full_name)).order_by(Voucher.id.desc()).first()
    assert voucher is not None, "Voucher not created!"
    assert voucher.amount == 4000.0
    print(f"✅ 3c. Receipt Voucher created: #{voucher.voucher_number}, Amount: {voucher.amount} YER")

    # 4. Test View Member Profile
    res = client.get(f"/members/{member.id}")
    assert res.status_code == 200
    assert "متبقي مالي بذمة المشترك".encode("utf-8") in res.data
    assert "2,000.00".encode("utf-8") in res.data
    assert "محفظة الكريمي".encode("utf-8") in res.data
    print("✅ 4. Member profile shows debt alert and subscription details correctly.")

    # 5. Test Pay Remaining Balance
    jeep = PaymentMethod.query.filter_by(code="JEEP").first()
    res = client.post(f"/subscriptions/{sub.id}/pay-remaining", data={
        "pay_amount": "2000.0",
        "payment_method_id": str(jeep.id)
    }, follow_redirects=True)
    assert res.status_code == 200

    db.session.refresh(sub)
    db.session.refresh(member)
    assert sub.remaining_amount == 0.0, f"Expected remaining 0, got {sub.remaining_amount}"
    assert sub.paid_amount == 6000.0
    assert sub.payment_status == "مدفوع بالكامل"
    assert member.total_debt == 0.0, f"Expected debt 0, got {member.total_debt}"
    print(f"✅ 5. Pay Remaining succeeded! Remaining: {sub.remaining_amount}, Debt: {member.total_debt}, Status: {sub.payment_status}")

    # Check second voucher
    second_voucher = Voucher.query.filter(Voucher.description.contains(member.full_name)).order_by(Voucher.id.desc()).first()
    assert second_voucher.id != voucher.id
    assert second_voucher.amount == 2000.0
    print(f"✅ 5b. Second Receipt Voucher created: #{second_voucher.voucher_number}, Amount: {second_voucher.amount} YER")

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
