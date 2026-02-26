"""Contacts list, category counts, create, update, delete APIs."""
from flask import request, session, jsonify

from utils.decorators import login_required
from utils.database import Database

from . import dashboard_bp


@dashboard_bp.route("/api/dashboard/contacts")
@login_required
def api_contacts_list():
    """Return contacts for the current user's company. Query: category (optional), search (optional)."""
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=True)
    if not company_id:
        return jsonify({"error": "Could not load contacts"}), 400
    category = request.args.get("category") or None
    if category == "":
        category = None
    search = request.args.get("search") or None
    contacts = Database.get_contacts(company_id, category=category, search=search)
    out = []
    for c in contacts:
        out.append({
            "id": c["id"],
            "category": c.get("category") or "",
            "organization": c.get("organization") or "",
            "contact_name": c.get("contact_name") or "",
            "email": c.get("email") or "",
            "phone": c.get("phone") or "",
            "role": c.get("role") or "",
        })
    return jsonify({"contacts": out})


@dashboard_bp.route("/api/dashboard/contacts/category-counts")
@login_required
def api_contacts_category_counts():
    """Return category name -> count for current company."""
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=True)
    if not company_id:
        return jsonify({"error": "Could not load contacts"}), 400
    counts = Database.get_contact_category_counts(company_id)
    total = sum(counts.values())
    return jsonify({"counts": counts, "total": total})


@dashboard_bp.route("/api/dashboard/contacts", methods=["POST"])
@login_required
def api_contacts_create():
    """Create a contact for the current company."""
    try:
        company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=True)
        if not company_id:
            return jsonify({"error": "Could not save contact"}), 400
        data = request.get_json(force=True, silent=True) or request.form or {}
        category = (data.get("category") or "").strip()
        if category not in Database.CONTACT_CATEGORIES:
            return jsonify({"error": "Invalid category"}), 400
        contact_id = Database.create_contact(
            company_id,
            category,
            organization=data.get("organization"),
            contact_name=data.get("contact_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            role=data.get("role"),
        )
        if not contact_id:
            return jsonify({"error": "Failed to create contact"}), 500
        return jsonify({"id": contact_id, "success": True}), 201
    except Exception as e:
        return jsonify({"error": "Failed to save contact. Please try again."}), 500


@dashboard_bp.route("/api/dashboard/contacts/<int:contact_id>", methods=["PUT"])
@login_required
def api_contacts_update(contact_id):
    """Update a contact."""
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=True)
    if not company_id:
        return jsonify({"error": "Could not update contact"}), 400
    data = request.json or request.form or {}
    category = data.get("category")
    if category is not None and (category or "").strip() not in Database.CONTACT_CATEGORIES:
        return jsonify({"error": "Invalid category"}), 400
    n = Database.update_contact(
        contact_id,
        company_id,
        category=data.get("category") if category is not None else None,
        organization=data.get("organization"),
        contact_name=data.get("contact_name"),
        email=data.get("email"),
        phone=data.get("phone"),
        role=data.get("role"),
    )
    if n == 0:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"success": True})


@dashboard_bp.route("/api/dashboard/contacts/<int:contact_id>", methods=["DELETE"])
@login_required
def api_contacts_delete(contact_id):
    """Delete a contact."""
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=True)
    if not company_id:
        return jsonify({"error": "Could not delete contact"}), 400
    n = Database.delete_contact(contact_id, company_id)
    if n == 0:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"success": True})
