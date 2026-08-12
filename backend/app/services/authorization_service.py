from __future__ import annotations

from sqlmodel import Session, select

from ..models.schemas import Problem, ProblemCollaborator, RoleCapability, User

DEFAULT_ROLE_CAPABILITIES: dict[str, set[str]] = {
    "admin": {"*"},
    "super_admin": {"*"},
    "instructor": {
        "problem:create",
        "problem:edit",
        "problem:review",
        "problem:publish",
        "problem:data.read",
        "submission:rejudge",
        "judge:operate",
        "homework:manage",
        "grading:manual",
        "content:manage",
        "exam:manage",
        "plagiarism:operate",
        "observability:read",
        "collaboration:manage",
    },
    "ta": {
        "problem:edit",
        "problem:data.read",
        "submission:rejudge",
        "homework:manage",
        "grading:manual",
        "content:manage",
        "plagiarism:operate",
        "observability:read",
        "collaboration:manage",
    },
    "problem_setter": {"problem:create", "problem:edit", "problem:data.read"},
    "reviewer": {"problem:review", "problem:publish", "problem:data.read"},
    "judge_operator": {
        "submission:rejudge",
        "judge:operate",
        "problem:data.read",
    },
    "support": {"problem:data.read", "audit:read", "observability:read"},
    "viewer": set(),
    "student": set(),
}
KNOWN_CAPABILITIES = set().union(*DEFAULT_ROLE_CAPABILITIES.values()) - {"*"}


class AuthorizationService:
    def capabilities_for(self, session: Session, user: User) -> set[str]:
        configured = set(
            session.exec(
                select(RoleCapability.capability).where(
                    RoleCapability.role_name == user.user_group
                )
            ).all()
        )
        if configured:
            return configured - {"__none__"}
        return DEFAULT_ROLE_CAPABILITIES.get(user.user_group, set())

    def has_capability(
        self, session: Session, user: User, capability: str
    ) -> bool:
        capabilities = self.capabilities_for(session, user)
        return "*" in capabilities or capability in capabilities

    def can_access_problem(
        self,
        session: Session,
        user: User,
        problem: Problem,
        capability: str,
        *,
        require_scope: bool = True,
    ) -> bool:
        if not self.has_capability(session, user, capability):
            return False
        if not require_scope or "*" in self.capabilities_for(session, user):
            return True
        if problem.owner_id == user.id:
            return True
        collaborator = session.exec(
            select(ProblemCollaborator).where(
                ProblemCollaborator.problem_id == problem.id,
                ProblemCollaborator.user_id == user.id,
            )
        ).first()
        return collaborator is not None and (
            capability != "problem:edit" or collaborator.can_edit
        )
