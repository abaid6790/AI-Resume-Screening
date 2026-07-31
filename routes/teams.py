"""Teams blueprint: membership, roles, team switching, and the audit log view."""
from __future__ import annotations

import logging

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import AuditLog, TeamRole
from services import audit_service
from services.team_service import (
    TeamError,
    change_role,
    create_personal_team,
    get_membership,
    get_user_teams,
    invite_member,
    remove_member,
    switch_team,
)

logger = logging.getLogger(__name__)

teams_bp = Blueprint("teams", __name__)

AUDIT_PAGE_SIZE = 25


@teams_bp.route("/")
@login_required
def index():
    """Team management: current team's members, your other teams, invite/role controls."""
    team = g.current_team
    membership = get_membership(current_user, team)
    return render_template(
        "teams/index.html",
        team=team,
        my_role=membership.role if membership else None,
        members=sorted(team.memberships, key=lambda m: m.created_at),
        all_teams=get_user_teams(current_user),
        TeamRole=TeamRole,
    )


@teams_bp.route("/invite", methods=["POST"])
@login_required
def invite():
    email = request.form.get("email", "")
    role_value = request.form.get("role", TeamRole.MEMBER.value)
    try:
        role = TeamRole(role_value)
        membership = invite_member(g.current_team, current_user, email, role)
    except (TeamError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("teams.index"))

    audit_service.log(
        "member_invited",
        f"Invited {membership.user.email} as {membership.role.value}",
        user=current_user,
        team_id=g.current_team.id,
    )
    flash(f"Added {membership.user.email} to the team.", "success")
    return redirect(url_for("teams.index"))


@teams_bp.route("/members/<int:user_id>/role", methods=["POST"])
@login_required
def update_role(user_id: int):
    role_value = request.form.get("role", "")
    try:
        role = TeamRole(role_value)
        membership = change_role(g.current_team, current_user, user_id, role)
    except (TeamError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("teams.index"))

    audit_service.log(
        "role_changed",
        f"Changed {membership.user.email}'s role to {membership.role.value}",
        user=current_user,
        team_id=g.current_team.id,
    )
    flash(f"Updated {membership.user.email}'s role to {membership.role.value.title()}.", "success")
    return redirect(url_for("teams.index"))


@teams_bp.route("/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove(user_id: int):
    try:
        remove_member(g.current_team, current_user, user_id)
    except TeamError as exc:
        flash(str(exc), "error")
        return redirect(url_for("teams.index"))

    audit_service.log(
        "member_removed", f"Removed user_id={user_id} from the team",
        user=current_user, team_id=g.current_team.id,
    )
    flash("Member removed.", "success")
    return redirect(url_for("teams.index"))


@teams_bp.route("/create", methods=["POST"])
@login_required
def create():
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Give the new team a name.", "error")
        return redirect(url_for("teams.index"))

    team = create_personal_team(current_user, name=name)
    audit_service.log("team_created", f"Created team {team.name!r}", user=current_user, team_id=team.id)
    flash(f'Created "{team.name}" — you\'re now viewing it.', "success")

    from flask import session
    session["current_team_id"] = team.id
    return redirect(url_for("teams.index"))


@teams_bp.route("/switch/<int:team_id>", methods=["POST"])
@login_required
def switch(team_id: int):
    try:
        team = switch_team(current_user, team_id)
    except TeamError as exc:
        flash(str(exc), "error")
        return redirect(url_for("teams.index"))

    flash(f'Switched to "{team.name}".', "success")
    return redirect(request.referrer or url_for("dashboard.index"))


@teams_bp.route("/audit")
@login_required
def audit_log():
    """Paginated audit log for the current team. Owners/admins only."""
    membership = get_membership(current_user, g.current_team)
    if not membership or membership.role not in (TeamRole.OWNER, TeamRole.ADMIN):
        flash("Only owners and admins can view the audit log.", "error")
        return redirect(url_for("teams.index"))

    page = request.args.get("page", 1, type=int)
    pagination = (
        AuditLog.query.filter_by(team_id=g.current_team.id)
        .order_by(AuditLog.created_at.desc())
        .paginate(page=page, per_page=AUDIT_PAGE_SIZE, error_out=False)
    )
    return render_template("teams/audit_log.html", pagination=pagination, team=g.current_team)
