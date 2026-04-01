import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from backend.core.security import decode_access_token

logger = logging.getLogger(__name__)

# Paths that do NOT require authentication
_PUBLIC_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/login",
    "/auth/register",
    "/health",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Attach decoded JWT user info to ``request.state.user``.

    Does NOT reject unauthenticated requests — that responsibility
    belongs to the ``get_current_user`` dependency on protected routes.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.user = None

        # Skip public paths
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_access_token(token)
                request.state.user = payload
            except Exception:
                pass  # dependency handles rejection

        return await call_next(request)
