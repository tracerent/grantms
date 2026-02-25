"""Route blueprints. Register in app with app.register_blueprint(...)."""
from routes.main import main_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.grants import grants_bp
from routes.account import account_bp

__all__ = ["main_bp", "auth_bp", "dashboard_bp", "grants_bp", "account_bp"]
