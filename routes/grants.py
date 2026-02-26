"""Apply grant (future flow), update status, save/remove saved grants."""
from flask import Blueprint, request, session, jsonify, url_for

from utils.database import Database

grants_bp = Blueprint("grants", __name__)


@grants_bp.route("/apply-grant", methods=["POST"])
def apply_grant():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    grant_id = data.get("grant_id")
    user_id = session["user_id"]

    company = Database.get_company_for_user(user_id)
    if not company or not Database.subscription_can_start_grants(company["id"]):
        return jsonify({
            "error": "Your free trial has ended. Please upgrade to continue.",
            "redirect": url_for("dashboard.dashboard"),
            "open_subscriptions": True,
        }), 403

    try:
        Database.apply_for_grant_company(company["id"], grant_id)
        return jsonify({"success": True, "message": "Grant application started"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grants_bp.route("/update-grant-status", methods=["POST"])
def update_grant_status_route():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    grant_id = data.get("grant_id")
    status = data.get("status")
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=False)
    if not company_id:
        return jsonify({"error": "No company"}), 403

    try:
        Database.update_grant_status_company(company_id, grant_id, status)
        return jsonify({"success": True, "message": "Status updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grants_bp.route("/add-grant-to-portfolio", methods=["POST"])
def add_grant_to_portfolio_route():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    grant_id = data.get("grant_id")
    quarter = (data.get("quarter") or "").strip()
    user_id = session["user_id"]

    company = Database.get_company_for_user(user_id)
    if not company or not Database.subscription_can_start_grants(company["id"]):
        return jsonify({
            "error": "Your free trial has ended. Please upgrade to continue.",
            "redirect": url_for("dashboard.dashboard"),
            "open_subscriptions": True,
        }), 403

    if not quarter:
        return jsonify({"error": "Quarter is required"}), 400

    try:
        Database.add_grant_to_portfolio_company(company["id"], grant_id, quarter)
        return jsonify({"success": True, "message": "Grant saved"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grants_bp.route("/remove-grant-from-portfolio", methods=["POST"])
def remove_grant_from_portfolio_route():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    grant_id = data.get("grant_id")
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=False)
    if not company_id:
        return jsonify({"error": "No company"}), 403

    if grant_id is None:
        return jsonify({"error": "grant_id is required"}), 400

    try:
        Database.remove_grant_from_portfolio_company(company_id, grant_id)
        return jsonify({"success": True, "message": "Grant removed from saved list"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
