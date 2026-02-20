from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from utils.config import get_flask_config
from utils.database import (
    init_db, create_user, get_user_by_id, get_user_by_username,
    update_user_profile, get_all_grants, apply_for_grant,
    update_grant_status, get_user_grants, add_favorite, remove_favorite,
    is_favorite, get_user_favorites
)

app = Flask(__name__)

# Load Flask configuration from core-config.yaml
flask_config = get_flask_config()
app.secret_key = flask_config.get("secret_key", "dev-secret-change-me-prod")

# Initialize DB on startup
init_db()

# Routes
@app.route("/")
def index():
    return redirect(url_for("home"))

@app.route("/home")
def home():
    # Count documents and videos in each resource folder
    resources_path = os.path.join(os.path.dirname(__file__), "static", "resources")
    
    resource_data = {}
    resource_folders = {
        "rd": {"name": "R&D Resources", "description": "Guide to prepare for an R&D grant application, including eligibility criteria, required documentation, and best practices."},
        "expert": {"name": "Expert Resources", "description": "Guide to writing an export grant to expand your business internationally."},
        "hiring": {"name": "Hiring Resources", "description": "Guide to leverage hiring grants and pay attention to key criteria to increase your chances of success."},
        "training": {"name": "Training Resources", "description": "Access to employee training grants, skill development programs and upskilling resources.", "coming_soon": True},
        "expansion": {"name": "Expansion Resources", "description": "Access to business expansion funding, capital investment programs and growth strategies.", "coming_soon": True}
    }
    
    for key, info in resource_folders.items():
        folder_path = os.path.join(resources_path, f"{key}-resources")
        documents = 0
        videos = 0
        
        if os.path.exists(folder_path):
            files = os.listdir(folder_path)
            documents = len([f for f in files if f.endswith('.pdf')])
            videos = len([f for f in files if f.endswith('.mp4')])
        
        resource_data[key] = {
            "name": info["name"],
            "description": info["description"],
            "documents": documents,
            "videos": videos,
            "coming_soon": info.get("coming_soon", False)
        }
    
    return render_template("home.html", resources=resource_data)

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
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    contact_type = request.form.get("contact_type", "contact")
    
    if not email or not message:
        flash("Email and message are required", "danger")
        return redirect(url_for("contact", type=contact_type))
    
    if len(message) > 1000:
        flash("Message cannot exceed 1000 characters", "danger")
        return redirect(url_for("contact", type=contact_type))
    
    # In a real application, you would save this to a database or send an email
    # For now, we'll just show a success message
    flash(f"Thank you! We received your message and will contact you at {email} soon.", "success")
    return redirect(url_for("home"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        company_name = request.form.get("company_name", "").strip()
        
        if not username or not email or not password:
            flash("All fields are required", "danger")
            return redirect(url_for("signup"))
        
        try:
            user_id = create_user(username, email, generate_password_hash(password), company_name)
            session["user_id"] = user_id
            session["username"] = username
            flash(f"Welcome, {username}!", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            if "Duplicate entry" in str(e) or "username" in str(e).lower() or "email" in str(e).lower():
                flash("Username or email already exists", "danger")
            else:
                flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("signup"))
    
    return render_template("signup.html")

@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if not username or not password:
            flash("Username and password required", "danger")
            return redirect(url_for("signin"))
        
        user = get_user_by_username(username)
        
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {username}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for("signin"))
    
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
