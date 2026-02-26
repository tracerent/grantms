"""Sign-in, sign-up, OAuth, forgot/reset password."""
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from utils.config import get_oauth_config, get_mail_config
from utils.database import Database
from utils.utils import Utils

auth_bp = Blueprint("auth", __name__, url_prefix="")
OAUTH_PROVIDERS = ("google", "microsoft", "apple")


def _get_oauth():
    """OAuth instance is attached to the app in app.py as app.oauth."""
    return getattr(current_app, "oauth", None)


def _send_password_reset_email(to_email, reset_link):
    """Send password reset email if SMTP is configured. Returns True if sent."""
    cfg = get_mail_config()
    if not cfg.get("smtp_host"):
        return False
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset your Grant Roadmap password"
        msg["From"] = cfg.get("from_addr", "noreply@grantroadmap.com")
        msg["To"] = to_email
        text = f"Use this link to reset your password: {reset_link}\n\nThis link expires in 1 hour."
        msg.attach(MIMEText(text, "plain"))
        with smtplib.SMTP(cfg["smtp_host"], cfg.get("smtp_port", 587)) as server:
            if cfg.get("smtp_user"):
                server.starttls()
                server.login(cfg["smtp_user"], cfg.get("smtp_password", ""))
            server.sendmail(msg["From"], [to_email], msg.as_string())
        return True
    except Exception:
        return False


@auth_bp.route("/auth/<provider>/login")
def oauth_login(provider):
    if provider not in OAUTH_PROVIDERS:
        flash("Unknown sign-in provider", "danger")
        return redirect(url_for("auth.signin"))
    oauth_cfg = get_oauth_config()
    if not oauth_cfg.get(provider, {}).get("client_id"):
        flash(f"Sign in with {provider.title()} is not configured yet.", "warning")
        return redirect(url_for("auth.signin"))
    oauth = _get_oauth()
    if not oauth:
        flash("Sign-in is not available.", "danger")
        return redirect(url_for("auth.signin"))
    session["oauth_company_name"] = request.args.get("company_name", "").strip()
    session["oauth_name"] = request.args.get("name", "").strip()
    session["oauth_next"] = request.args.get("next", "").strip()
    redirect_uri = url_for("auth.oauth_callback", provider=provider, _external=True)
    return getattr(oauth, provider).authorize_redirect(redirect_uri)


@auth_bp.route("/auth/<provider>/callback")
def oauth_callback(provider):
    if provider not in OAUTH_PROVIDERS:
        flash("Unknown sign-in provider", "danger")
        return redirect(url_for("auth.signin"))
    oauth = _get_oauth()
    if not oauth:
        flash("Sign-in was cancelled or failed.", "danger")
        return redirect(url_for("auth.signin"))
    try:
        token = getattr(oauth, provider).authorize_access_token()
    except Exception:
        flash("Sign-in was cancelled or failed.", "danger")
        return redirect(url_for("auth.signin"))
    company_name = session.pop("oauth_company_name", "") or ""
    oauth_name = session.pop("oauth_name", "") or ""
    next_url = session.pop("oauth_next", "") or ""

    userinfo = token.get("userinfo")
    if not userinfo and isinstance(token.get("id_token"), dict):
        userinfo = token["id_token"]
    if not userinfo:
        userinfo = {}
    email = (userinfo.get("email") or userinfo.get("preferred_username") or "").strip()
    name = oauth_name.strip() or (userinfo.get("name") or userinfo.get("given_name") or "").strip()
    provider_id = (userinfo.get("sub") or token.get("sub") or "").strip()
    if not email or not provider_id:
        flash("Could not get your email from the sign-in provider.", "danger")
        return redirect(url_for("auth.signin"))

    user = Database.get_user_by_oauth(provider, provider_id)
    if user:
        if user.get("is_active") == 0:
            flash("This account has been deactivated. Please contact your account administrator.", "danger")
            return redirect(url_for("auth.signin"))
        session["user_id"] = user["id"]
        session["username"] = user["email"]
        if next_url and next_url.startswith(request.host_url):
            flash(f"Welcome back, {Utils.get_user_display_name(user) or user['email'] or 'User'}!", "success")
    else:
        existing = Database.get_user_by_email(email)
        if existing:
            if existing.get("is_active") == 0:
                flash("This account has been deactivated. Please contact your account administrator.", "danger")
                return redirect(url_for("auth.signin"))
            Database.link_oauth_to_user(existing["id"], provider, provider_id)
            session["user_id"] = existing["id"]
            session["username"] = existing["email"]
            if next_url and next_url.startswith(request.host_url):
                flash(f"Welcome back! Your account is now linked to {provider.title()}.", "success")
        else:
            try:
                user_id = Database.create_oauth_user(email, name, provider, provider_id)
                Database.create_company_for_user(user_id, company_name=company_name)  # company name stored in company table only
                user = Database.get_user_by_id(user_id)
                session["user_id"] = user_id
                session["username"] = user["email"]
                if next_url and next_url.startswith(request.host_url):
                    flash(f"Welcome, {Utils.get_user_display_name(user) or name or email or 'User'}!", "success")
            except Exception as e:
                if "Duplicate entry" in str(e) or "email" in str(e).lower():
                    flash("An account with this email already exists. Sign in with email and password.", "danger")
                else:
                    flash(f"Error: {str(e)}", "danger")
                return redirect(url_for("auth.signin"))

    if next_url and next_url.startswith(request.host_url):
        return redirect(next_url)
    return redirect(url_for("dashboard.dashboard"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html", error=None)
    email = request.form.get("email", "").strip()
    if not email:
        return render_template("forgot_password.html", error="Please enter your email address.")
    user = Database.get_user_by_email(email)
    if not user:
        return render_template("forgot_password.html", error="Email address not registered with us. Please create an account.", email=email)
    if not user.get("password"):
        return render_template("forgot_password.html", error="This account uses sign-in with Google/Microsoft/Apple. Use that to sign in.", email=email)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    Database.create_reset_token(user["id"], token, expires_at)
    reset_link = request.url_root.rstrip("/") + url_for("auth.reset_password", token=token)
    sent = _send_password_reset_email(email, reset_link)
    return render_template("forgot_password_done.html", sent=sent, reset_link=reset_link, email=email)


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    token = request.args.get("token") or request.form.get("token", "")
    if not token:
        flash("Invalid or missing reset link.", "danger")
        return redirect(url_for("auth.forgot_password"))
    if request.method == "GET":
        user_id = Database.get_reset_token_user_id(token)
        if not user_id:
            flash("This reset link has expired or is invalid.", "danger")
            return redirect(url_for("auth.forgot_password"))
        return render_template("reset_password.html", token=token)
    new_password = request.form.get("password", "").strip()
    confirm = request.form.get("confirm_password", "").strip()
    if not new_password or not confirm:
        flash("Please fill in both password fields.", "danger")
        return render_template("reset_password.html", token=token)
    if new_password != confirm:
        flash("Passwords do not match.", "danger")
        return render_template("reset_password.html", token=token)
    if len(new_password) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return render_template("reset_password.html", token=token)
    user_id = Database.get_reset_token_user_id(token)
    if not user_id:
        flash("This reset link has expired or is invalid.", "danger")
        return redirect(url_for("auth.forgot_password"))
    Database.update_user_password(user_id, generate_password_hash(new_password))
    Database.delete_reset_token(token)
    flash("Your password has been reset. You can sign in now.", "success")
    return redirect(url_for("auth.signin"))


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        company_name = request.form.get("company_name", "").strip()
        password = request.form.get("password", "").strip()

        if not first_name or not email or not password:
            flash("First name, email and password are required", "danger")
            return redirect(url_for("auth.signup"))
        if not company_name:
            flash("Company name is required", "danger")
            return redirect(url_for("auth.signup"))
        if len(password) < 6:
            flash("Password must be at least 6 characters", "danger")
            return redirect(url_for("auth.signup"))

        try:
            user_id = Database.create_user(first_name, last_name, email, generate_password_hash(password))
            Database.create_company_for_user(user_id, company_name=company_name)  # company name stored in company table only
            user = Database.get_user_by_id(user_id)
            session["user_id"] = user_id
            session["username"] = user["email"]
            return redirect(url_for("dashboard.dashboard"))
        except Exception as e:
            if "Duplicate entry" in str(e) or "email" in str(e).lower():
                flash("An account with this email already exists", "danger")
            else:
                flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("auth.signup"))

    return render_template("signup.html")


@auth_bp.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "GET" and session.get("user_id"):
        # Already logged in: do not show signin page (avoids Dashboard tab flashing on signin then disappearing)
        next_url = request.args.get("next", "").strip()
        if next_url and next_url.startswith(request.host_url):
            return redirect(next_url)
        return redirect(url_for("dashboard.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required", "danger")
            return redirect(url_for("auth.signin"))

        user = Database.get_user_by_email(email)
        if not user or not user.get("password"):
            flash("Invalid email or password", "danger")
            return redirect(url_for("auth.signin"))
        if not check_password_hash(user["password"], password):
            flash("Invalid email or password", "danger")
            return redirect(url_for("auth.signin"))
        if user.get("is_active") == 0:
            flash("This account has been deactivated. Please contact your account administrator.", "danger")
            return redirect(url_for("auth.signin"))
        session["user_id"] = user["id"]
        session["username"] = user["email"]
        next_url = request.form.get("next") or request.args.get("next")
        if next_url and next_url.startswith(request.host_url):
            flash(f"Welcome back, {Utils.get_user_display_name(user) or user['email'] or 'User'}!", "success")
        if next_url and next_url.startswith(request.host_url):
            return redirect(next_url)
        return redirect(url_for("dashboard.dashboard"))

    return render_template("signin.html")


@auth_bp.route("/signout")
def signout():
    session.clear()
    flash("Signed out successfully", "info")
    return redirect(url_for("main.home"))
