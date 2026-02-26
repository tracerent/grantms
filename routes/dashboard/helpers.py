"""Shared helpers for dashboard routes."""
from datetime import datetime

from utils.database import Database


def current_plan_display(company_id):
    """Build dict for Current Plan section.
    Basic: no billing (billed_amount None). Paid plans: billed annually; billed_amount = last invoice amount or plan annual_cost; monthly_cost = current plan monthly."""
    sub = Database.get_company_subscription(company_id) if company_id else None
    if not sub:
        return {"plan_display_name": "Basic Plan", "annual_cost": 0, "monthly_cost": 0, "member_count": 1,
                "days_remaining": None, "next_billing_date": None, "subscription_id": 0, "billed_amount": None}
    plan_id = int(sub.get("subscription_id", 0))
    plan_names = {0: "Basic Plan", 1: "Success Plan", 2: "Premium Plan"}
    plan_display_name = plan_names.get(plan_id, "Custom Plan")
    monthly = float(sub.get("monthly_cost") or 0)
    annual = float(sub.get("annual_cost") or 0)
    member_count = int(sub.get("member_count") or 1)
    billed_amount = None
    if plan_id != 0:
        billed_amount = Database.get_last_invoice_amount_for_plan(company_id, plan_id)
        if billed_amount is None:
            billed_amount = annual
    ends_at = sub.get("ends_at")
    now = datetime.now()
    days_remaining = None
    next_billing_date = None
    if plan_id != 0 and ends_at is not None:
        try:
            end_dt = ends_at if hasattr(ends_at, "__le__") else datetime.fromisoformat(str(ends_at).replace("Z", "+00:00"))
            if end_dt > now:
                days_remaining = (end_dt - now).days
            next_billing_date = end_dt.strftime("%b %d, %Y") if hasattr(end_dt, "strftime") else str(ends_at)[:10]
        except (TypeError, ValueError):
            pass
    if plan_id == 0 and ends_at is not None:
        try:
            end_dt = ends_at if hasattr(ends_at, "__le__") else datetime.fromisoformat(str(ends_at).replace("Z", "+00:00"))
            if end_dt > now:
                days_remaining = (end_dt - now).days
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
        "billed_amount": billed_amount,
    }


def apply_grants_filters(grants_list, filters_dict):
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


def grant_timeline_item(g):
    """Serialize a company grant for Saved Grants timeline (id, title, funding_amount, deadline, planned quarter)."""
    year, quarter = g.get("year"), g.get("quarter")
    planned = f"{year} Q{quarter}" if year is not None and quarter is not None else ""
    return {
        "id": g.get("id"),
        "title": g.get("title") or "",
        "funding_amount": float(g["funding_amount"]) if g.get("funding_amount") is not None else 0,
        "deadline": g.get("deadline") or "",
        "planned": planned,
    }
