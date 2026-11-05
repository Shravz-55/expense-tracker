from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user

from config import Config

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.auth import bp as auth_bp
    from app.expenses import bp as expenses_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('expenses.dashboard'))
        return redirect(url_for('auth.login'))

    with app.app_context():
        from app.models import User, Expense  # noqa: F401
        db.create_all()

    return app
