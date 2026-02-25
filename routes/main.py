"""Home, contact, resources, FAQ, and other public pages."""
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from bs4 import BeautifulSoup
import mammoth

main_bp = Blueprint("main", __name__)


# Remove the coming_soon flag when a resource is available for users
RESOURCE_FOLDERS = {
    "rd": {"name": "R&D Resources", "description": "Guide to prepare for an R&D grant application, including eligibility criteria, required documentation, and best practices."},
    "export": {"name": "Export Resources", "description": "Guide to writing an export grant to expand your business internationally."},
    "hiring": {"name": "Hiring Resources", "description": "Guide to leverage hiring grants and pay attention to key criteria to increase your chances of success."},
    "training": {"name": "Training Resources", "description": "Access to employee training grants, skill development programs and upskilling resources.", "coming_soon": True},
    "expansion": {"name": "Expansion Resources", "description": "Access to business expansion funding, capital investment programs and growth strategies.", "coming_soon": True}
}
DOC_EXTENSIONS = ('.pdf', '.docx')
VIDEO_EXTENSIONS = ('.mp4',)

FAQ_DOCX_PATH = "faq/FAQ.docx"
FAQ_HEADING_TAGS = ("h1", "h2", "h3")


def _get_resources_path():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "resources")


def _faq_html_to_items(faq_html):
    """Parse mammoth HTML into list of {question, answer}. Uses headings as questions."""
    soup = BeautifulSoup(faq_html, "html.parser")
    body = soup.find("body")
    if not body:
        body = soup
        if not soup.find(FAQ_HEADING_TAGS):
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


@main_bp.route("/")
def index():
    return redirect(url_for("main.home"))


@main_bp.route("/home")
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


@main_bp.route("/resources/<key>")
def resources_view(key):
    if key not in RESOURCE_FOLDERS:
        flash("Resource category not found", "danger")
        return redirect(url_for("main.home"))
    info = RESOURCE_FOLDERS[key]
    if info.get("coming_soon"):
        flash("This resource category is coming soon.", "info")
        return redirect(url_for("main.home"))
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


@main_bp.route("/resources/<key>/file/<path:filename>")
def resource_file(key, filename):
    if key not in RESOURCE_FOLDERS:
        return "Not found", 404
    folder_name = f"{key}-resources"
    folder_path = os.path.join(_get_resources_path(), folder_name)
    if not os.path.exists(folder_path):
        return "Not found", 404
    safe_path = os.path.normpath(os.path.join(folder_path, filename))
    if not safe_path.startswith(os.path.abspath(folder_path)):
        return "Not found", 404
    if not os.path.isfile(safe_path):
        return "Not found", 404
    force_download = request.args.get("download") or filename.lower().endswith(".docx")
    return send_from_directory(folder_path, filename, as_attachment=force_download, download_name=os.path.basename(filename))


@main_bp.route("/faq")
def faq():
    faq_path = os.path.join(_get_resources_path(), FAQ_DOCX_PATH)
    if not os.path.isfile(faq_path):
        flash("FAQ is not available at the moment.", "info")
        return redirect(url_for("main.home"))
    try:
        with open(faq_path, "rb") as f:
            result = mammoth.convert_to_html(f)
        faq_html = result.value
        faq_items = _faq_html_to_items(faq_html)
    except Exception:
        faq_items = [{"question": "Error", "answer": "<p class='text-danger'>Unable to load the FAQ document.</p>"}]
    return render_template("faq.html", faq_items=faq_items)


@main_bp.route("/plans")
def plans():
    return redirect(url_for("main.home") + "#plans")


@main_bp.route("/contact", methods=["GET"])
def contact():
    contact_type = request.args.get('type', 'contact')
    if contact_type == 'quote':
        page_title = "Request a Quote"
        page_subtitle = "Tell us about your grant funding needs and we'll provide you with a customized quote."
    else:
        page_title = "Contact Us"
        page_subtitle = "We'd love to hear from you. Send us a message and we'll respond as soon as possible."
    return render_template("contact.html", page_title=page_title, page_subtitle=page_subtitle, contact_type=contact_type)


@main_bp.route("/submit-contact", methods=["POST"])
def submit_contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    contact_type = request.form.get("contact_type", "contact")
    if not name or not email or not message:
        flash("Name, email and message are required", "danger")
        return redirect(url_for("main.contact", type=contact_type))
    if len(message) > 1000:
        flash("Message cannot exceed 1000 characters", "danger")
        return redirect(url_for("main.contact", type=contact_type))
    flash(f"Thank you, {name}! We received your request and will contact you at {email} soon.", "success")
    return redirect(url_for("main.home"))
