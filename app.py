from flask import Flask, render_template, session
from utils.config import get_flask_config, get_oauth_config
from utils.database import Database
from utils.utils import Utils
from authlib.integrations.flask_client import OAuth

from routes import main_bp, auth_bp, dashboard_bp, grants_bp, account_bp

app = Flask(__name__)

flask_config = get_flask_config()
app.secret_key = flask_config.get("secret_key", "grantms-#24n-25y-roadmap-dev")

Database.init_db()


@app.context_processor
def inject_current_user():
    """Make current_user (email, first_name, last_name, display_name, etc.) available in all templates when logged in."""
    if session.get("user_id"):
        user = Database.get_user_by_id(session["user_id"])
        if user:
            u = dict(user)
            u["display_name"] = Utils.get_user_display_name(user)
            return {"current_user": u}
    return {"current_user": None}


oauth = OAuth(app)
app.oauth = oauth
_oauth_cfg = get_oauth_config()

if _oauth_cfg.get("google", {}).get("client_id"):
    oauth.register(
        name="google",
        client_id=_oauth_cfg["google"]["client_id"],
        client_secret=_oauth_cfg["google"]["client_secret"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
if _oauth_cfg.get("microsoft", {}).get("client_id"):
    oauth.register(
        name="microsoft",
        client_id=_oauth_cfg["microsoft"]["client_id"],
        client_secret=_oauth_cfg["microsoft"]["client_secret"],
        server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
if _oauth_cfg.get("apple", {}).get("client_id"):
    oauth.register(
        name="apple",
        client_id=_oauth_cfg["apple"]["client_id"],
        client_secret=_oauth_cfg["apple"]["client_secret"],
        server_metadata_url="https://appleid.apple.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email name"},
    )


@app.errorhandler(404)
def not_found(_e):
    """Display 404 page for undefined URLs."""
    return render_template("404.html"), 404


app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(grants_bp)
app.register_blueprint(account_bp)


if __name__ == "__main__":
    app.run(debug=True)
