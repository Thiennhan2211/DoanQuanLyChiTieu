from flask import Flask, app, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_required
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'

def currency_vnd(value):
    try:
        value = float(value)
        return f"{value:,.0f} ₫".replace(",", ".")
    except (ValueError, TypeError):
        return "0 ₫"
    
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    from app.categories import bp as categories_bp
    app.register_blueprint(categories_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.groups import bp as groups_bp
    app.register_blueprint(groups_bp, url_prefix='/groups')

    from app.expenses import bp as expenses_bp
    app.register_blueprint(expenses_bp, url_prefix='/expenses')

    @app.route('/')
    def index():
        # Nếu đã đăng nhập → chuyển sang trang nhóm
        if current_user.is_authenticated:
            return redirect(url_for('groups.group_list'))
        # Nếu chưa → hiển thị trang chủ với nút đăng nhập / đăng ký
        return render_template('index.html')
    
    app.jinja_env.filters['currency_vnd'] = currency_vnd
    return app