"""Profile, company, team, payment methods, subscription upgrade."""
from datetime import datetime
from flask import Blueprint, request, redirect, url_for, session, flash, jsonify

from utils.database import (
    update_user_profile, update_user_personal_info, get_user_by_id, get_company_for_user,
    get_company_members, get_subscription_max_members, create_company_for_user,
    update_company, update_company_subscription, set_user_active, add_team_member,
    get_plan_by_id, get_payment_methods, add_payment_method, set_default_payment_method,
    clear_default_payment_method, remove_payment_method, add_invoice,
)

account_bp = Blueprint("account", __name__)


def _str_val(data, key):
    v = data.get(key)
    return (v.strip() if isinstance(v, str) else (str(v) if v is not None else "")) or None


def _int_val(data, key):
    v = data.get(key)
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _date_val(data, key):
    v = data.get(key)
    if not v:
        return None
    s = (v.strip() if isinstance(v, str) else str(v))[:10]
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


@account_bp.route("/update-profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    user_id = session["user_id"]
    try:
        update_user_profile(user_id)
        flash("Profile updated", "success")
        return redirect(url_for("dashboard.dashboard"))
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("dashboard.dashboard"))


@account_bp.route("/api/account/profile", methods=["POST"])
def api_account_profile():
    """Update current user's personal info (first_name, last_name, email, job_title)."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json() or {}
    user_id = session["user_id"]
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip()
    job_title = (data.get("job_title") or "").strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400
    try:
        update_user_personal_info(
            user_id,
            first_name=first_name or None,
            last_name=last_name or None,
            email=email,
            job_title=job_title or None,
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@account_bp.route("/api/account/company", methods=["POST"])
def api_account_company():
    """Update company info for current user. Creates company if user has none."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json() or {}
    user_id = session["user_id"]
    company = get_company_for_user(user_id)
    if not company:
        company = create_company_for_user(user_id)
    update_company_subscription(company["id"])
    try:
        update_company(
            company["id"],
            legal_entity_name=_str_val(data, "legal_entity_name"),
            operating_name=_str_val(data, "operating_name"),
            company_name=_str_val(data, "company_name"),
            provincial_corporate_access_number=_str_val(data, "provincial_corporate_access_number"),
            workers_compensation_number=_str_val(data, "workers_compensation_number"),
            business_number=_str_val(data, "business_number"),
            business_phone_number=_str_val(data, "business_phone_number"),
            address=_str_val(data, "address"),
            date_of_incorporation=_date_val(data, "date_of_incorporation"),
            postal_code=_str_val(data, "postal_code"),
            years_in_operation=_int_val(data, "years_in_operation"),
            founder_name=_str_val(data, "founder_name"),
            website=_str_val(data, "website"),
            founder_title=_str_val(data, "founder_title"),
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@account_bp.route("/api/account/team/add", methods=["POST"])
def api_account_team_add():
    """Add a team member. Any company member can add; checks plan limit."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    user_id = session["user_id"]
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 401
    company = get_company_for_user(user_id)
    if not company:
        return jsonify({"error": "No company associated with your account"}), 400
    plan_max = get_subscription_max_members(company["id"])
    current_count = len(get_company_members(company["id"]))
    if current_count >= plan_max:
        return jsonify({"error": f"Your plan allows up to {plan_max} member(s). Upgrade to add more."}), 400
    data = request.get_json() or {}
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip()
    job_title = (data.get("job_title") or "").strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400
    try:
        new_id = add_team_member(company["id"], first_name, last_name, email, job_title)
        if new_id:
            return jsonify({"success": True, "user_id": new_id})
        return jsonify({"error": "Could not add member (email may already be registered)"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@account_bp.route("/api/account/team/toggle-active", methods=["POST"])
def api_account_team_toggle_active():
    """Activate or deactivate a team member. Any company member can toggle; cannot toggle self."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    user_id = session["user_id"]
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 401
    data = request.get_json() or {}
    target_id = data.get("user_id")
    if target_id is None:
        return jsonify({"error": "user_id is required"}), 400
    try:
        target_id = int(target_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user_id"}), 400
    if target_id == user_id:
        return jsonify({"error": "You cannot change your own status"}), 400
    company = get_company_for_user(user_id)
    if not company:
        return jsonify({"error": "No company"}), 400
    members = get_company_members(company["id"])
    target = next((m for m in members if m["id"] == target_id), None)
    if not target:
        return jsonify({"error": "User not found in your team"}), 404
    new_active = 0 if target.get("is_active") == 1 else 1
    set_user_active(target_id, new_active)
    return jsonify({"success": True, "is_active": new_active})


@account_bp.route("/api/account/payment-methods/add", methods=["POST"])
def api_account_payment_methods_add():
    """Add a payment method for the current user's company."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    user_id = session["user_id"]
    company = get_company_for_user(user_id)
    if not company:
        return jsonify({"error": "No company associated with your account"}), 400
    data = request.get_json() or {}
    card_number = (data.get("card_number") or "").replace(" ", "")
    expiry = (data.get("expiry") or "").strip()
    save_for_future = bool(data.get("save_for_future"))

    brand = "Card"
    if card_number.startswith("4"):
        brand = "Visa"
    elif card_number[:2] in ("51", "52", "53", "54", "55"):
        brand = "Mastercard"
    elif card_number.startswith("3"):
        brand = "Amex"

    last4 = card_number[-4:] if len(card_number) >= 4 else ""
    expiry_month = None
    expiry_year = None
    if expiry and len(expiry) >= 4 and "/" in expiry:
        try:
            mm, yy = expiry.split("/", 1)
            expiry_month = int(mm)
            expiry_year = 2000 + int(yy)
        except (ValueError, TypeError):
            expiry_month = None
            expiry_year = None

    if not save_for_future:
        return jsonify({
            "success": True,
            "saved": False,
            "message": "Payment processing is not implemented yet.",
        })

    if not last4:
        return jsonify({"error": "Card number is invalid"}), 400

    try:
        pm_id = add_payment_method(company["id"], brand=brand, last4=last4, expiry_month=expiry_month, expiry_year=expiry_year)
        if pm_id:
            return jsonify({
                "success": True,
                "saved": True,
                "message": "Payment method saved. Payment processing is not implemented yet.",
                "payment_method": {
                    "payment_method_id": pm_id,
                    "brand": brand,
                    "last4": last4,
                    "expiry_month": expiry_month,
                    "expiry_year": expiry_year,
                    "is_default": False,
                },
            })
        return jsonify({"error": "Failed to save payment method"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@account_bp.route("/api/account/payment-methods/remove", methods=["POST"])
def api_account_payment_methods_remove():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    user_id = session["user_id"]
    company = get_company_for_user(user_id)
    if not company:
        return jsonify({"error": "No company associated with your account"}), 400
    data = request.get_json() or {}
    method_id = data.get("method_id")
    try:
        method_id = int(method_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid payment method id"}), 400
    try:
        removed = remove_payment_method(company["id"], method_id)
        if removed:
            return jsonify({"success": True})
        return jsonify({"error": "Payment method not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@account_bp.route("/api/account/payment-methods/set-default", methods=["POST"])
def api_account_payment_methods_set_default():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    company = get_company_for_user(session["user_id"])
    if not company:
        return jsonify({"error": "No company associated with your account"}), 400
    data = request.get_json() or {}
    method_id = data.get("payment_method_id") or data.get("method_id")
    try:
        method_id = int(method_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid payment method id"}), 400
    try:
        updated = set_default_payment_method(company["id"], method_id)
        if updated:
            return jsonify({"success": True})
        return jsonify({"error": "Payment method not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@account_bp.route("/api/account/payment-methods/clear-default", methods=["POST"])
def api_account_payment_methods_clear_default():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    company = get_company_for_user(session["user_id"])
    if not company:
        return jsonify({"error": "No company associated with your account"}), 400
    try:
        clear_default_payment_method(company["id"])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@account_bp.route("/api/account/subscription/upgrade", methods=["POST"])
def api_account_subscription_upgrade():
    """Upgrade company to Success (1) or Premium (2)."""
    if "user_id" not in session:
        flash("Please sign in to change your plan.", "warning")
        return redirect(url_for("auth.signin"))
    company = get_company_for_user(session["user_id"])
    if not company:
        flash("No company associated with your account.", "danger")
        return redirect(url_for("dashboard.dashboard"))
    try:
        subscription_id = int(request.form.get("subscription_id", 0))
    except (TypeError, ValueError):
        subscription_id = None
    if subscription_id not in (1, 2):
        flash("Invalid plan selected.", "danger")
        return redirect(url_for("dashboard.dashboard") + "#account-subscriptions")
    update_company_subscription(company["id"], subscription_id=subscription_id)
    plan = get_plan_by_id(subscription_id)
    if plan:
        plan_name = plan.get("plan_name") or "Plan"
        amount = plan.get("monthly_cost") if plan.get("monthly_cost") is not None else 0
        add_invoice(company["id"], subscription_id, plan_name, amount, currency="USD", status="succeeded")
    flash("Your plan has been updated.", "success")
    return redirect(url_for("dashboard.dashboard") + "#account-subscriptions")
