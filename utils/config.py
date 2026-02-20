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
