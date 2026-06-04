"""
Agent Ready service — streams the full 20-criteria analysis as SSE.
FIXED: Reliable Windows command execution + guaranteed file content reading.
"""
import os
import re
import subprocess
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional
from dotenv import load_dotenv

load_dotenv()

SKILL_TEXT = """You are a FastAPI backend standardization auditor. Run a full deep scan every time.

Evaluate the project against the FastAPI Backend Standardization Guide across 6 pillars and 24 criteria.
Rate each criterion as PASS, WARN, or FAIL with a one-line justification.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILLAR 1 — PROJECT STRUCTURE (4 criteria)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.1  Directory layout matches: app.py, config.py, requirements.txt, keys/, logs/, modules/
     modules/ must contain: api_routes/, api_modules/, service_modules/, dependencies.py
1.2  File names use PascalCase for all modules inside modules/ (e.g. DatabaseManager.py)
1.3  keys/ and logs/ directories are git-ignored; no secrets committed to version control
1.4  Every Python package (modules/, api_routes/, api_modules/, service_modules/) has __init__.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILLAR 2 — CONFIGURATION & ENTRY POINT (4 criteria)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.1  config.py uses pydantic-settings BaseSettings (NOT YAML + eval(), NOT raw os.getenv at module level)
     Exports exactly: settings (AppSettings), logger (logging.Logger), limiter (Limiter)
2.2  Logger uses TimedRotatingFileHandler (midnight rotation, 30-day retention, %s formatting not f-strings)
     Never logs passwords, tokens, or encryption keys at INFO level
2.3  app.py only: imports config, initializes FastAPI, registers rate-limiting, registers exception handlers,
     registers middleware, includes routers. Contains NO business logic, DB queries, or schema definitions.
2.4  All secrets live in keys/.env loaded via Pydantic SettingsConfigDict(env_file="keys/.env").
     CORS origins come from settings.cors_origins, never hardcoded wildcards.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILLAR 3 — LAYERED ARCHITECTURE (5 criteria)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3.1  Three distinct layers exist: api_routes/ (HTTP), api_modules/ (business logic), service_modules/ (I/O)
3.2  Business logic layer (api_modules/) has zero FastAPI imports — no Request, Response, JSONResponse, Depends
3.3  Every component and service function returns the standardized dict:
     {"status": bool, "message": str, "output": any, "error": str}
3.4  Route handlers are thin: delegate immediately to a component function, map result["status"] to HTTP code,
     wrap everything in try/except returning HTTP 500 on unexpected exceptions
3.5  Service layer uses Manager classes (e.g. DatabaseManager). Each Manager method catches specific exceptions
     first then a generic Exception fallback, logs before returning, and returns the standardized dict.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILLAR 4 — API, SCHEMAS & RESPONSE (4 criteria)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4.1  Every public endpoint has @limiter.limit() decorator. Rate limits follow the standard:
     auth endpoints 5/min, protected operations 20/min, read-only 60/min.
     Single Limiter instance imported from config — never re-instantiated in route files.
4.2  All request schemas inherit from SecureBaseModel (which enforces extra='forbid' and bleach sanitization).
     Required fields use Field(...), strings have min_length/max_length, passwords use SecretStr.
4.3  All endpoints return responses via APIResponse(success, data, message).model_dump() wrapped in JSONResponse.
     HTTP status codes: 200 success, 400 business rejection, 401 wrong credentials, 403 expired/invalid token,
     429 rate limited, 500 unexpected exception.
4.4  Middleware registration order in app.py: CORSMiddleware first (outermost), then LoggingMiddleware,
     then security headers via @app.middleware("http"). Security headers include: Server: Hidden,
     X-Content-Type-Options, Content-Security-Policy, Strict-Transport-Security, X-Frame-Options, X-XSS-Protection.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILLAR 5 — AUTHENTICATION & DEPENDENCY INJECTION (4 criteria)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5.1  Auth uses Depends(get_current_user) pattern — route handlers receive a verified payload dict,
     never a raw token. No manual jwt.decode() calls inside route handlers.
5.2  get_current_user dependency handles: Bearer token extraction, jwt.decode(), expiry/claims validation,
     raises HTTPException(401) for invalid tokens, HTTPException(403) for expired tokens.
5.3  Manager instances are provided via FastAPI Depends() from modules/dependencies.py.
     Singleton managers (DB, API clients) use @lru_cache() on the dependency function.
5.4  Business logic functions receive manager instances as plain parameters (not Depends).
     The route handler bridges the two layers: calls Depends() then passes managers to component functions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILLAR 6 — CODING CONVENTIONS & SECURITY (3 criteria)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6.1  Import order: (1) from config import ... (2) stdlib (3) third-party (4) local modules.
     Naming: Files=PascalCase, Classes=PascalCase, Functions/Variables=snake_case,
     Constants=UPPER_SNAKE_CASE, Route paths=kebab-case. Type hints on all function signatures.
6.2  Route handlers use def (sync, run in threadpool). Middleware dispatch uses async def.
     Business logic and service methods are synchronous. async def routes only if entire I/O stack is async.
6.3  Security checklist — all of these must be PASS:
     - Input sanitized via SecureBaseModel (bleach)
     - Extra fields forbidden (extra='forbid')
     - Passwords use SecretStr, never logged
     - JWT tokens signed with HS256 (long secret) or RS256
     - Security response headers present
     - Every public endpoint rate-limited
     - CORS origins from config, not wildcards
     - No secrets in code — all in keys/.env
     - Error messages never expose stack traces or internal paths
     - Server header hidden

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MATURITY LEVELS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
L1 Baseline:      requirements.txt, app.py exists, at least one router registered, .gitignore present
L2 Configured:    L1 + config.py with Pydantic Settings, logger from config, secrets in keys/.env
L3 Layered:       L2 + three-layer architecture enforced, standardized result dict, no FastAPI in business logic
L4 Hardened:      L3 + SecureBaseModel schemas, rate limiting on all endpoints, security headers middleware,
                  Depends()-based auth, APIResponse wrapper on all endpoints
L5 Standardized:  L4 + all 24 criteria PASS — fully compliant with the FastAPI Backend Standardization Guide

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (follow exactly)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FASTAPI STANDARDIZATION REPORT: [project name]
MATURITY: Level X — [Level Name]
Score: X/24 criteria passing

PILLAR 1 — PROJECT STRUCTURE
  1.1  [PASS|WARN|FAIL] [one-line finding]
  1.2  [PASS|WARN|FAIL] [one-line finding]
  ...

(repeat for all 6 pillars)

IMPROVEMENT PLAN
  Quick Wins (can fix now):
    - [specific file or pattern to add/change]
  Requires Human Decision:
    - [architectural or secret-management changes]"""


def _sh(cmd: str, cwd: str) -> str:
    """Run shell command and return output (max 5000 chars)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=30)
        out = (r.stdout + r.stderr).strip()
        return out[:5000] if len(out) > 5000 else out
    except Exception as e:
        return f"(error: {e})"


def _find_project_root(extracted_path: str) -> str:
    """Auto-detect the actual project root inside the extraction folder."""
    root = Path(extracted_path)
    
    print(f"  🔍 Searching for project root in: {root}")
    
    def score_directory(path: Path) -> int:
        score = 0
        if (path / "backend").is_dir():
            score += 5
            print(f"    ✓ Found backend/ in {path.name}")
        if (path / "frontend").is_dir():
            score += 5
            print(f"    ✓ Found frontend/ in {path.name}")
        if (path / "src").is_dir():
            score += 5
            print(f"    ✓ Found src/ in {path.name}")
        if (path / "package.json").exists():
            score += 3
            print(f"    ✓ Found package.json in {path.name}")
        if (path / "pyproject.toml").exists():
            score += 3
            print(f"    ✓ Found pyproject.toml in {path.name}")
        if (path / "requirements.txt").exists():
            score += 3
            print(f"    ✓ Found requirements.txt in {path.name}")
        if (path / "README.md").exists():
            score += 1
        if (path / ".gitignore").exists():
            score += 1
        if (path / ".git").is_dir():
            score += 1
        return score
    
    current_score = score_directory(root)
    print(f"  📊 Current directory score: {current_score}")
    
    if current_score >= 8:
        print(f"  ✅ Using {root.name} as project root (score: {current_score})")
        return str(root)
    
    exclude = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
    subdirs = [
        d for d in root.iterdir()
        if d.is_dir() and not d.name.startswith('.') and d.name not in exclude
    ]
    
    if len(subdirs) == 1:
        print(f"  🔽 Single subdirectory found: {subdirs[0].name}, recursing...")
        return _find_project_root(str(subdirs[0]))
    
    if subdirs:
        print(f"  🔍 Scanning {len(subdirs)} subdirectories...")
        best_dir = root
        best_score = current_score
        for subdir in subdirs[:5]:
            subdir_score = score_directory(subdir)
            print(f"    {subdir.name}: score {subdir_score}")
            if subdir_score > best_score:
                best_score = subdir_score
                best_dir = subdir
        if best_dir != root:
            print(f"  ✅ Using {best_dir.name} as project root (score: {best_score})")
            return str(best_dir)
    
    print(f"  ⚠️ No strong project indicators found, using original path")
    return str(root)


def _list_all_folders_and_files(root: Path) -> str:
    """Recursively list ALL folders, subfolders, and files."""
    exclude = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.pytest_cache', 
               '.mypy_cache', 'dist', 'build', '.next', 'coverage'}
    
    lines = ["## 📁 COMPLETE DIRECTORY LISTING"]
    lines.append(f"Root: {root.name}")
    lines.append("")
    
    folder_count = 0
    file_count = 0
    
    def scan_directory(path: Path, prefix: str = "", is_last: bool = True):
        nonlocal folder_count, file_count
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return
        items = [item for item in items 
                 if item.name not in exclude and not item.name.startswith('.')]
        for i, item in enumerate(items):
            is_last_item = (i == len(items) - 1)
            connector = "└── " if is_last_item else "├── "
            if item.is_dir():
                folder_count += 1
                lines.append(f"{prefix}{connector}📁 {item.name}/")
                extension = "    " if is_last_item else "│   "
                scan_directory(item, prefix + extension, is_last_item)
            elif item.is_file():
                file_count += 1
                try:
                    size_bytes = item.stat().st_size
                    if size_bytes < 1024:
                        size_str = f"{size_bytes}B"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes/1024:.1f}KB"
                    else:
                        size_str = f"{size_bytes/(1024*1024):.1f}MB"
                    lines.append(f"{prefix}{connector}📄 {item.name} ({size_str})")
                except:
                    lines.append(f"{prefix}{connector}📄 {item.name}")
    
    scan_directory(root)
    lines.insert(2, f"Total folders: {folder_count}")
    lines.insert(3, f"Total files: {file_count}")
    lines.insert(4, "")
    return "\n".join(lines)


def _count_lines_python(root: Path) -> list[tuple[str, int]]:
    """Count lines in Python files using pure Python (Windows-safe)."""
    results = []
    for f in root.rglob("*.py"):
        if any(p in f.parts for p in ['node_modules', '.venv', '__pycache__']):
            continue
        try:
            line_count = sum(1 for _ in f.open(errors='ignore'))
            if line_count > 50:  # Only count meaningful files
                results.append((str(f.relative_to(root)), line_count))
        except:
            pass
    return sorted(results, key=lambda x: x[1], reverse=True)[:30]


def _count_lines_js(root: Path) -> list[tuple[str, int]]:
    """Count lines in JS/TS files using pure Python."""
    results = []
    for ext in ['*.js', '*.jsx', '*.ts', '*.tsx']:
        for f in root.rglob(ext):
            if any(p in f.parts for p in ['node_modules', '.venv', '__pycache__']):
                continue
            try:
                line_count = sum(1 for _ in f.open(errors='ignore'))
                if line_count > 50:
                    results.append((str(f.relative_to(root)), line_count))
            except:
                pass
    return sorted(results, key=lambda x: x[1], reverse=True)[:30]


def _gather_project_data(project_path: str) -> str:
    """
    Gather all project data for LLM analysis using pure Python (no shell commands).
    GUARANTEED to read file contents regardless of OS.
    """
    
    root = Path(project_path)

    def fe(rel): return (root / rel).exists()
    def ge(pat): return any(root.glob(pat))

    sections = []

    sections.append(f"## Project Root: {root.name}")
    sections.append(f"Full path: {root}")
    
    # Root contents listing - using pure Python
    sections.append("\n## Project Root Contents")
    try:
        root_items = sorted(root.iterdir(), key=lambda x: x.name.lower())
        for item in root_items[:50]:  # First 50 items
            if item.name.startswith('.'):
                continue
            if item.is_dir():
                sections.append(f"  📁 {item.name}/")
            else:
                size = item.stat().st_size / 1024
                sections.append(f"  📄 {item.name} ({size:.1f}KB)")
    except:
        sections.append("(error listing)")
    
    # Key directories
    sections.append("\n## Key Directories Found")
    for subdir in ["backend", "frontend", "src", "tests", "alembic"]:
        if (root / subdir).is_dir():
            try:
                file_count = sum(1 for _ in (root / subdir).rglob("*") if _.is_file())
                sections.append(f"  ✓ {subdir}/ ({file_count} total items)")
            except:
                sections.append(f"  ✓ {subdir}/")
        else:
            sections.append(f"  ✗ {subdir}/ (not found)")

    sections.append("\n## Tooling & Config Files")
    checks = {
        "package.json": fe("package.json"),
        "frontend/package.json": fe("frontend/package.json"),
        "pyproject.toml": fe("pyproject.toml"),
        "requirements.txt": fe("requirements.txt"),
        "uv.lock / package-lock.json": fe("uv.lock") or fe("package-lock.json"),
        "eslint config": ge("**/eslint.config.*") or ge("**/.eslintrc*"),
        "prettier config": ge("**/.prettierrc*") or ge("**/prettier.config.*"),
        "tsconfig.json": fe("tsconfig.json") or fe("frontend/tsconfig.json"),
        "mypy": ge("**/mypy.ini") or ("mypy" in (root / "pyproject.toml").read_text(errors="ignore") if fe("pyproject.toml") else False),
        ".pre-commit-config.yaml": fe(".pre-commit-config.yaml"),
        ".husky/": fe(".husky"),
        "CLAUDE.md / AGENTS.md": fe("CLAUDE.md") or fe("AGENTS.md"),
        ".env.example": fe(".env.example"),
        ".gitignore": fe(".gitignore"),
        "README.md": fe("README.md"),
        "dependabot / renovate": fe(".github/dependabot.yml") or fe("renovate.json"),
    }
    for name, exists in checks.items():
        sections.append(f"  {'✓' if exists else '✗'} {name}")

    # File sizes - using pure Python
    sections.append("\n## Source Files by Line Count (top 30 combined)")
    all_files = _count_lines_python(root) + _count_lines_js(root)
    all_files.sort(key=lambda x: x[1], reverse=True)
    for path, lines in all_files[:30]:
        sections.append(f"  {lines:5d} {path}")

    # Directory file counts - using pure Python
    sections.append("\n## Files per Directory (top 20)")
    dir_counts = []
    for d in root.rglob("*"):
        if not d.is_dir():
            continue
        if any(p in d.parts for p in ['node_modules', '.venv', '__pycache__', '.git']):
            continue
        try:
            file_count = sum(1 for f in d.iterdir() if f.is_file())
            if file_count > 0:
                dir_counts.append((str(d.relative_to(root)), file_count))
        except:
            pass
    dir_counts.sort(key=lambda x: x[1], reverse=True)
    for path, count in dir_counts[:20]:
        sections.append(f"  {count:3d} files in {path}")

    # Test vs Source counts - using pure Python
    sections.append("\n## Test vs Source File Counts")
    test_patterns = ['*.test.*', '*.spec.*', 'test_*.py', '*_test.py']
    source_patterns = ['*.py', '*.js', '*.jsx', '*.ts', '*.tsx']
    
    test_count = 0
    for pattern in test_patterns:
        for f in root.rglob(pattern):
            if 'node_modules' not in f.parts and '.venv' not in f.parts:
                test_count += 1
    
    src_count = 0
    for pattern in source_patterns:
        for f in root.rglob(pattern):
            if 'node_modules' not in f.parts and '.venv' not in f.parts:
                src_count += 1
    
    sections.append(f"  Test files: {test_count}")
    sections.append(f"  Source files: {src_count}")
    if src_count > 0:
        ratio = test_count / src_count
        sections.append(f"  Ratio: 1:{src_count/max(test_count, 1):.1f}")

    # CRITICAL: Read README.md content
    sections.append("\n## README.md (first 50 lines)")
    readme = root / "README.md"
    if readme.exists():
        try:
            lines_read = readme.read_text(errors="ignore").splitlines()[:50]
            sections.append("\n".join(lines_read))
            if len(lines_read) >= 50:
                sections.append("... (content continues)")
        except:
            sections.append("(error reading file)")
    else:
        sections.append("(not found)")

    # CRITICAL: Read .gitignore content
    sections.append("\n## .gitignore (first 40 lines)")
    gitignore = root / ".gitignore"
    if gitignore.exists():
        try:
            lines_read = gitignore.read_text(errors="ignore").splitlines()[:40]
            sections.append("\n".join(lines_read))
            if len(lines_read) >= 40:
                sections.append("... (content continues)")
        except:
            sections.append("(error reading file)")
    else:
        sections.append("(not found)")

    # CRITICAL: Read pyproject.toml content
    sections.append("\n## pyproject.toml (first 60 lines)")
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            lines_read = pyproject.read_text(errors="ignore").splitlines()[:60]
            sections.append("\n".join(lines_read))
            if len(lines_read) >= 60:
                sections.append("... (content continues)")
        except:
            sections.append("(error reading file)")
    else:
        sections.append("(not found)")

    # Package.json content (if exists)
    sections.append("\n## package.json scripts")
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            import json
            data = json.loads(pkg_json.read_text())
            if 'scripts' in data:
                sections.append("Scripts found:")
                for name, cmd in list(data['scripts'].items())[:15]:
                    sections.append(f"  {name}: {cmd}")
        except:
            sections.append("(error parsing)")
    else:
        sections.append("(not found)")

    # Secrets check - using pure Python
    sections.append("\n## Potential Hardcoded Secrets")
    secret_pattern = re.compile(r'(API_KEY|SECRET|PASSWORD|TOKEN)\s*=\s*[\'"][^\'"]{8,}[\'"]')
    secrets_found = []
    for ext in ['*.py', '*.js', '*.jsx', '*.ts', '*.tsx']:
        for f in root.rglob(ext):
            if any(p in f.parts for p in ['node_modules', '.venv', '.env']):
                continue
            try:
                content = f.read_text(errors='ignore')
                matches = secret_pattern.findall(content)
                if matches and 'example' not in f.name.lower() and 'placeholder' not in content.lower():
                    secrets_found.append(f"  {f.relative_to(root)}: {len(matches)} potential secrets")
            except:
                pass
            if len(secrets_found) >= 10:
                break
    if secrets_found:
        sections.extend(secrets_found[:10])
    else:
        sections.append("(none found)")

    result = "\n".join(sections)
    print(f"  DEBUG: Generated {len(result)} chars of project data")
    return result


async def stream_agent_ready(
    project_path: str,
    provider: str = "azure_foundry_claude",
    model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream Agent Ready analysis as SSE events."""

    yield "data: 🔍 Gathering project data...\n\n"

    loop = asyncio.get_event_loop()
    
    # Step 1: Find actual project root
    try:
        project_path = await loop.run_in_executor(None, _find_project_root, project_path)
    except Exception as e:
        yield f"data: ✗ Error finding project root: {e}\n\n"
        yield "data: [DONE]\n\n"
        return
    
    root = Path(project_path)
    
    # Step 2: Stream the folder tree
    yield "data: \n\n"
    yield "data: ═══════════════════════════════════════════════════════════════\n\n"
    yield "data: \n\n"
    
    try:
        folder_tree = await loop.run_in_executor(None, _list_all_folders_and_files, root)
        for line in folder_tree.splitlines():
            yield f"data: {line}\n\n"
            await asyncio.sleep(0.001)
    except Exception as e:
        yield f"data: ✗ Error listing files: {e}\n\n"
    
    yield "data: \n\n"
    yield "data: ═══════════════════════════════════════════════════════════════\n\n"
    yield "data: \n\n"
    
    # Step 3: Gather project data using pure Python (no shell commands)
    yield "data: 📊 Reading project files for analysis...\n\n"
    
    try:
        project_data = await loop.run_in_executor(None, _gather_project_data, project_path)
    except Exception as e:
        yield f"data: ✗ Error gathering data: {e}\n\n"
        yield "data: [DONE]\n\n"
        return

    yield f"data: \n\n"
    yield f"data: ✓ Gathered {len(project_data)} chars of analysis data\n\n"
    yield f"data: 🤖 Calling {provider} ({model or 'default'}) for L1-L5 analysis...\n\n"
    yield "data: ⏳ This may take 30-60 seconds...\n\n"
    yield "data: \n\n"

    user_prompt = f"""Run a full Agent Ready analysis on this project.

Project data:
{project_data}

Produce the complete AGENT READINESS REPORT with all 20 criteria, maturity level (L1-L5), and IMPROVEMENT PLAN."""

    # Step 4: Call LLM and stream response
    try:
        from llm.client import LLMClient
        client = LLMClient(provider=provider, model=model)

        response = await loop.run_in_executor(
            None,
            lambda: client.complete(SKILL_TEXT, user_prompt, max_tokens=4096)
        )

        for line in response.splitlines():
            yield f"data: {line}\n\n"
            await asyncio.sleep(0.005)

        yield "data: \n\n"
        yield "data: ✅ Analysis complete!\n\n"

    except Exception as e:
        yield f"data: ✗ LLM Error: {e}\n\n"
        yield "data: \n\n"
        yield "data: --- Raw Project Data (no LLM) ---\n\n"
        for line in project_data.splitlines()[:80]:
            yield f"data: {line}\n\n"

    yield "data: [DONE]\n\n"
