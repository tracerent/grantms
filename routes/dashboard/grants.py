"""Saved grants and request-grant APIs."""
from flask import request, session, jsonify

from utils.decorators import login_required
from utils.database import Database
from utils.utils import Utils

from . import dashboard_bp
from .helpers import grant_timeline_item


@dashboard_bp.route("/api/dashboard/saved-grants")
def api_saved_grants():
    """Return saved grants (company portfolio) split into Next 6 Months and After 6 Months."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=False)
    company_grants = Database.get_company_grants(company_id) if company_id else []
    timeline_next_6 = []
    timeline_after_6 = []
    for g in (company_grants or []):
        if Utils.is_quarter_in_next_6_months(g.get("year"), g.get("quarter")):
            timeline_next_6.append(grant_timeline_item(g))
        else:
            timeline_after_6.append(grant_timeline_item(g))
    return jsonify({
        "timeline_next_6": timeline_next_6,
        "timeline_after_6": timeline_after_6,
        "total_count": len(company_grants or []),
    })


@dashboard_bp.route("/api/dashboard/grant/<int:grant_id>/progress")
def api_grant_progress(grant_id):
    """Return progress percent for a company grant (0–100). Placeholder until task list exists."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=False)
    if not company_id:
        return jsonify({"error": "No company"}), 403
    # TODO: compute from task list (completed_tasks / total_tasks) when available
    progress_percent = 0
    return jsonify({"progress_percent": progress_percent})
