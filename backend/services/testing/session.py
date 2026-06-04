"""
Session Manager for Testing - In-memory storage for test sessions
FIXED: Added update_feature_result function
"""
from typing import Optional, Dict, List
from fastapi import HTTPException

_test_sessions = {}


def create_test_session(
    session_id: str,
    workspace_path: str,
    project_path: str,
    app_url: Optional[str] = None
) -> None:
    """Initialize test session."""
    _test_sessions[session_id] = {
        "session_id": session_id,
        "workspace_path": workspace_path,
        "project_path": project_path,
        "app_url": app_url,
        "features": [],
        "test_results": {},
    }


def get_test_session(session_id: str) -> Dict:
    """Get session data."""
    if session_id not in _test_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return _test_sessions[session_id]


def set_features(session_id: str, features: List[Dict]) -> None:
    """Store detected features."""
    session = get_test_session(session_id)
    session["features"] = features


def update_feature_result(session_id: str, feature_id: str, result: Dict) -> None:
    """
    Store test result for a feature.
    This is called by test_executor after each test completes.
    """
    session = get_test_session(session_id)
    
    # Ensure test_results dict exists
    if "test_results" not in session:
        session["test_results"] = {}
    
    # Store result
    session["test_results"][feature_id] = result


def get_feature(session_id: str, feature_id: str) -> Dict:
    """Get specific feature."""
    session = get_test_session(session_id)
    for feature in session["features"]:
        if feature.get("id") == feature_id:
            return feature
    raise HTTPException(status_code=404, detail=f"Feature '{feature_id}' not found")


def set_app_url(session_id: str, app_url: str) -> None:
    """Update app URL."""
    session = get_test_session(session_id)
    session["app_url"] = app_url


def cleanup_test_session(session_id: str) -> None:
    """Remove session from memory."""
    if session_id in _test_sessions:
        del _test_sessions[session_id]


def list_test_sessions() -> List[str]:
    """List all active session IDs."""
    return list(_test_sessions.keys())
