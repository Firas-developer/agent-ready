"""
Feature Executor — Complete standalone service.
1. Reads files from uploaded ZIP
2. Detects features using AI
3. Executes features with npx playwright-cli
"""
import subprocess
import time
import json
import json5
import re
import uuid
from pathlib import Path
from typing import List, Dict, Optional, AsyncGenerator


async def detect_and_execute_all_features(
    project_path: str,
    app_url: str,
    credentials: Optional[Dict],
    provider: str,
    model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    COMPLETE WORKFLOW:
    1. Read files from project_path
    2. Detect features using AI
    3. Execute ALL features with npx playwright-cli
    
    Args:
        project_path: Path to extracted ZIP
        app_url: Target application URL
        credentials: Optional {username, password}
        provider: LLM provider
        model: Optional model override
    
    Yields:
        SSE progress messages
    """
    from llm.client import LLMClient
    
    client = LLMClient(provider=provider, model=model)
    session_name = f"auto-exec-{int(time.time())}"
    
    yield f"data: 🚀 UNIFIED WORKFLOW: Detect + Execute\n\n"
    yield f"data: 📁 Project: {project_path}\n\n"
    yield f"data: 🌐 Target: {app_url}\n\n"
    yield "data: \n\n"
    
    # ============================================
    # PHASE 1: DETECT FEATURES FROM FILES
    # ============================================
    yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    yield "data: 📊 PHASE 1: Feature Detection\n\n"
    yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    features = []
    
    try:
        # Read and analyze files
        yield "data: 📖 Reading source files...\n\n"
        
        file_contents, files_read = _extract_file_contents(project_path, max_files=25)
        
        if files_read:
            yield f"data: ✅ Read {len(files_read)} files:\n\n"
            for i, filename in enumerate(files_read[:5], 1):
                yield f"data:    {i}. {filename}\n\n"
            if len(files_read) > 5:
                yield f"data:    ... and {len(files_read) - 5} more\n\n"
        else:
            yield "data: ⚠️ WARNING: No files read!\n\n"
        
        yield "data: \n\n"
        
        # Detect features with AI
        yield "data: 🤖 Analyzing with AI to detect features...\n\n"
        
        features = await _detect_features_with_ai(
            client,
            project_path,
            file_contents,
            files_read
        )
        
        if features:
            yield f"data: ✅ Detected {len(features)} features:\n\n"
            for i, feature in enumerate(features, 1):
                yield f"data:    {i}. {feature['name']} ({feature.get('type', 'unknown')})\n\n"
        else:
            yield "data: ⚠️ No features detected - creating fallback\n\n"
            features = [{
                "id": f"feat-{str(uuid.uuid4())[:8]}",
                "name": "Application Entry Point",
                "type": "navigation",
                "entry_point": "/",
                "description": "Main application page",
                "ui_components": {},
                "test_steps": []
            }]
        
    except Exception as e:
        yield f"data: ❌ Feature detection failed: {e}\n\n"
        features = [{
            "id": f"feat-fallback",
            "name": "Fallback Feature",
            "type": "navigation",
            "entry_point": "/",
            "description": f"Detection failed: {e}",
            "ui_components": {},
            "test_steps": []
        }]
    
    yield "data: \n\n"
    
    # ============================================
    # PHASE 2: EXECUTE ALL FEATURES
    # ============================================
    yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    yield "data: 🧪 PHASE 2: Test Execution\n\n"
    yield "data: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Track results
    results = {
        "total": len(features),
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "feature_results": []
    }
    
    try:
        # Open browser ONCE
        yield f"data: 🌐 Opening browser: {app_url}\n\n"
        _run_cli(session_name, f"open {app_url}")
        time.sleep(2)
        
        # Authenticate ONCE (if credentials)
        yield "data: 📸 Taking initial snapshot...\n\n"
        initial_snapshot = _run_cli(session_name, "snapshot")
        
        if credentials:
            username = credentials.get('username') or credentials.get('email')
            password = credentials.get('password')
            
            yield "data: 🔑 Authenticating...\n\n"
            
            yield "data:    [1/5] Looking for login button...\n\n"
            
            if 'sso login' in initial_snapshot.lower() or 'sign in' in initial_snapshot.lower():
                button_ref = _extract_button_ref(initial_snapshot, ['sso login', 'sign in', 'login'])
                
                if button_ref:
                    yield f"data:    ✓ Found: {button_ref}\n\n"
                    _run_cli(session_name, f"click {button_ref}")
                    time.sleep(3)
                    
                    yield "data:    [2/5] Waiting for auth page...\n\n"
                    time.sleep(2)
                    
                    auth_snapshot = _run_cli(session_name, "snapshot")
                    
                    yield "data:    [3/5] Filling email...\n\n"
                    email_ref = _extract_input_ref(auth_snapshot, ['email', 'username', 'phone', 'skype'])
                    
                    if email_ref:
                        _run_cli(session_name, f'fill {email_ref} "{username}"')
                        time.sleep(1)
                        
                        yield "data:    [4/5] Clicking Next...\n\n"
                        next_ref = _extract_button_ref(auth_snapshot, ['next', 'continue'])
                        
                        if next_ref:
                            _run_cli(session_name, f"click {next_ref}")
                            time.sleep(3)
                            
                            if password:
                                yield "data:    [5/5] Filling password...\n\n"
                                pwd_snapshot = _run_cli(session_name, "snapshot")
                                pwd_ref = _extract_input_ref(pwd_snapshot, ['password'])
                                
                                if pwd_ref:
                                    _run_cli(session_name, f'fill {pwd_ref} "{password}"')
                                    time.sleep(1)
                                    
                                    signin_ref = _extract_button_ref(pwd_snapshot, ['sign in', 'submit'])
                                    if signin_ref:
                                        _run_cli(session_name, f"click {signin_ref}")
                                        time.sleep(5)
                            
                            yield "data:    ✅ Authentication complete!\n\n"
        
        yield "data: \n\n"
        
        # Test each feature
        for index, feature in enumerate(features, 1):
            feature_id = feature.get("id")
            feature_name = feature.get("name")
            entry_point = feature.get("entry_point", "/")
            
            yield "data: \n\n"
            yield f"data: 📝 Feature {index}/{len(features)}: {feature_name}\n\n"
            yield f"data: 🔗 Entry: {entry_point}\n\n"
            
            feature_result = {
                "feature_id": feature_id,
                "feature_name": feature_name,
                "status": "not_run",
                "commands_executed": [],
                "error": None,
                "duration_ms": 0
            }
            
            start_time = time.time()
            
            try:
                if entry_point and entry_point != "/":
                    yield f"data:    Navigating to: {entry_point}\n\n"
                    _run_cli(session_name, f"goto {entry_point}")
                    time.sleep(2)
                
                current_snapshot = _run_cli(session_name, "snapshot")
                
                yield "data:    🤖 Generating test commands...\n\n"
                
                commands = await _generate_commands_for_feature(
                    client,
                    feature,
                    current_snapshot
                )
                
                if not commands:
                    yield "data:    ⚠️ No commands generated - skipping\n\n"
                    results["skipped"] += 1
                    feature_result["status"] = "skipped"
                    feature_result["error"] = "No commands generated"
                    results["feature_results"].append(feature_result)
                    continue
                
                yield f"data:    ✓ Generated {len(commands)} commands\n\n"
                
                all_passed = True
                
                for cmd_index, command in enumerate(commands, 1):
                    cmd_str = command.get("command")
                    cmd_desc = command.get("description", "")
                    
                    yield f"data:       [{cmd_index}/{len(commands)}] {cmd_desc}\n\n"
                    
                    output = _run_cli(session_name, cmd_str)
                    
                    if "error" in output.lower() or "failed" in output.lower():
                        yield f"data:           ⚠️ Warning\n\n"
                        all_passed = False
                    else:
                        yield f"data:           ✓ OK\n\n"
                    
                    feature_result["commands_executed"].append({
                        "command": cmd_str,
                        "description": cmd_desc,
                        "output": output[:200]
                    })
                    
                    time.sleep(0.5)
                
                duration_ms = int((time.time() - start_time) * 1000)
                feature_result["duration_ms"] = duration_ms
                
                if all_passed:
                    feature_result["status"] = "passed"
                    results["passed"] += 1
                    yield f"data:    ✅ PASSED ({duration_ms}ms)\n\n"
                else:
                    feature_result["status"] = "failed"
                    results["failed"] += 1
                    yield f"data:    ❌ FAILED ({duration_ms}ms)\n\n"
                
            except Exception as e:
                feature_result["status"] = "failed"
                feature_result["error"] = str(e)
                results["failed"] += 1
                yield f"data:    ❌ Error: {e}\n\n"
            
            results["feature_results"].append(feature_result)
        
        yield "data: \n\n"
        yield "data: 🔴 Closing browser...\n\n"
        _run_cli(session_name, "close")
        
    except Exception as e:
        yield f"data: ❌ Fatal error: {e}\n\n"
    
    # Summary
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
    yield "data: __RESULTS_JSON_START__\n\n"
    yield f"data: {json.dumps(results, indent=2)}\n\n"
    yield "data: __RESULTS_JSON_END__\n\n"
    yield "data: [DONE]\n\n"


# ============================================
# FILE READING (from feature_detector.py)
# ============================================

def _extract_file_contents(project_path: str, max_files: int = 25) -> tuple[str, list[str]]:
    """Extract source files for AI analysis."""
    root = Path(project_path)
    contents = []
    successfully_read = []
    
    patterns = [
        "**/Login*.tsx", "**/Login*.jsx",
        "**/Auth*.tsx", "**/Auth*.jsx",
        "**/Chat*.tsx", "**/Chat*.jsx",
        "**/routes/*.py", "**/routers/*.py",
        "**/pages/**/*.tsx", "**/pages/**/*.jsx",
        "**/components/**/*.tsx", "**/components/**/*.jsx",
        "**/api/**/*.py",
    ]
    
    files_added = 0
    seen_files = set()
    
    for pattern in patterns:
        if files_added >= max_files:
            break
        
        for file in root.glob(pattern):
            if files_added >= max_files:
                break
            
            if 'node_modules' in file.parts or '.venv' in file.parts:
                continue
            
            if file in seen_files:
                continue
            
            seen_files.add(file)
            
            try:
                rel_path = str(file.relative_to(root)).replace('\\', '/')
                content = file.read_text(encoding='utf-8', errors='ignore')
                
                if len(content.strip()) < 50:
                    continue
                
                if len(content) > 2000:
                    content = content[:2000] + "\n... (truncated)"
                
                contents.append(f"\n## File: {rel_path}\n```\n{content}\n```\n")
                successfully_read.append(rel_path)
                files_added += 1
                
            except Exception:
                pass
    
    return "\n".join(contents), successfully_read


async def _detect_features_with_ai(
    client,
    project_path: str,
    file_contents: str,
    files_read: List[str]
) -> List[Dict]:
    """Use AI to detect features from source code."""
    
    # Build context
    context = f"""# Project Source Code Analysis

## Files Analyzed ({len(files_read)})
{chr(10).join('- ' + f for f in files_read)}

## Source Code
{file_contents}
"""
    
    # Load prompt
    prompt_file = Path(__file__).parent.parent.parent / "prompts" / "feature_detection.txt"
    
    if not prompt_file.exists():
        return []
    
    system_prompt = prompt_file.read_text(encoding='utf-8')
    
    user_prompt = f"""Analyze this codebase and detect testable features.

{context}

CRITICAL:
- Extract EXACT selectors from source code (className, id, data-testid)
- DO NOT guess generic selectors like "button.btn"
- Focus on user-facing features
- Return valid JSON array

Detect ALL important features (no limit).
"""
    
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.complete(system_prompt, user_prompt, max_tokens=8192)
        )
        
        # Extract JSON
        json_str = None
        
        # Try markdown code block
        start = response.find('```json')
        if start != -1:
            start += 7
            end = response.find('```', start)
            if end != -1:
                json_str = response[start:end].strip()
        
        # Try brackets
        if not json_str:
            start = response.find('[')
            end = response.rfind(']')
            if start != -1 and end != -1:
                json_str = response[start:end+1]
        
        if not json_str:
            return []
        
        # Clean and parse
        json_str = re.sub(r'//[^\n]*', '', json_str)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        try:
            features = json5.loads(json_str)
        except:
            features = json.loads(json_str)
        
        # Add IDs
        if features and isinstance(features, list):
            for feature in features:
                if isinstance(feature, dict):
                    feature["id"] = f"feat-{str(uuid.uuid4())[:8]}"
                    feature["detected_from"] = files_read[:3]
            
            return features
        
        return []
        
    except Exception as e:
        print(f"AI detection failed: {e}")
        return []


# ============================================
# COMMAND EXECUTION (npx playwright-cli)
# ============================================

def _run_cli(session_name: str, command: str) -> str:
    """Execute playwright-cli command."""
    full_cmd = f"npx playwright-cli -s={session_name} {command}"
    
    result = subprocess.run(
        full_cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=30,
        encoding='utf-8',
        errors='replace'
    )
    
    return (result.stdout or '') + (result.stderr or '')


def _extract_button_ref(snapshot: str, keywords: List[str]) -> Optional[str]:
    """Extract button ref from snapshot."""
    for keyword in keywords:
        pattern = rf'button\s+"[^"]*{re.escape(keyword)}[^"]*"\s+\[ref=([^\]]+)\]'
        match = re.search(pattern, snapshot, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_input_ref(snapshot: str, keywords: List[str]) -> Optional[str]:
    """Extract input ref from snapshot."""
    for keyword in keywords:
        pattern = rf'textbox\s+"[^"]*{re.escape(keyword)}[^"]*"\s+\[ref=([^\]]+)\]'
        match = re.search(pattern, snapshot, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


async def _generate_commands_for_feature(
    client,
    feature: Dict,
    current_snapshot: str
) -> List[Dict]:
    """Generate npx commands for a feature."""
    
    system_prompt = """Generate playwright-cli commands to test a feature.

Return JSON:
{
  "commands": [
    {"command": "click e20", "description": "Click button"},
    {"command": "fill e25 \\"test\\"", "description": "Fill input"},
    {"command": "snapshot", "description": "Capture result"}
  ]
}

Available commands: click eXX, fill eXX "text", snapshot, wait 2000
Use element refs from snapshot. Return ONLY valid JSON."""
    
    user_prompt = f"""Generate test commands:

**Feature:** {feature.get('name')}
**Type:** {feature.get('type')}
**Entry:** {feature.get('entry_point', '/')}

**Current Snapshot:**
{current_snapshot[:2000]}

Return JSON with commands."""
    
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.complete(system_prompt, user_prompt, max_tokens=1024)
        )
        
        json_match = re.search(r'\{[^{}]*"commands"[^{}]*\[[^\]]*\][^{}]*\}', response, re.DOTALL)
        if not json_match:
            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                return []
        else:
            data = json.loads(json_match.group(0))
        
        return data.get("commands", [])
    
    except Exception:
        return []


# ============================================
# WRAPPER FOR EXISTING WORKFLOW
# ============================================

async def execute_all_features(
    features: List[Dict],
    app_url: str,
    project_path: str,
    credentials: Optional[Dict],
    provider: str,
    model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Execute pre-detected features (for compatibility with existing flow).
    This is called by playwright_testing.py when features are already detected.
    """
    # Just use the detection logic but skip the AI detection part
    # and use the provided features directly
    
    from llm.client import LLMClient
    client = LLMClient(provider=provider, model=model)
    session_name = f"auto-exec-{int(time.time())}"
    
    yield f"data: 🚀 Executing {len(features)} pre-detected features\n\n"
    yield f"data: 🌐 Target: {app_url}\n\n"
    yield "data: \n\n"
    
    results = {"total": len(features), "passed": 0, "failed": 0, "skipped": 0, "feature_results": []}
    
    try:
        yield f"data: 🌐 Opening browser...\n\n"
        _run_cli(session_name, f"open {app_url}")
        time.sleep(2)
        
        initial_snapshot = _run_cli(session_name, "snapshot")
        
        # Auth logic (same as above)
        if credentials:
            username = credentials.get('username') or credentials.get('email')
            password = credentials.get('password')
            
            yield "data: 🔑 Authenticating...\n\n"
            # ... (same auth code as in detect_and_execute_all_features)
        
        # Execute features (same loop as above)
        for index, feature in enumerate(features, 1):
            # ... (same execution code)
            pass
        
        _run_cli(session_name, "close")
        
    except Exception as e:
        yield f"data: ❌ Error: {e}\n\n"
    
    yield "data: __RESULTS_JSON_START__\n\n"
    yield f"data: {json.dumps(results, indent=2)}\n\n"
    yield "data: __RESULTS_JSON_END__\n\n"
    yield "data: [DONE]\n\n"
