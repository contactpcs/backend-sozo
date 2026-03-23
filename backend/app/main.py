"""Neurowellness Healthcare Platform API - Main Application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import db_manager
from app.core.logging import setup_logging
from app.shared.exceptions import NeurowellnessException
from app.modules.users.router import router as users_router, register_user, login as users_login
from app.shared.schemas.auth import LoginRequest, TokenResponse
from app.modules.users.schemas import UserCreate, UserResponse
from app.modules.patients.router import router as patients_router
from app.modules.prs import prs_router



# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    # Startup
    logger.info(f"Starting Neurowellness application in {settings.environment.value} environment")
    db_manager.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Neurowellness application")
    await db_manager.close()


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.app_version,
    description="Production-grade healthcare SaaS platform API",
    lifespan=lifespan,
    docs_url="/api/v1/docs" if settings.is_development else None,
    redoc_url="/api/v1/redoc" if settings.is_development else None,
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# Trust proxy headers for Azure App Service
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "*.azurewebsites.net",
        "*.neurowellness.health",
    ] if not settings.is_development else ["*"]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(NeurowellnessException)
async def neurowellness_exception_handler(request, exc: NeurowellnessException):
    """Handle application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc: SQLAlchemyError):
    """Handle database exceptions."""
    logger.error(f"Database error: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "DATABASE_ERROR",
            "message": "Database operation failed",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
    )


# ============================================================================
# ROUTES
# ============================================================================

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Application health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment.value,
    }


@app.get("/readiness", tags=["health"])
async def readiness_check():
    """Kubernetes readiness probe."""
    try:
        # Can add database connectivity check here
        return {
            "status": "ready",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@app.get("/liveness", tags=["health"])
async def liveness_check():
    """Kubernetes liveness probe."""
    return {
        "status": "alive",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }


@app.get("/health/db", tags=["health"])
async def database_health_check():
    """Database connectivity health check endpoint.
    
    Tests Supabase client connectivity (uses Supabase client only).
    """
    try:
        # Only check Supabase client connectivity to determine DB health
        supabase_ok = await db_manager._test_supabase_connection()

        if supabase_ok:
            logger.info("Supabase connectivity confirmed")
            return {
                "database": "connected",
                "supabase": "available",
                "status": "healthy",
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }
        logger.error("Supabase connectivity test failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase connection test failed"
        )
    except Exception as e:
        logger.error(f"✗ Database health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database health check failed: {str(e)}"
        )


# API v1 routes
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(patients_router, prefix=settings.api_v1_prefix)


# Public shortcut: map top-level /register to the users.register_user handler
@app.post("/register", tags=["auth"], response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def public_register(user_data: UserCreate):
    """Public registration endpoint mapped to users.register_user.

    This provides a convenience top-level route `/register` that forwards
    to the existing users router implementation.
    """
    return await register_user(user_data)


# Public shortcut: map top-level /login to the users.login handler
@app.post("/login", tags=["auth"], response_model=TokenResponse)
async def public_login(credentials: LoginRequest):
    """Public login endpoint mapped to users.login.

    Convenience top-level route `/login` that forwards to the existing
    users router implementation (demo mode returns a hardcoded token).
    """
    return await users_login(credentials)

# PRS module
app.include_router(prs_router, prefix=settings.api_v1_prefix)


# ============================================================================
# SUPABASE ROUTES
# ============================================================================

@app.get("/api/v1/supabase/status", tags=["supabase"])
async def supabase_status():
    """Get Supabase connection status and basic info."""
    try:
        # Test Supabase client connection
        result = await db_manager._test_supabase_connection()
        
        return {
            "supabase_connected": result,
            "supabase_url": settings.supabase_url,
            "client_initialized": db_manager._supabase_client is not None,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Supabase status check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supabase status check failed: {str(e)}"
        )


@app.get("/api/v1/supabase/tables/{table_name}", tags=["supabase"])
async def query_supabase_table(table_name: str, limit: int = 10):
    """Query a Supabase table directly (for testing/debugging)."""
    try:
        result = await db_manager.query_table(
            table=table_name,
            select="*"
        )
        
        if result["error"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supabase query failed: {result['error']}"
            )
        
        # Limit results for safety
        data = result["data"]
        if data and len(data) > limit:
            data = data[:limit]
        
        return {
            "table": table_name,
            "data": data,
            "count": len(data) if data else 0,
            "limited": len(result["data"]) > limit if result["data"] else False,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Table query failed for {table_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Table query failed: {str(e)}"
        )


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", tags=["info"])
async def root():
    """Root endpoint with API information."""
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment.value,
        "api_version": "v1",
        "docs_url": "/api/v1/docs",
        "redoc_url": "/api/v1/redoc",
        "health_check": "/health/db",
        "supabase": {
            "status_endpoint": "/api/v1/supabase/status",
            "url": settings.supabase_url,
            "connected": db_manager._supabase_client is not None
        }
    }


# ============================================================================
# STARTUP LOGGING
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
