"""
Team management: membership, role permissions, and figuring out which team
a request is currently operating in.

Role rules (deliberately simple, no ownership transfer):
  - Every team has exactly one OWNER — the user who created it. Owners
    cannot be removed or demoted, so a team can never end up ownerless.
  - Only the OWNER can grant or revoke ADMIN.
  - OWNER and ADMIN can both invite/remove MEMBERs.
  - MEMBER has no team-management access at all.
"""
from __future__ import annotations

import logging

from flask import session

from models import Team, TeamMembership, TeamRole, User, db

logger = logging.getLogger(__name__)


class TeamError(Exception):
    """Raised for user-facing team-management validation/permission errors."""


def create_personal_team(user: User, name: str | None = None) -> Team:
    """Create a new team with `user` as its OWNER."""
    team = Team(name=name or f"{user.email.split('@')[0]}'s Team")
    db.session.add(team)
    db.session.flush()  # assigns team.id

    membership = TeamMembership(team_id=team.id, user_id=user.id, role=TeamRole.OWNER)
    db.session.add(membership)
    db.session.commit()
    logger.info("Created team id=%s %r for user %s", team.id, team.name, user.email)
    return team


def get_user_teams(user: User) -> list[Team]:
    """All teams a user belongs to, oldest membership first."""
    memberships = sorted(user.team_memberships, key=lambda m: m.created_at)
    return [m.team for m in memberships]


def get_membership(user: User, team: Team) -> TeamMembership | None:
    for membership in user.team_memberships:
        if membership.team_id == team.id:
            return membership
    return None


def resolve_current_team(user: User) -> Team | None:
    """
    Figure out which team the current session is operating in.

    Uses the team id stored in the session if it's still a valid membership;
    otherwise falls back to the user's first team and updates the session.
    Returns None only if the user somehow has no teams at all.
    """
    teams = get_user_teams(user)
    if not teams:
        return None

    team_by_id = {team.id: team for team in teams}
    session_team_id = session.get("current_team_id")

    if session_team_id in team_by_id:
        return team_by_id[session_team_id]

    default_team = teams[0]
    session["current_team_id"] = default_team.id
    return default_team


def switch_team(user: User, team_id: int) -> Team:
    """Set the session's active team, if the user is actually a member of it."""
    for team in get_user_teams(user):
        if team.id == team_id:
            session["current_team_id"] = team.id
            return team
    raise TeamError("You're not a member of that team.")


def invite_member(team: Team, actor: User, email: str, role: TeamRole) -> TeamMembership:
    """Add an existing, verified user to a team. Raises TeamError on any problem."""
    actor_membership = get_membership(actor, team)
    if actor_membership is None or actor_membership.role not in (TeamRole.OWNER, TeamRole.ADMIN):
        raise TeamError("Only owners and admins can invite members.")
    if role == TeamRole.OWNER:
        raise TeamError("A team can only have one owner.")
    if role == TeamRole.ADMIN and actor_membership.role != TeamRole.OWNER:
        raise TeamError("Only the owner can grant admin access.")

    email = (email or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        raise TeamError(
            "No account with that email exists yet. They'll need to register first."
        )
    if not user.is_verified:
        raise TeamError("That user hasn't verified their email yet.")
    if get_membership(user, team) is not None:
        raise TeamError("That person is already a member of this team.")

    membership = TeamMembership(team_id=team.id, user_id=user.id, role=role)
    db.session.add(membership)
    db.session.commit()
    logger.info("Added %s to team id=%s as %s", user.email, team.id, role.value)
    return membership


def change_role(team: Team, actor: User, target_user_id: int, new_role: TeamRole) -> TeamMembership:
    """Change a member's role. Only the OWNER can grant/revoke ADMIN. Raises TeamError on issues."""
    actor_membership = get_membership(actor, team)
    if actor_membership is None or actor_membership.role != TeamRole.OWNER:
        raise TeamError("Only the team owner can change roles.")

    target_membership = TeamMembership.query.filter_by(team_id=team.id, user_id=target_user_id).first()
    if not target_membership:
        raise TeamError("That person isn't a member of this team.")
    if target_membership.role == TeamRole.OWNER:
        raise TeamError("The team owner's role can't be changed.")
    if new_role == TeamRole.OWNER:
        raise TeamError("A team can only have one owner.")

    target_membership.role = new_role
    db.session.commit()
    logger.info("Changed role for user_id=%s in team_id=%s to %s", target_user_id, team.id, new_role.value)
    return target_membership


def remove_member(team: Team, actor: User, target_user_id: int) -> None:
    """Remove a member from a team. Raises TeamError on any permission issue."""
    actor_membership = get_membership(actor, team)
    if actor_membership is None or actor_membership.role not in (TeamRole.OWNER, TeamRole.ADMIN):
        raise TeamError("Only owners and admins can remove members.")

    target_membership = TeamMembership.query.filter_by(team_id=team.id, user_id=target_user_id).first()
    if not target_membership:
        raise TeamError("That person isn't a member of this team.")
    if target_membership.role == TeamRole.OWNER:
        raise TeamError("The team owner can't be removed.")
    if target_membership.role == TeamRole.ADMIN and actor_membership.role != TeamRole.OWNER:
        raise TeamError("Only the owner can remove an admin.")

    db.session.delete(target_membership)
    db.session.commit()
    logger.info("Removed user_id=%s from team_id=%s", target_user_id, team.id)
