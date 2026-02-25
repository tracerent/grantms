"""Dashboard page and dashboard-home / save-list-filters APIs."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify

from utils.decorators import login_required
from utils.database import (
    get_user_by_id, get_user_grants, get_all_grants, get_user_filter_settings, save_user_filter_settings,
    get_company_for_user, get_company_members, get_subscription_plan_name, get_subscription_max_members,
    get_trial_status, get_subscription_banner_status, get_billing_history, get_payment_methods,
    get_company_subscription, _user_display_name,
)

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="")


def _current_plan_display(company_id):
    """Build dict for Subscription Management: plan_display_name, annual_cost, monthly_cost, member_count, days_remaining, next_billing_date, subscription_id."""
    sub = get_company_subscription(company_id) if company_id else None
    if not sub:
        return {"plan_display_name": "Basic Plan", "annual_cost": 0, "monthly_cost": 0, "member_count": 1,
                "days_remaining": None, "next_billing_date": None, "subscription_id": 0}
    plan_id = int(sub.get("subscription_id", 0))
    plan_names = {0: "Basic Plan", 1: "Success Plan", 2: "Premium Plan"}
    plan_display_name = plan_names.get(plan_id, "Custom Plan")
    monthly = float(sub.get("monthly_cost") or 0)
    annual = float(sub.get("annual_cost") or 0)
    member_count = int(sub.get("member_count") or 1)
    ends_at = sub.get("ends_at")
    now = datetime.now()
    days_remaining = None
    next_billing_date = None
    if ends_at is not None:
        try:
            end_dt = ends_at if hasattr(ends_at, "__le__") else datetime.fromisoformat(str(ends_at).replace("Z", "+00:00"))
            if end_dt > now:
                days_remaining = (end_dt - now).days
            next_billing_date = end_dt.strftime("%b %d, %Y") if hasattr(end_dt, "strftime") else str(ends_at)[:10]
        except (TypeError, ValueError):
            pass
    return {
        "plan_display_name": plan_display_name,
        "annual_cost": annual,
        "monthly_cost": monthly,
        "member_count": member_count,
        "days_remaining": days_remaining,
        "next_billing_date": next_billing_date,
        "subscription_id": plan_id,
    }


def _apply_grants_filters(grants_list, filters_dict):
    """Apply List Building filters (status, funding_for) to a list of grant dicts."""
    if not grants_list:
        return []
    if not filters_dict:
        return list(grants_list)
    out = list(grants_list)
    status = (filters_dict.get("status") or "").strip()
    if status:
        out = [g for g in out if (g.get("status") or "") == status]
    funding_for = (filters_dict.get("funding_for") or "").strip()
    if funding_for:
        want = funding_for.lower()
        out = [
            g for g in out
            if want in (g.get("category") or "").lower() or want in (g.get("funding_for") or "").lower()
        ]
    return out


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        from flask import flash
        flash("Your session is invalid. Please sign in.", "warning")
        return redirect(url_for("auth.signin"))
    user_grants = get_user_grants(user_id)
    all_grants = get_all_grants()
    saved_filters = get_user_filter_settings(user_id)
    display_matches = _apply_grants_filters(all_grants, saved_filters or {})
    portfolio_grant_ids = [g["id"] for g in user_grants] if user_grants else []
    portfolio_grants_info = [{"id": g["id"], "year": g.get("year"), "quarter": g.get("quarter")} for g in (user_grants or [])]
    company = get_company_for_user(user_id)
    company_id = company["id"] if company else None
    team_members = get_company_members(company_id) if company_id else []
    plan_name = get_subscription_plan_name(company_id)
    plan_max_members = get_subscription_max_members(company_id)
    trial_status = get_trial_status(company_id) if company_id else {"days_left": None, "ended": False}
    subscription_banner = get_subscription_banner_status(company_id) if company_id else {"banner_type": "welcome", "days_left": None}
    is_primary_user = (user.get("is_primary") == 1) if user else False
    user_display_name = _user_display_name(user) if user else ""
    current_plan_display = _current_plan_display(company_id)
    billing_history = get_billing_history(company_id) if company_id else []
    payment_methods = get_payment_methods(company_id) if company_id else []
    has_default_payment_method = any((pm or {}).get("is_default") for pm in (payment_methods or []))

    return render_template(
        "dashboard.html",
        user=user,
        user_grants=user_grants,
        company=company,
        team_members=team_members,
        plan_name=plan_name,
        plan_max_members=plan_max_members,
        trial_status=trial_status,
        subscription_banner=subscription_banner,
        current_plan_display=current_plan_display,
        billing_history=billing_history,
        payment_methods=payment_methods,
        has_default_payment_method=has_default_payment_method,
        is_primary_user=is_primary_user,
        user_display_name=user_display_name,
        favorites=[],
        all_grants=all_grants,
        display_matches=display_matches,
        portfolio_grant_ids=portfolio_grant_ids,
        portfolio_grants_info=portfolio_grants_info,
        saved_filters=saved_filters,
    )


@dashboard_bp.route("/api/save-list-filters", methods=["POST"])
def api_save_list_filters():
    """Save List Building filter settings for the current user."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.json or {}
    filters = {
        "status": (data.get("status") or "").strip(),
        "funding_for": (data.get("funding_for") or "").strip(),
    }
    try:
        save_user_filter_settings(session["user_id"], filters)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/api/dashboard-home")
def api_dashboard_home():
    """Return fresh Home tab data (user_grants, matches by saved filters, total_value)."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    user_id = session["user_id"]
    user_grants = get_user_grants(user_id)
    all_grants = get_all_grants()
    saved_filters = get_user_filter_settings(user_id)
    display_matches = _apply_grants_filters(all_grants, saved_filters or {})
    total_value = 0
    for g in (user_grants or []):
        amt = g.get("funding_amount")
        total_value += float(amt) if amt is not None else 0

    def grant_for_json(g):
        return {
            "id": g.get("id"),
            "title": g.get("title") or "",
            "status": g.get("status") or "",
            "funding_amount": float(g["funding_amount"]) if g.get("funding_amount") is not None else 0,
        }

    def match_for_json(g):
        return {
            "id": g.get("id"),
            "title": g.get("title") or "",
            "funding_amount": float(g["funding_amount"]) if g.get("funding_amount") is not None else 0,
        }

    return jsonify({
        "user_grants": [grant_for_json(g) for g in (user_grants or [])],
        "all_grants": [match_for_json(g) for g in display_matches],
        "total_value": total_value,
    })
