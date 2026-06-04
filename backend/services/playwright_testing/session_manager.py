"""
Session manager for Playwright testing.
Stores test sessions in memory (similar to visualizer's _session_graphs pattern).
"""
from pathlib import Path
from typing import Optional
from fastapi import HTTPException

# In-memory storage (similar to visualizer.py pattern)
_test_sessions = {}


def create_session(session_id: str, project_path: str, app_url: Optional[str] = None) -> None:
    """Initialize a new test session."""
    
    session_dir = Path(project_path).parent  # Parent is /tmp/pipeline_ui_sessions/{session_id}
    
    # Create test workspace directories
    tests_dir = session_dir / "tests"
    results_dir = session_dir / "test-results"
    artifacts_dir = session_dir / "artifacts"
    
    tests_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)
    artifacts_dir.mkdir(exist_ok=True)
    
    _test_sessions[session_id] = {
        "project_path": project_path,
        "app_url": app_url,
        "playwright_installed": False,
        "features": [],
        "tests_dir": str(tests_dir),
        "results_dir": str(results_dir),
        "artifacts_dir": str(artifacts_dir),
    }
    
    print(f"✓ Created test session: {session_id}")
    print(f"  Project: {project_path}")
    print(f"  Tests: {tests_dir}")
    print(f"  Results: {results_dir}")
    print(f"  Artifacts: {artifacts_dir}")


def add_features(session_id: str, features: list) -> None:
    """Store detected features in session."""
    if session_id not in _test_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    _test_sessions[session_id]["features"] = features
    print(f"✓ Added {len(features)} features to session {session_id}")


def update_feature(session_id: str, feature_id: str, updates: dict) -> None:
    """Update a specific feature's data."""
    if session_id not in _test_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    features = _test_sessions[session_id]["features"]
    for feature in features:
        if feature.get("id") == feature_id:
            feature.update(updates)
            print(f"✓ Updated feature {feature_id} in session {session_id}")
            return
    
    raise HTTPException(status_code=404, detail=f"Feature '{feature_id}' not found")


def get_session(session_id: str) -> dict:
    """Retrieve full session data."""
    if session_id not in _test_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    return _test_sessions[session_id]


def get_feature(session_id: str, feature_id: str) -> dict:
    """Get a specific feature from session."""
    session = get_session(session_id)
    
    for feature in session["features"]:
        if feature.get("id") == feature_id:
            return feature
    
    raise HTTPException(status_code=404, detail=f"Feature '{feature_id}' not found")


def set_app_url(session_id: str, app_url: str) -> None:
    """Set or update the application URL for testing."""
    if session_id not in _test_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    _test_sessions[session_id]["app_url"] = app_url
    print(f"✓ Set app_url for session {session_id}: {app_url}")


def mark_playwright_installed(session_id: str) -> None:
    """Mark that Playwright has been installed for this session."""
    if session_id not in _test_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    _test_sessions[session_id]["playwright_installed"] = True


def cleanup_session(session_id: str) -> None:
    """Remove session from memory (files cleaned up by zip_handler)."""
    if session_id in _test_sessions:
        del _test_sessions[session_id]
        print(f"✓ Cleaned up session {session_id}")


def list_sessions() -> list:
    """List all active session IDs (for debugging)."""
    return list(_test_sessions.keys())
