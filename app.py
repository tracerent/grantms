from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets
from datetime import datetime, timedelta
from utils.config import get_flask_config, get_oauth_config, get_mail_config
from utils.database import (
    init_db, create_user, get_user_by_id, get_user_by_username, get_user_by_email,
    get_user_by_oauth, create_oauth_user, link_oauth_to_user,
    update_user_profile, create_contact_submission,
    create_reset_token, get_reset_token_user_id, delete_reset_token, update_user_password,
    get_all_grants, apply_for_grant,
    update_grant_status, get_user_grants, add_favorite, remove_favorite,
    is_favorite, get_user_favorites
)
from authlib.integrations.flask_client import OAuth
import mammoth
from bs4 import BeautifulSoup

app = Flask(__name__)

# Resource categories (key -> name, description, coming_soon)
RESOURCE_FOLDERS = {
    "rd": {"name": "R&D Resources", "description": "Guide to prepare for an R&D grant application, including eligibility criteria, required documentation, and best practices."},
    "export": {"name": "Export Resources", "description": "Guide to writing an export grant to expand your business internationally."},
    "hiring": {"name": "Hiring Resources", "description": "Guide to leverage hiring grants and pay attention to key criteria to increase your chances of success."},
    "training": {"name": "Training Resources", "description": "Access to employee training grants, skill development programs and upskilling resources.", "coming_soon": True},
    "expansion": {"name": "Expansion Resources", "description": "Access to business expansion funding, capital investment programs and growth strategies.", "coming_soon": True}
}
DOC_EXTENSIONS = ('.pdf', '.docx')
VIDEO_EXTENSIONS = ('.mp4',)

# Load Flask configuration from core-config.yaml
flask_config = get_flask_config()
app.secret_key = flask_config.get("secret_key", "dev-secret-change-me-prod")

# Initialize DB on startup
init_db()


@app.context_processor
def inject_current_user():
    """Make current_user (email, name, company_name, username) available in all templates when logged in."""
    if session.get("user_id"):
        user = get_user_by_id(session["user_id"])
        if user:
            return {"current_user": user}
    return {"current_user": None}


# OAuth (Google, Microsoft, Apple)
oauth = OAuth(app)
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
# Apple requires extra setup (JWT client secret); button still shown, redirect will fail until configured
if _oauth_cfg.get("apple", {}).get("client_id"):
    oauth.register(
        name="apple",
        client_id=_oauth_cfg["apple"]["client_id"],
        client_secret=_oauth_cfg["apple"]["client_secret"],
        server_metadata_url="https://appleid.apple.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email name"},
    )

# Routes
@app.route("/")
def index():
    return redirect(url_for("home"))

def _get_resources_path():
    return os.path.join(os.path.dirname(__file__), "static", "resources")

@app.route("/home")
def home():
    resources_path = _get_resources_path()
    resource_data = {}
    for key, info in RESOURCE_FOLDERS.items():
        folder_path = os.path.join(resources_path, f"{key}-resources")
        documents = 0
        videos = 0
        if os.path.exists(folder_path):
            files = os.listdir(folder_path)
            documents = len([f for f in files if f.lower().endswith(DOC_EXTENSIONS)])
            videos = len([f for f in files if f.lower().endswith(VIDEO_EXTENSIONS)])
        resource_data[key] = {
            "name": info["name"],
            "description": info["description"],
            "documents": documents,
            "videos": videos,
            "coming_soon": info.get("coming_soon", False)
        }
    return render_template("home.html", resources=resource_data)

@app.route("/resources/<key>")
def resources_view(key):
    if key not in RESOURCE_FOLDERS:
        flash("Resource category not found", "danger")
        return redirect(url_for("home"))
    info = RESOURCE_FOLDERS[key]
    if info.get("coming_soon"):
        flash("This resource category is coming soon.", "info")
        return redirect(url_for("home"))
    folder_path = os.path.join(_get_resources_path(), f"{key}-resources")
    documents = []
    videos = []
    if os.path.exists(folder_path):
        for f in sorted(os.listdir(folder_path)):
            low = f.lower()
            if low.endswith(DOC_EXTENSIONS):
                documents.append({"filename": f, "ext": os.path.splitext(f)[1].lower()})
            elif low.endswith(VIDEO_EXTENSIONS):
                videos.append(f)
    return render_template(
        "resources_view.html",
        key=key,
        name=info["name"],
        description=info["description"],
        documents=documents,
        videos=videos,
    )

@app.route("/resources/<key>/file/<path:filename>")
def resource_file(key, filename):
    if key not in RESOURCE_FOLDERS:
        return "Not found", 404
    folder_name = f"{key}-resources"
    folder_path = os.path.join(_get_resources_path(), folder_name)
    if not os.path.exists(folder_path):
        return "Not found", 404
    # Security: ensure filename doesn't escape the folder (no .. or absolute path)
    safe_path = os.path.normpath(os.path.join(folder_path, filename))
    if not safe_path.startswith(os.path.abspath(folder_path)):
        return "Not found", 404
    if not os.path.isfile(safe_path):
        return "Not found", 404
    force_download = request.args.get("download") or filename.lower().endswith(".docx")
    return send_from_directory(folder_path, filename, as_attachment=force_download, download_name=os.path.basename(filename))


# FAQ: display a DOCX as Q/A accordion (open to all)
FAQ_DOCX_PATH = "faq/FAQ.docx"
FAQ_HEADING_TAGS = ("h1", "h2", "h3")

def _faq_html_to_items(faq_html):
    """Parse mammoth HTML into list of {question, answer}. Uses headings as questions."""
    soup = BeautifulSoup(faq_html, "html.parser")
    body = soup.find("body")
    if not body:
        # Fragment without body: use soup's first element or whole thing
        body = soup
        if soup.find(FAQ_HEADING_TAGS):
            pass  # headings at top level
        else:
            return [{"question": "FAQ", "answer": faq_html}]
    items = []
    current_heading = None
    current_answer_nodes = []
    for el in body.children:
        if hasattr(el, "name") and el.name in FAQ_HEADING_TAGS:
            if current_heading is not None:
                answer_html = "".join(str(n) for n in current_answer_nodes).strip()
                items.append({"question": current_heading.get_text(strip=True), "answer": answer_html or ""})
            current_heading = el
            current_answer_nodes = []
        else:
            if current_heading is not None:
                current_answer_nodes.append(el)
    if current_heading is not None:
        answer_html = "".join(str(n) for n in current_answer_nodes).strip()
        items.append({"question": current_heading.get_text(strip=True), "answer": answer_html or ""})
    if not items:
        return [{"question": "FAQ", "answer": faq_html}]
    return items

@app.route("/faq")
def faq():
    faq_path = os.path.join(_get_resources_path(), FAQ_DOCX_PATH)
    if not os.path.isfile(faq_path):
        flash("FAQ is not available at the moment.", "info")
        return redirect(url_for("home"))
    try:
        with open(faq_path, "rb") as f:
            result = mammoth.convert_to_html(f)
        faq_html = result.value
        faq_items = _faq_html_to_items(faq_html)
    except Exception as e:
        faq_items = [{"question": "Error", "answer": "<p class='text-danger'>Unable to load the FAQ document.</p>"}]
    return render_template("faq.html", faq_items=faq_items)


# ----- OAuth sign-in (Google, Microsoft, Apple) -----
OAUTH_PROVIDERS = ("google", "microsoft", "apple")


@app.route("/auth/<provider>/login")
def oauth_login(provider):
    if provider not in OAUTH_PROVIDERS:
        flash("Unknown sign-in provider", "danger")
        return redirect(url_for("signin"))
    if not _oauth_cfg.get(provider, {}).get("client_id"):
        flash(f"Sign in with {provider.title()} is not configured yet.", "warning")
        return redirect(url_for("signin"))
    session["oauth_company_name"] = request.args.get("company_name", "").strip()
    session["oauth_name"] = request.args.get("name", "").strip()
    session["oauth_next"] = request.args.get("next", "").strip()
    redirect_uri = url_for("oauth_callback", provider=provider, _external=True)
    return getattr(oauth, provider).authorize_redirect(redirect_uri)


@app.route("/auth/<provider>/callback")
def oauth_callback(provider):
    if provider not in OAUTH_PROVIDERS:
        flash("Unknown sign-in provider", "danger")
        return redirect(url_for("signin"))
    try:
        token = getattr(oauth, provider).authorize_access_token()
    except Exception as e:
        flash("Sign-in was cancelled or failed.", "danger")
        return redirect(url_for("signin"))
    company_name = session.pop("oauth_company_name", "") or ""
    oauth_name = session.pop("oauth_name", "") or ""
    next_url = session.pop("oauth_next", "") or ""

    # Get user info (OpenID Connect userinfo or token sub/email)
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
        return redirect(url_for("signin"))

    user = get_user_by_oauth(provider, provider_id)
    if user:
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash(f"Welcome back, {user.get('name') or user['username']}!", "success")
    else:
        existing = get_user_by_email(email)
        if existing:
            link_oauth_to_user(existing["id"], provider, provider_id)
            session["user_id"] = existing["id"]
            session["username"] = existing["username"]
            flash(f"Welcome back! Your account is now linked to {provider.title()}.", "success")
        else:
            try:
                user_id = create_oauth_user(email, name, company_name, provider, provider_id)
                user = get_user_by_id(user_id)
                session["user_id"] = user_id
                session["username"] = user["username"]
                flash(f"Welcome, {name or email}!", "success")
            except Exception as e:
                if "Duplicate entry" in str(e) or "email" in str(e).lower():
                    flash("An account with this email already exists. Sign in with email and password.", "danger")
                else:
                    flash(f"Error: {str(e)}", "danger")
                return redirect(url_for("signin"))

    if next_url and next_url.startswith(request.host_url):
        return redirect(next_url)
    return redirect(url_for("dashboard"))


@app.route("/plans")
def plans():
    return render_template("plans.html")

@app.route("/contact", methods=["GET"])
def contact():
    contact_type = request.args.get('type', 'contact')
    
    if contact_type == 'quote':
        page_title = "Request a Quote"
        page_subtitle = "Tell us about your grant funding needs and we'll provide you with a customized quote"
    else:
        page_title = "Contact Us"
        page_subtitle = "We'd love to hear from you. Send us a message and we'll respond as soon as possible"
    
    return render_template("contact.html", page_title=page_title, page_subtitle=page_subtitle, contact_type=contact_type)

@app.route("/submit-contact", methods=["POST"])
def submit_contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    contact_type = request.form.get("contact_type", "contact")
    
    if not name or not email or not message:
        flash("Name, email and message are required", "danger")
        return redirect(url_for("contact", type=contact_type))
    
    if len(message) > 1000:
        flash("Message cannot exceed 1000 characters", "danger")
        return redirect(url_for("contact", type=contact_type))
    
    try:
        create_contact_submission(name, email, message, contact_type)
        flash(f"Thank you, {name}! We received your request and will contact you at {email} soon.", "success")
    except Exception as e:
        flash("We couldn't save your request. Please try again or email us directly.", "danger")
        return redirect(url_for("contact", type=contact_type))
    return redirect(url_for("home"))


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


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html", error=None)
    email = request.form.get("email", "").strip()
    if not email:
        return render_template("forgot_password.html", error="Please enter your email address.")
    user = get_user_by_email(email)
    if not user:
        return render_template("forgot_password.html", error="Email address not registered with us. Please create an account.", email=email)
    if not user.get("password"):
        return render_template("forgot_password.html", error="This account uses sign-in with Google/Microsoft/Apple. Use that to sign in.", email=email)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    create_reset_token(user["id"], token, expires_at)
    reset_link = request.url_root.rstrip("/") + url_for("reset_password", token=token)
    sent = _send_password_reset_email(email, reset_link)
    return render_template("forgot_password_done.html", sent=sent, reset_link=reset_link, email=email)


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    token = request.args.get("token") or request.form.get("token", "")
    if not token:
        flash("Invalid or missing reset link.", "danger")
        return redirect(url_for("forgot_password"))
    if request.method == "GET":
        user_id = get_reset_token_user_id(token)
        if not user_id:
            flash("This reset link has expired or is invalid.", "danger")
            return redirect(url_for("forgot_password"))
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
    user_id = get_reset_token_user_id(token)
    if not user_id:
        flash("This reset link has expired or is invalid.", "danger")
        return redirect(url_for("forgot_password"))
    update_user_password(user_id, generate_password_hash(new_password))
    delete_reset_token(token)
    flash("Your password has been reset. You can sign in now.", "success")
    return redirect(url_for("signin"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        company_name = request.form.get("company_name", "").strip()
        password = request.form.get("password", "").strip()
        
        if not name or not email or not company_name or not password:
            flash("Name, email, company name and password are required", "danger")
            return redirect(url_for("signup"))
        if len(password) < 6:
            flash("Password must be at least 6 characters", "danger")
            return redirect(url_for("signup"))
        
        try:
            user_id = create_user(name, email, generate_password_hash(password), company_name)
            user = get_user_by_id(user_id)
            session["user_id"] = user_id
            session["username"] = user["username"]
            flash(f"Welcome, {name or user['username']}!", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            if "Duplicate entry" in str(e) or "username" in str(e).lower() or "email" in str(e).lower():
                flash("An account with this email already exists", "danger")
            else:
                flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("signup"))
    
    return render_template("signup.html")

@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        
        if not email or not password:
            flash("Email and password are required", "danger")
            return redirect(url_for("signin"))
        
        user = get_user_by_email(email)
        if not user or not user.get("password"):
            flash("Invalid email or password", "danger")
            return redirect(url_for("signin"))
        if not check_password_hash(user["password"], password):
            flash("Invalid email or password", "danger")
            return redirect(url_for("signin"))
        
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash(f"Welcome back, {user.get('name') or user['username']}!", "success")
        next_url = request.form.get("next") or request.args.get("next")
        if next_url and next_url.startswith(request.host_url):
            return redirect(next_url)
        return redirect(url_for("dashboard"))
    
    return render_template("signin.html")

@app.route("/signout")
def signout():
    session.clear()
    flash("Signed out successfully", "info")
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please sign in first", "warning")
        return redirect(url_for("signin"))
    
    user_id = session["user_id"]
    user = get_user_by_id(user_id)
    user_grants = get_user_grants(user_id)
    favorites = get_user_favorites(user_id)
    all_grants = get_all_grants()
    
    return render_template("dashboard.html", user=user, user_grants=user_grants, 
                         favorites=favorites, all_grants=all_grants)

@app.route("/apply-grant", methods=["POST"])
def apply_grant():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    grant_id = data.get("grant_id")
    user_id = session["user_id"]
    
    try:
        apply_for_grant(user_id, grant_id)
        return jsonify({"success": True, "message": "Grant application started"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/update-grant-status", methods=["POST"])
def update_grant_status_route():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    grant_id = data.get("grant_id")
    status = data.get("status")
    user_id = session["user_id"]
    
    try:
        update_grant_status(user_id, grant_id, status)
        return jsonify({"success": True, "message": "Status updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/toggle-favorite", methods=["POST"])
def toggle_favorite():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    grant_id = data.get("grant_id")
    user_id = session["user_id"]
    
    try:
        if is_favorite(user_id, grant_id):
            remove_favorite(user_id, grant_id)
            message = "Removed from favorites"
        else:
            add_favorite(user_id, grant_id)
            message = "Added to favorites"
        
        return jsonify({"success": True, "message": message}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/update-profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    user_id = session["user_id"]
    company_description = request.form.get("company_description", "")
    
    try:
        update_user_profile(user_id, company_description)
        flash("Profile updated", "success")
        return redirect(url_for("dashboard"))
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
