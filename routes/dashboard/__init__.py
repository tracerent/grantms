"""Dashboard blueprint: main page, Home/Saved Grants/Contacts/Application/Add Grant APIs."""
from flask import Blueprint

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="")

# Import route modules so they register on dashboard_bp (order does not matter for registration)
from . import home
from . import contacts
from . import grants
from . import request_grant
from . import grant_detail

__all__ = ["dashboard_bp"]
