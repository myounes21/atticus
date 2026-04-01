from fastapi import Depends, HTTPException, status

from backend.core.dependencies import CurrentUser, get_current_user


class RoleChecker:
    """Callable dependency that checks the user's role against an allow-list."""

    def __init__(self, allowed_roles: list[str]) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(
        self, user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted. Required: {', '.join(self.allowed_roles)}",
            )
        return user


# Convenience instances
admin_only = RoleChecker(["admin"])
lawyer_only = RoleChecker(["lawyer"])
any_authenticated = RoleChecker(["admin", "lawyer"])
