"""Playwright testing services."""

from . import feature_detector
from . import feature_executor  # ✅ ADD THIS LINE
from . import session_manager
from . import test_generator
from . import test_executor

__all__ = [
    'feature_detector',
    'feature_executor',  # ✅ ADD THIS LINE
    'session_manager',
    'test_generator',
    'test_executor'
]
