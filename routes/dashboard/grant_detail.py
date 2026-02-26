"""Grant detail page: progress, message board, supporting docs."""
from flask import render_template, redirect, url_for, session, request, jsonify

from utils.decorators import login_required
from utils.database import Database

from . import dashboard_bp


def _checkpoint_stage(status):
    """Map status to 1-based stage: 1=Initiated (Saved), 2=In Progress, 3=Submitted, 4=Approved/Rejected."""
    s = (status or "").strip()
    if s == "Saved":
        return 1
    if s == "In Progress":
        return 2
    if s in ("Applied", "Awaiting Review", "Submitted"):
        return 3
    if s in ("Approved", "Rejected"):
        return 4
    return 1


@dashboard_bp.route("/dashboard/grant/<int:grant_id>")
@login_required
def grant_detail(grant_id):
    """Grant detail page: title, view details modal, checkpoint stages, progress bar, message board, supporting docs."""
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=False)
    if not company_id:
        return redirect(url_for("dashboard.dashboard"))
    grant = Database.get_company_grant(company_id, grant_id)
    if not grant:
        return redirect(url_for("dashboard.dashboard"))
    messages = Database.get_grant_messages(company_id, grant_id)
    status = grant.get("status") or "Saved"
    stage = _checkpoint_stage(status)
    # Progress %: placeholder until task list is implemented (completed_tasks / total_tasks)
    progress_percent = 0
    return render_template(
        "grant_detail.html",
        grant=grant,
        messages=messages,
        status=status,
        stage=stage,
        progress_percent=progress_percent,
    )


@dashboard_bp.route("/api/dashboard/grant/<int:grant_id>/message", methods=["POST"])
@login_required
def grant_detail_post_message(grant_id):
    """Post a message to the grant message board."""
    company_id = Database.get_current_company_id(session.get("user_id"), create_if_missing=False)
    if not company_id:
        return jsonify({"error": "No company"}), 403
    grant = Database.get_company_grant(company_id, grant_id)
    if not grant:
        return jsonify({"error": "Grant not found"}), 404
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    user_id = session.get("user_id")
    msg_id = Database.add_grant_message(company_id, grant_id, user_id, message)
    if not msg_id:
        return jsonify({"error": "Failed to save message"}), 500
    messages = Database.get_grant_messages(company_id, grant_id)
    out = []
    for m in messages:
        out.append({
            "id": m.get("id"),
            "user_id": m.get("user_id"),
            "first_name": m.get("first_name") or "",
            "last_name": m.get("last_name") or "",
            "message": m.get("message") or "",
            "created_at": m.get("created_at").strftime("%b %d, %Y %I:%M %p") if m.get("created_at") else "",
        })
    return jsonify({"success": True, "messages": out})
