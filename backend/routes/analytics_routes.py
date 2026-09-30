"""
backend/routes/analytics_routes.py
===================================
GET /api/analytics/dashboard - all numbers + chart data behind the dashboard
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(request: Request, user_id: str = Depends(get_current_user)):
    return request.app.state.analytics_service.dashboard(user_id)
