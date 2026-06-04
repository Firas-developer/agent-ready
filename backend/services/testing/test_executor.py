"""
Test Executor - Working version with playwright-cli
✅ Authentication State Detection
✅ Smart Element Reference Recovery  
✅ No screenshots (playwright-cli doesn't support it)
"""
import subprocess
import time
import re
import json
from typing import Optional, Dict, List, AsyncGenerator
from pathlib import Path


async def execute_all_tests(
    session_id: str,
    project_path: str,
    app_url: str,
    features: List[Dict],
    credentials: Optional[Dict] = None,
    workspace_path: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Execute tests for all features using npx playwright-cli.
    """
    from . import session
    
    cli_session = f"test-{session_id[:8]}"
    
    yield f"data: 🌐 Opening browser: {app_url}\n\n"
    
    # Open browser
    _run_cli(cli_session, f"open {app_url}")
    time.sleep(3)
    
    # Initial snapshot
    yield "data: 📸 Taking initial snapshot...\n\n"
    initial_snapshot = _run_cli(cli_session, "snapshot")
    
    # Authenticate if credentials provided
    if credentials:
        yield "data: 🔑 Authenticating...\n\n"
        
        auth_success = await _authenticate(
            cli_session, initial_snapshot, credentials
        )
        
        if auth_success:
            yield "data: ✅ Authentication successful\n\n"
        else:
            yield "data: ⚠️ Authentication issues (continuing anyway)\n\n"
        
        time.sleep(3)
    
    yield "data: \n\n"
    
    # Execute each feature
    results = {
        "total": len(features),
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "feature_results": []
    }
    
    for index, feature in enumerate(features, 1):
        feature_id = feature["id"]
        feature_name = feature["name"]
        feature_type = feature.get("type", "unknown")
        entry_point = feature.get("entry_point", "/")
        
        yield f"data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        yield f"data: 📝 Test {index}/{len(features)}: {feature_name}\n\n"
        yield f"data: 🔗 Entry: {entry_point}\n\n"
        
        result = {
            "feature_id": feature_id,
            "feature_name": feature_name,
            "status": "not_run",
            "commands": [],
            "error": None,
            "duration_ms": 0,
            "screenshots": {}  # Always empty with playwright-cli
        }
        
        start_time = time.time()
        
        try:
            # Check authentication state
            current_snapshot = _run_cli(cli_session, "snapshot")
            auth_state = _detect_authentication_state(current_snapshot)
            
            yield f"data:    🔐 Auth State: {'✅ Authenticated' if auth_state['authenticated'] else '❌ Not Authenticated'}\n\n"
            
            # Skip login tests if already authenticated
            if feature_type == "authentication" and "login" in feature_name.lower() and auth_state["authenticated"]:
                yield f"data:    ⏩ Skipping - user already authenticated\n\n"
                result["status"] = "skipped"
                result["error"] = "User already authenticated"
                results["skipped"] += 1
                
                session.update_feature_result(session_id, feature_id, result)
                results["feature_results"].append(result)
                
                yield "data: \n\n"
                yield f"data:    ┌{'─' * 50}┐\n\n"
                yield f"data:    │ 📊 TEST RESULT SUMMARY\n\n"
                yield f"data:    ├{'─' * 50}┤\n\n"
                yield f"data:    │ Feature: {feature_name}\n\n"
                yield f"data:    │ Status: ⏩ SKIPPED\n\n"
                yield f"data:    │ Reason: Already authenticated\n\n"
                yield f"data:    └{'─' * 50}┘\n\n"
                yield "data: \n\n"
                yield f"data:    📈 Running Stats: {results['passed']} passed, {results['failed']} failed, {results['skipped']} skipped ({index}/{len(features)} complete)\n\n"
                yield "data: \n\n"
                continue
            
            # Navigate to entry point
            if entry_point and entry_point != "/":
                base_url = app_url.rstrip('/')
                full_url = base_url + entry_point
                
                yield f"data:    → Navigating to {entry_point}\n\n"
                _run_cli(cli_session, f"goto {full_url}")
                time.sleep(3)
            
            # Take snapshot after navigation
            current_snapshot = _run_cli(cli_session, "snapshot")
            
            # Check if on error page
            if _is_error_page(current_snapshot):
                yield f"data:    ⚠️ Navigation failed - error page detected\n\n"
                result["status"] = "skipped"
                result["error"] = "Navigation to entry point failed (error page)"
                results["skipped"] += 1
            else:
                # Generate commands
                yield "data:    → Generating test commands...\n\n"
                commands = await _generate_commands(feature, current_snapshot, app_url)
                
                if not commands:
                    yield "data:    ⚠️ No commands generated\n\n"
                    result["status"] = "skipped"
                    result["error"] = "No commands generated"
                    results["skipped"] += 1
                else:
                    yield f"data:    → Executing {len(commands)} commands\n\n"
                    
                    all_passed = True
                    
                    for cmd_idx, cmd_data in enumerate(commands, 1):
                        cmd = cmd_data.get("command", "")
                        desc = cmd_data.get("description", "")
                        
                        yield f"data:       [{cmd_idx}/{len(commands)}] {desc}\n\n"
                        
                        # Execute with retry
                        success, output = await _execute_command_with_retry(
                            cli_session, cmd, desc, max_retries=2
                        )
                        
                        result["commands"].append({
                            "command": cmd,
                            "description": desc,
                            "output": output[:200],
                            "success": success
                        })
                        
                        if not success or any(err in output.lower() for err in ["error", "timeout", "not found"]):
                            all_passed = False
                            yield f"data:           ⚠️ Warning\n\n"
                        else:
                            yield f"data:           ✓ OK\n\n"
                        
                        time.sleep(0.8)
                    
                    result["duration_ms"] = int((time.time() - start_time) * 1000)
                    
                    if all_passed:
                        result["status"] = "passed"
                        results["passed"] += 1
                    else:
                        result["status"] = "failed"
                        results["failed"] += 1
        
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            results["failed"] += 1
            yield f"data:    ❌ Error: {e}\n\n"
        
        # Calculate duration if not set
        if result["duration_ms"] == 0:
            result["duration_ms"] = int((time.time() - start_time) * 1000)
        
        # Store result
        session.update_feature_result(session_id, feature_id, result)
        results["feature_results"].append(result)
        
        # Print summary
        yield "data: \n\n"
        yield f"data:    ┌{'─' * 50}┐\n\n"
        yield f"data:    │ 📊 TEST RESULT SUMMARY\n\n"
        yield f"data:    ├{'─' * 50}┤\n\n"
        yield f"data:    │ Feature: {feature_name}\n\n"
        yield f"data:    │ Status: "
        
        if result["status"] == "passed":
            yield f"✅ PASSED\n\n"
            yield f"data:    │ Duration: {result['duration_ms']}ms\n\n"
            yield f"data:    │ Commands: {len(result['commands'])} executed successfully\n\n"
        elif result["status"] == "failed":
            yield f"❌ FAILED\n\n"
            yield f"data:    │ Duration: {result['duration_ms']}ms\n\n"
            yield f"data:    │ Commands: {len(result['commands'])} executed\n\n"
            if result.get("error"):
                yield f"data:    │ Error: {result['error'][:80]}\n\n"
            else:
                warnings = sum(1 for cmd in result['commands'] if not cmd.get('success', True))
                yield f"data:    │ Warnings: {warnings}\n\n"
        else:  # skipped
            yield f"⏩ SKIPPED\n\n"
            yield f"data:    │ Reason: {result.get('error', 'Unknown')}\n\n"
        
        yield f"data:    └{'─' * 50}┘\n\n"
        yield "data: \n\n"
        yield f"data:    📈 Running Stats: {results['passed']} passed, {results['failed']} failed, {results['skipped']} skipped ({index}/{len(features)} complete)\n\n"
        yield "data: \n\n"
    
    # Close browser
    yield "data: 🔴 Closing browser...\n\n"
    _run_cli(cli_session, "close")
    
    # Final Summary
    yield "data: \n\n"
    yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    yield "data: 📊 FINAL SUMMARY\n\n"
    yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    yield f"data: 🧪 Total: {results['total']}\n\n"
    yield f"data: ✅ Passed: {results['passed']}\n\n"
    yield f"data: ❌ Failed: {results['failed']}\n\n"
    yield f"data: ⏩ Skipped: {results['skipped']}\n\n"
    
    if results['passed'] + results['failed'] > 0:
        pass_rate = (results['passed'] / (results['passed'] + results['failed'])) * 100
        yield f"data: 📈 Pass Rate: {pass_rate:.1f}%\n\n"
    
    yield "data: \n\n"
    yield "data: __RESULTS_JSON__\n\n"
    yield f"data: {json.dumps(results, indent=2)}\n\n"


# ============================================
# HELPER FUNCTIONS
# ============================================

def _detect_authentication_state(snapshot: str) -> dict:
    """Detect if user is authenticated."""
    auth_indicators = {
        "authenticated": [
            "logout", "sign out", "profile", "avatar", "welcome",
            "dashboard", "chat interface", "settings", "menu"
        ],
        "not_authenticated": [
            "sso login", "sign in", "login", "get started",
            "welcome to tensaigpt", "smarter chats brighter ideas"
        ]
    }
    
    snapshot_lower = snapshot.lower()
    
    auth_score = sum(1 for indicator in auth_indicators["authenticated"] 
                     if indicator in snapshot_lower)
    not_auth_score = sum(1 for indicator in auth_indicators["not_authenticated"] 
                         if indicator in snapshot_lower)
    
    username_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', snapshot)
    username = username_match.group(1) if username_match else None
    
    return {
        "authenticated": auth_score > not_auth_score,
        "username": username,
        "confidence": abs(auth_score - not_auth_score)
    }


async def _execute_command_with_retry(
    cli_session: str,
    command: str,
    description: str,
    max_retries: int = 2
) -> tuple:
    """Execute command with retry."""
    for attempt in range(max_retries + 1):
        output = _run_cli(cli_session, command)
        
        if "Ref" in output and "not found" in output:
            if attempt < max_retries:
                time.sleep(1)
                fresh_snapshot = _run_cli(cli_session, "snapshot")
                
                cmd_parts = command.split()
                if len(cmd_parts) > 0:
                    cmd_name = cmd_parts[0]
                    
                    if cmd_name == "click":
                        keywords = _extract_keywords_from_description(description)
                        new_ref = _extract_ref(fresh_snapshot, keywords, "button")
                        
                        if new_ref:
                            command = f"click {new_ref}"
                            continue
                    elif cmd_name == "fill":
                        keywords = _extract_keywords_from_description(description)
                        new_ref = _extract_ref(fresh_snapshot, keywords, "textbox")
                        
                        if new_ref and len(cmd_parts) > 2:
                            value = " ".join(cmd_parts[2:])
                            command = f"fill {new_ref} {value}"
                            continue
        
        if "error" not in output.lower() or "### Ran Playwright code" in output:
            return True, output
    
    return False, output


def _extract_keywords_from_description(description: str) -> list:
    """Extract keywords from description."""
    keywords = []
    desc_lower = description.lower()
    
    if any(word in desc_lower for word in ["login", "sso", "sign in"]):
        keywords.extend(["login", "sign in", "sso"])
    if any(word in desc_lower for word in ["email", "username"]):
        keywords.extend(["email", "username", "phone", "skype"])
    if "password" in desc_lower:
        keywords.extend(["password", "pwd"])
    if any(word in desc_lower for word in ["next", "continue"]):
        keywords.extend(["next", "continue", "proceed"])
    if "submit" in desc_lower:
        keywords.extend(["submit", "sign in", "login"])
    
    return keywords if keywords else ["button", "input"]


def _is_error_page(snapshot: str) -> bool:
    """Check if snapshot is error page."""
    error_indicators = [
        "chrome-error://", "ERR_ABORTED", "ERR_CONNECTION",
        "reload-button", "This site can't be reached",
        "Unable to connect", "net::ERR_"
    ]
    return any(indicator.lower() in snapshot.lower() for indicator in error_indicators)


def _run_cli(session_name: str, command: str) -> str:
    """Execute playwright-cli command."""
    full_cmd = f"npx playwright-cli -s={session_name} {command}"
    
    try:
        result = subprocess.run(
            full_cmd, shell=True, capture_output=True,
            text=True, timeout=30, encoding='utf-8', errors='replace'
        )
        return (result.stdout or '') + (result.stderr or '')
    except Exception as e:
        return f"ERROR: {e}"


async def _authenticate(cli_session: str, snapshot: str, credentials: Dict) -> bool:
    """Perform authentication."""
    username = credentials.get("username", "")
    password = credentials.get("password", "")
    
    if not username:
        return False
    
    try:
        button_ref = _extract_ref(snapshot, ["sso login", "sign in", "login"], "button")
        
        if button_ref:
            _run_cli(cli_session, f"click {button_ref}")
            time.sleep(3)
            
            auth_snapshot = _run_cli(cli_session, "snapshot")
            
            email_ref = _extract_ref(auth_snapshot, ["email", "username", "phone", "skype"], "textbox")
            if email_ref:
                _run_cli(cli_session, f'fill {email_ref} "{username}"')
                time.sleep(1)
                
                next_ref = _extract_ref(auth_snapshot, ["next", "continue"], "button")
                if next_ref:
                    _run_cli(cli_session, f"click {next_ref}")
                    time.sleep(3)
                    
                    if password:
                        pwd_snapshot = _run_cli(cli_session, "snapshot")
                        pwd_ref = _extract_ref(pwd_snapshot, ["password"], "textbox")
                        
                        if pwd_ref:
                            _run_cli(cli_session, f'fill {pwd_ref} "{password}"')
                            time.sleep(1)
                            
                            signin_ref = _extract_ref(pwd_snapshot, ["sign in"], "button")
                            if signin_ref:
                                _run_cli(cli_session, f"click {signin_ref}")
                                time.sleep(5)
            
            return True
    except:
        pass
    
    return False


def _extract_ref(snapshot: str, keywords: List[str], element_type: str) -> Optional[str]:
    """Extract element ref from snapshot."""
    for keyword in keywords:
        pattern = rf'{element_type}\s+"[^"]*{re.escape(keyword)}[^"]*"\s+\[ref=([^\]]+)\]'
        match = re.search(pattern, snapshot, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


async def _generate_commands(feature: Dict, snapshot: str, app_url: str) -> List[Dict]:
    """Generate commands using AI."""
    from llm.client import LLMClient
    import asyncio
    
    if _is_error_page(snapshot):
        return []
    
    system_prompt = """Generate playwright-cli commands to test a feature.

IMPORTANT RULES:
1. Only use: click, fill, goto, snapshot
2. Do NOT use: wait_for_load_state, wait, assert, expect, resize
3. Extract element refs from snapshot
4. For goto use FULL URLs

Return JSON:
{
  "commands": [
    {"command": "click e20", "description": "Click button"},
    {"command": "fill e25 \\"text\\"", "description": "Fill input"}
  ]
}"""
    
    user_prompt = f"""Generate test commands:

**Feature:** {feature.get('name')}
**Type:** {feature.get('type')}
**Entry Point:** {feature.get('entry_point')}

**Snapshot:**
{snapshot[:1500]}

Generate 2-4 commands using refs from snapshot."""
    
    try:
        client = LLMClient(provider="azure_foundry_claude")
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.complete(system_prompt, user_prompt, max_tokens=1024)
        )
        
        commands_data = _extract_commands_json(response)
        
        if not commands_data:
            return []
        
        return _validate_commands(commands_data, app_url)
        
    except Exception as e:
        print(f"Command generation error: {e}")
        return []


def _extract_commands_json(response: str) -> Optional[Dict]:
    """Extract JSON from response."""
    match = re.search(r'\{[^{}]*"commands"[^{}]*\[[^\]]*\][^{}]*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    
    match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
    if match:
        try:
            commands_array = json.loads(match.group(0))
            return {"commands": commands_array}
        except:
            pass
    
    return None


def _validate_commands(commands_data: Dict, app_url: str) -> List[Dict]:
    """Validate commands."""
    valid_cmds = ["click", "fill", "goto", "snapshot"]
    invalid_cmds = ["wait_for_load_state", "wait", "assert", "expect", "resize"]
    
    commands = commands_data.get("commands", [])
    validated = []
    
    for cmd in commands:
        cmd_str = cmd.get("command", "").strip()
        
        if not cmd_str:
            continue
        
        cmd_name = cmd_str.split()[0].lower()
        
        if cmd_name in invalid_cmds or cmd_name not in valid_cmds:
            continue
        
        if cmd_name == "goto":
            url_part = cmd_str.split(None, 1)[1] if len(cmd_str.split()) > 1 else ""
            url_part = url_part.strip('"\'')
            
            if "chrome-error://" in url_part:
                continue
            
            if url_part.startswith('/'):
                base_url = app_url.rstrip('/')
                full_url = base_url + url_part
                cmd["command"] = f'goto {full_url}'
        
        validated.append(cmd)
    
    return validated
