from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.auth.jwt import decode_token
import logging

logger = logging.getLogger(__name__)

class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Global middleware to validate JWT on all requests except whitelisted paths.
    """
    
    # Paths that don't require authentication
    WHITELIST = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/auth/login",
        "/api/auth/register",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip auth for whitelisted paths
        if any(path.startswith(wl) for wl in self.WHITELIST):
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            logger.warning(f"Missing or invalid Authorization header for {path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization header"}
            )
        
        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        
        if payload is None:
            logger.warning(f"Invalid JWT token for {path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"}
            )
        
        # Attach user info to request state for downstream use
        request.state.user = payload
        
        response = await call_next(request)
        return response
