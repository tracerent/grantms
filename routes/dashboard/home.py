"""Dashboard main view, account fragment, list filters, and dashboard-home API."""
from flask import render_template, request, redirect, url_for, session, jsonify

from utils.decorators import login_required
from utils.database import Database
from utils.utils import Utils

from . import dashboard_bp
from .helpers import current_plan_display, apply_grants_filters


@dashboard_bp.route("/api/dashboard/account-subscriptions-fragment")
@login_required
def account_subscriptions_fragment():
    """Return JSON with account, account_team, and banner HTML fragments for immediate UI update without full refresh (e.g. after plan upgrade)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    user = Database.get_user_by_id(user_id)
    company = Database.get_current_company(session.get("user_id"))
    company_id = company["id"] if company else None
    team_members = Database.get_company_members(company_id) if company_id else []
    plan_name = Database.get_subscription_plan_name(company_id)
    plan_max_members = Database.get_subscription_max_members(company_id)
    current_plan_display_data = current_plan_display(company_id)
    billing_history = Database.get_billing_history(company_id) if company_id else []
    payment_methods = Database.get_payment_methods(company_id) if company_id else []
    has_default_payment_method = any((pm or {}).get("is_default") for pm in (payment_methods or []))
    subscription_banner = Database.get_subscription_banner_status(company_id) if company_id else {"banner_type": "welcome", "days_left": None}
    account_html = render_template(
        "dashboard_account_fragment.html",
        current_plan_display=current_plan_display_data,
        billing_history=billing_history,
        payment_methods=payment_methods,
        has_default_payment_method=has_default_payment_method,
        team_members=team_members,
    )
    account_team_html = render_template(
        "dashboard_account_team_fragment.html",
        plan_name=plan_name,
        plan_max_members=plan_max_members,
        team_members=team_members,
        user=user or {},
    )
    banner_html = render_template(
        "dashboard_banner_fragment.html",
        subscription_banner=subscription_banner,
        has_default_payment_method=has_default_payment_method,
    )
    return jsonify({"account": account_html, "account_team": account_team_html, "banner": banner_html})


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard page."""
    user_id = session["user_id"]
    user = Database.get_user_by_id(user_id)
    if not user:
        session.clear()
        from flask import flash
        flash("Your session is invalid. Please sign in.", "warning")
        return redirect(url_for("auth.signin"))
    company = Database.get_current_company(session.get("user_id"))
    company_id = company["id"] if company else None
    company_grants = Database.get_company_grants(company_id) if company_id else []
    all_grants = Database.get_all_grants()
    saved_filters = Database.get_user_filter_settings(user_id)
    display_matches = apply_grants_filters(all_grants, saved_filters or {})
    portfolio_grant_ids = [g["id"] for g in company_grants] if company_grants else []
    portfolio_grants_info = [{"id": g["id"], "year": g.get("year"), "quarter": g.get("quarter")} for g in (company_grants or [])]
    timeline_next_6 = []
    timeline_after_6 = []
    for g in (company_grants or []):
        if Utils.is_quarter_in_next_6_months(g.get("year"), g.get("quarter")):
            timeline_next_6.append(g)
        else:
            timeline_after_6.append(g)

    app_in_progress = [g for g in (company_grants or []) if g.get("status") == "In Progress"]
    app_awaiting = [g for g in (company_grants or []) if g.get("status") in ("Applied", "Awaiting Review")]
    app_approved = [g for g in (company_grants or []) if g.get("status") == "Approved"]
    app_rejected = [g for g in (company_grants or []) if g.get("status") == "Rejected"]
    app_saved = [g for g in (company_grants or []) if g.get("status") == "Saved"]

    def _sum_amount(grants):
        return sum(float(g.get("funding_amount") or 0) for g in grants)

    app_kpis = {
        "in_progress": {"count": len(app_in_progress), "amount": _sum_amount(app_in_progress)},
        "awaiting": {"count": len(app_awaiting), "amount": _sum_amount(app_awaiting)},
        "approved": {"count": len(app_approved), "amount": _sum_amount(app_approved)},
        "rejected": {"count": len(app_rejected), "amount": _sum_amount(app_rejected)},
    }

    team_members = Database.get_company_members(company_id) if company_id else []
    plan_name = Database.get_subscription_plan_name(company_id)
    plan_max_members = Database.get_subscription_max_members(company_id)
    trial_status = Database.get_trial_status(company_id) if company_id else {"days_left": None, "ended": False}
    subscription_banner = Database.get_subscription_banner_status(company_id) if company_id else {"banner_type": "welcome", "days_left": None}
    is_primary_user = (user.get("is_primary") == 1) if user else False
    user_display_name = Utils.get_user_display_name(user) if user else ""
    current_plan_display_data = current_plan_display(company_id)
    billing_history = Database.get_billing_history(company_id) if company_id else []
    payment_methods = Database.get_payment_methods(company_id) if company_id else []
    has_default_payment_method = any((pm or {}).get("is_default") for pm in (payment_methods or []))

    return render_template(
        "dashboard.html",
        user=user,
        company_grants=company_grants,
        company=company,
        team_members=team_members,
        plan_name=plan_name,
        plan_max_members=plan_max_members,
        trial_status=trial_status,
        subscription_banner=subscription_banner,
        current_plan_display=current_plan_display_data,
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
        timeline_next_6=timeline_next_6,
        timeline_after_6=timeline_after_6,
        app_kpis=app_kpis,
        app_in_progress=app_in_progress,
        app_awaiting=app_awaiting,
        app_approved=app_approved,
        app_rejected=app_rejected,
        app_saved=app_saved,
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
        Database.save_user_filter_settings(session["user_id"], filters)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/api/dashboard-home")
def api_dashboard_home():
    """Return fresh Home tab data (company grants, matches by saved filters, total_value)."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=False)
    company_grants = Database.get_company_grants(company_id) if company_id else []
    all_grants = Database.get_all_grants()
    saved_filters = Database.get_user_filter_settings(session.get("user_id"))
    display_matches = apply_grants_filters(all_grants, saved_filters or {})
    total_value = 0
    for g in (company_grants or []):
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
        "company_grants": [grant_for_json(g) for g in (company_grants or [])],
        "all_grants": [match_for_json(g) for g in display_matches],
        "total_value": total_value,
    })
