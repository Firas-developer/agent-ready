"""
Screenshot Manager - Works with Playwright Python API
"""
from pathlib import Path
from datetime import datetime


class ScreenshotManager:
    def __init__(self, session_id: str, workspace_path: str):
        self.session_id = session_id
        self.workspace_path = Path(workspace_path)
        self.screenshots_dir = self.workspace_path / "screenshots"
        
        # Create directories
        self.before_dir = self.screenshots_dir / "before"
        self.after_dir = self.screenshots_dir / "after"
        self.failures_dir = self.screenshots_dir / "failures"
        
        self.before_dir.mkdir(parents=True, exist_ok=True)
        self.after_dir.mkdir(parents=True, exist_ok=True)
        self.failures_dir.mkdir(parents=True, exist_ok=True)
