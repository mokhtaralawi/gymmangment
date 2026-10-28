import os
from flask import Flask, request
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from app.models import db, User, Account, Plan, NotificationRule, Shift, PaymentMethod
from sqlalchemy import inspect, text

login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "يرجى تسجيل الدخول للوصول إلى هذه الصفحة."
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.members import members_bp
    from app.routes.subscriptions import subscriptions_bp
    from app.routes.attendance import attendance_bp
    from app.routes.employees import employees_bp
    from app.routes.accounting import accounting_bp
    from app.routes.notifications import notifications_bp
    from app.routes.system import system_bp
    from app.routes.shifts import shifts_bp
    from app.routes.payment_methods import payments_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(members_bp, url_prefix="/members")
    app.register_blueprint(subscriptions_bp, url_prefix="/subscriptions")
    app.register_blueprint(shifts_bp, url_prefix="/shifts")
    app.register_blueprint(payments_bp, url_prefix="/payments")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(attendance_bp, url_prefix="/member-attendance")
    app.register_blueprint(employees_bp, url_prefix="/employees")
    app.register_blueprint(accounting_bp, url_prefix="/accounting")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")
    app.register_blueprint(system_bp, url_prefix="/system")

    @app.route("/")
    def index():
        from flask import redirect, url_for
        return redirect(url_for("dashboard.index"))

    @app.route("/offline")
    def offline():
        from flask import render_template
        return render_template("offline.html")

    @app.route("/sw.js")
    def service_worker():
        from flask import make_response, send_from_directory
        response = make_response(send_from_directory(app.static_folder, "sw.js"))
        response.headers["Content-Type"] = "application/javascript"
        response.headers["Service-Worker-Allowed"] = "/"
        return response

    with app.app_context():
        db.create_all()
        seed_initial_data()

    return app

def seed_initial_data():
    # 1. Admin users
    if not User.query.filter_by(username="771597106").first():
        u1 = User(username="771597106", full_name="مختار علوي", role_name="مدير النظام", is_active=True)
        u1.set_password("771597106mokhtar")
        db.session.add(u1)
    
    if not User.query.filter_by(username="admin").first():
        u2 = User(username="admin", full_name="مدير النظام", role_name="مدير النظام", is_active=True)
        u2.set_password("admin123")
        db.session.add(u2)

    # 2. Plans
    if not Plan.query.first():
        plans_data = [
            ("PLN-653158378C", "يومي", 1, 500.0, "اشتراك دخول يوم واحد"),
            ("PLN-D24CC244E2", "اسبوعي", 7, 1500.0, "اشتراك لمدة أسبوع كامل"),
            ("PLN-D05DFA0694", "شهري", 30, 6000.0, "اشتراك شهري شامل استخدام جميع المرافق والأجهزة الرياضية"),
        ]
        for code, name, days, price, desc in plans_data:
            db.session.add(Plan(plan_code=code, name=name, duration_days=days, price=price, description=desc, is_active=True))

    # Migration check for subscriptions columns
    try:
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('subscriptions')]
        with db.engine.connect() as conn:
            if 'shift_id' not in columns:
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN shift_id INTEGER REFERENCES shifts(id)"))
            if 'total_amount' not in columns:
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN total_amount FLOAT DEFAULT 0.0"))
            if 'paid_amount' not in columns:
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN paid_amount FLOAT DEFAULT 0.0"))
            if 'remaining_amount' not in columns:
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN remaining_amount FLOAT DEFAULT 0.0"))
            if 'payment_method_id' not in columns:
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN payment_method_id INTEGER REFERENCES payment_methods(id)"))
            if 'payment_status' not in columns:
                conn.execute(text("ALTER TABLE subscriptions ADD COLUMN payment_status VARCHAR(30) DEFAULT 'مدفوع بالكامل'"))
            conn.commit()
    except Exception as e:
        print(f"Migration check notice: {e}")

    # 3. Shifts (فترات التمرين)
    if not Shift.query.first():
        shifts_data = [
            ("الفترة الصباحية", "06:00", "11:00", "كابتن الفترة الصباحية", "تمارين الصباح وحرق الدهون واللياقة البدنية"),
            ("فترة بعد العصر", "16:00", "19:30", "كابتن فترة العصر", "تمارين الحديد والأوزان الحرة وبناء العضلات"),
            ("فترة المساء", "20:00", "23:30", "كابتن الفترة المسائية", "تمارين كمال الأجسام المكثفة والأبطال"),
        ]
        for name, s_time, e_time, sup, notes in shifts_data:
            db.session.add(Shift(name=name, start_time=s_time, end_time=e_time, supervisor_name=sup, notes=notes, is_active=True))

    # 4. Notification Rules
    if not NotificationRule.query.first():
        db.session.add(NotificationRule(days_before=7, days_after=30, is_enabled=True))

    # 4. Chart of Accounts
    if not Account.query.first():
        accounts_data = [
            # Level 1
            ("1", "الأصول", None, "رئيسي", False),
            ("2", "الخصوم والالتزامات", None, "رئيسي", False),
            ("3", "حقوق الملكية", None, "رئيسي", False),
            ("4", "الإيرادات", None, "رئيسي", False),
            ("5", "المصروفات", None, "رئيسي", False),
            # Level 2 & 3
            ("11", "الأصول المتداولة", "1", "تجميعي", False),
            ("1101", "الصندوق الرئيسي (الخزينة)", "11", "صندوق", True),
            ("1102", "حساب البنك (الحساب الجاري)", "11", "بنك", True),
            ("1103", "مدينو الاشتراكات والخدمات", "11", "أصل", True),
            ("1104", "سلف وعهـد الموظفين", "11", "أصل", True),
            ("12", "الأصول الثابتة", "1", "تجميعي", False),
            ("1201", "الأجهزة والمعدات الرياضية", "12", "أصل", True),
            ("1202", "الأثاث والتجهيزات المكتبية", "12", "أصل", True),
            
            ("21", "الالتزامات المتداولة", "2", "تجميعي", False),
            ("2101", "مستحقات الموظفين والرواتب", "21", "خصم", True),
            ("2102", "أمانات وتأمينات المشتركين", "21", "خصم", True),
            ("2103", "الموردون والدائنون", "21", "خصم", True),
            
            ("31", "رأس المال", "3", "تجميعي", False),
            ("3101", "رأس مال النادي", "31", "ملكية", True),
            ("32", "الأرباح والخسائر", "3", "تجميعي", False),
            ("3201", "الأرباح المبقاة والمرحلة", "32", "ملكية", True),
            
            ("41", "إيرادات النشاط الرياضي", "4", "تجميعي", False),
            ("4101", "إيرادات اشتراكات النادي", "41", "إيراد", True),
            ("4102", "إيرادات التدريب الشخصي (PT)", "41", "إيراد", True),
            ("4103", "إيرادات المشروبات والمبيعات الرياضية", "41", "إيراد", True),
            ("4104", "إيرادات التجديد ورسوم التسجيل", "41", "إيراد", True),
            ("4105", "إيرادات وأنشطة أخرى", "41", "إيراد", True),
            
            ("51", "المصروفات التشغيلية والعمومية", "5", "تجميعي", False),
            ("5101", "رواتب وأجور الموظفين والمدربين", "51", "مصروف", True),
            ("5102", "مكافآت وبدلات إضافية", "51", "مصروف", True),
            ("5103", "إيجار مقر وصالة النادي", "51", "مصروف", True),
            ("5104", "فواتير كهرباء ومياه وإنترنت", "51", "مصروف", True),
            ("5105", "صيانة المعدات والأجهزة الرياضية", "51", "مصروف", True),
            ("5106", "أدوات نظافة ومستلزمات تشغيلية", "51", "مصروف", True),
            ("5107", "دعاية وإعلان وتسويق", "51", "مصروف", True),
            ("5108", "مصروفات بنكية ورسوم", "51", "مصروف", True),
            ("5109", "مصروفات نثرية ومتنوعة", "51", "مصروف", True),
        ]
        
        acc_map = {}
        for code, name, parent_code, node_type, is_postable in accounts_data:
            parent_id = acc_map.get(parent_code) if parent_code else None
            acc = Account(code=code, name=name, parent_id=parent_id, node_type=node_type, is_postable=is_postable, balance=0.0)
            db.session.add(acc)
            db.session.flush()
            acc_map[code] = acc.id

    # 5. Payment Methods (أنواع وطرق الدفع)
    if not PaymentMethod.query.first():
        cash_acc = Account.query.filter_by(code="1101").first()
        bank_acc = Account.query.filter_by(code="1102").first()
        cash_id = cash_acc.id if cash_acc else None
        bank_id = bank_acc.id if bank_acc else None

        default_methods = [
            ("كاش (نقداً)", "CASH", cash_id, "الدفع النقدي المباشر في خزينة النادي"),
            ("محفظة جيب (Jeep)", "JEEP", cash_id, "الدفع عبر محفظة جيب الإلكترونية"),
            ("محفظة الكريمي (Kurimi Pay)", "KURIMI", bank_id, "الدفع عبر حساب أو محفظة الكريمي مالي جوال"),
            ("حوالة / تحويل بنكي", "BANK", bank_id, "إيداع أو تحويل بنكي مباشر"),
            ("محفظة ون كاش (OneCash)", "ONECASH", cash_id, "الدفع عبر خدمة ون كاش"),
            ("محفظة جوالي", "JAWALI", cash_id, "الدفع عبر محفظة جوالي الإلكترونية")
        ]
        for name, code, acc_id, notes in default_methods:
            db.session.add(PaymentMethod(
                name=name,
                code=code,
                account_id=acc_id,
                is_active=True,
                notes=notes
            ))

    db.session.commit()
