import yaml
import os

ENV = os.environ.get("APP_ENV", "development")


def load_config():
    """Load configuration from core-config.yaml based on APP_ENV."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core-config.yaml")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    return config


def get_app_config():
    """Get app-level configuration."""
    config = load_config()
    return config["app"]


def get_db_config():
    """Get database configuration for current environment."""
    config = load_config()
    return config["environments"][ENV]["database"]


def get_flask_config():
    """Get Flask configuration for current environment."""
    config = load_config()
    return config["environments"][ENV]["flask"]


def get_oauth_config():
    """Get OAuth provider config; env vars override (e.g. GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)."""
    config = load_config()
    oauth = config.get("oauth", {})
    out = {}
    for provider in ("google", "microsoft", "apple"):
        p = oauth.get(provider, {})
        key_upper = provider.upper()
        out[provider] = {
            "client_id": os.environ.get(f"{key_upper}_CLIENT_ID", p.get("client_id", "")),
            "client_secret": os.environ.get(f"{key_upper}_CLIENT_SECRET", p.get("client_secret", "")),
            "team_id": os.environ.get(f"{key_upper}_TEAM_ID", p.get("team_id", "")),
            "key_id": os.environ.get(f"{key_upper}_KEY_ID", p.get("key_id", "")),
        }
    return out


def get_mail_config():
    """Get mail config for password reset; env vars can override."""
    config = load_config()
    mail = config.get("mail", {})
    return {
        "smtp_host": os.environ.get("SMTP_HOST", mail.get("smtp_host", "")),
        "smtp_port": int(os.environ.get("SMTP_PORT", mail.get("smtp_port", 587))),
        "smtp_user": os.environ.get("SMTP_USER", mail.get("smtp_user", "")),
        "smtp_password": os.environ.get("SMTP_PASSWORD", mail.get("smtp_password", "")),
        "from_addr": os.environ.get("MAIL_FROM", mail.get("from_addr", "noreply@grantroadmap.com")),
    }
