"""Apply grant, update status, add/remove from portfolio."""
from flask import Blueprint, request, session, jsonify, url_for

from utils.database import (
    get_company_for_user,
    apply_for_grant,
    update_grant_status,
    add_grant_to_portfolio,
    remove_grant_from_portfolio,
    subscription_can_start_grants,
)

grants_bp = Blueprint("grants", __name__)


@grants_bp.route("/apply-grant", methods=["POST"])
def apply_grant():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    grant_id = data.get("grant_id")
    user_id = session["user_id"]

    company = get_company_for_user(user_id)
    if not company or not subscription_can_start_grants(company["id"]):
        return jsonify({
            "error": "Your free trial has ended. Please upgrade to continue.",
            "redirect": url_for("dashboard.dashboard"),
            "open_subscriptions": True,
        }), 403

    try:
        apply_for_grant(user_id, grant_id)
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
    user_id = session["user_id"]

    try:
        update_grant_status(user_id, grant_id, status)
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

    company = get_company_for_user(user_id)
    if not company or not subscription_can_start_grants(company["id"]):
        return jsonify({
            "error": "Your free trial has ended. Please upgrade to continue.",
            "redirect": url_for("dashboard.dashboard"),
            "open_subscriptions": True,
        }), 403

    if not quarter:
        return jsonify({"error": "Quarter is required"}), 400

    try:
        add_grant_to_portfolio(user_id, grant_id, quarter)
        return jsonify({"success": True, "message": "Grant added to portfolio"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@grants_bp.route("/remove-grant-from-portfolio", methods=["POST"])
def remove_grant_from_portfolio_route():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    grant_id = data.get("grant_id")
    user_id = session["user_id"]

    if grant_id is None:
        return jsonify({"error": "grant_id is required"}), 400

    try:
        remove_grant_from_portfolio(user_id, grant_id)
        return jsonify({"success": True, "message": "Grant removed from portfolio"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
