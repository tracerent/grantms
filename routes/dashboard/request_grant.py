"""Add New Grant form: submit user-requested grant for admin review."""
from flask import request, session, jsonify

from utils.decorators import login_required
from utils.database import Database

from . import dashboard_bp


@dashboard_bp.route("/api/dashboard/request-grant", methods=["POST"])
@login_required
def api_request_grant():
    """Submit a user-requested grant (Add Grants form). Required: funding_organization, program_name, link_to_grant. Optional: funding_description."""
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=True)
    if not company_id:
        return jsonify({"error": "Could not submit request"}), 400
    data = request.get_json(force=True, silent=True) or request.form or {}
    funding_organization = (data.get("funding_organization") or "").strip()
    program_name = (data.get("program_name") or "").strip()
    funding_description = (data.get("funding_description") or "").strip() or None
    link_to_grant = (data.get("link_to_grant") or "").strip()
    if not funding_organization:
        return jsonify({"error": "Funding Organization is required"}), 400
    if not program_name:
        return jsonify({"error": "Program Name is required"}), 400
    if not link_to_grant:
        return jsonify({"error": "Link to Grant is required"}), 400
    try:
        rid = Database.create_requested_grant(
            company_id=company_id,
            user_id=session.get("user_id"),
            funding_organization=funding_organization,
            program_name=program_name,
            funding_description=funding_description,
            link_to_grant=link_to_grant,
        )
        if not rid:
            return jsonify({"error": "Failed to submit request"}), 500
        return jsonify({"success": True, "id": rid}), 201
    except Exception as e:
        return jsonify({"error": "Failed to submit request. Please try again."}), 500
