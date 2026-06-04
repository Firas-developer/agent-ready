"""
Test Reporter - Generate test reports and summaries
"""
from typing import Dict
from . import session


def generate_test_report(session_id: str) -> Dict:
    """Generate comprehensive test report."""
    sess = session.get_test_session(session_id)
    features = sess.get("features", [])
    test_results = sess.get("test_results", {})
    
    total = len(features)
    passed = 0
    failed = 0
    skipped = 0
    
    for feature in features:
        feature_id = feature.get("id")
        result = test_results.get(feature_id, {})
        status = result.get("status", "not_run")
        
        if status == "passed":
            passed += 1
        elif status == "failed":
            failed += 1
        elif status in ["skipped", "not_run"]:
            skipped += 1
    
    executed = passed + failed
    pass_rate = (passed / executed * 100) if executed > 0 else 0
    
    return {
        "session_id": session_id,
        "app_url": sess.get("app_url"),
        "total_features": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "executed": executed,
        "pass_rate": pass_rate,
        "features": features,
        "test_results": test_results
    }
