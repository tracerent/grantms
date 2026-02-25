"""Shared decorators for route handlers."""
from functools import wraps
from flask import session, request, redirect, url_for, flash


def login_required(f):
    """Redirect to signin if user is not logged in. Use for dashboard and other page routes."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in first", "warning")
            next_url = request.url if request.url else url_for("dashboard.dashboard")
            return redirect(url_for("auth.signin", next=next_url))
        return f(*args, **kwargs)
    return wrapped
