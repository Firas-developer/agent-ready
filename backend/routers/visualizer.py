from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import Response
from services.zip_handler import extract_zip
from services.visualizer_service import build_graph, compute_impact
import asyncio
import json
import urllib.request
import urllib.error
from pathlib import Path

router = APIRouter(prefix="/api/visualizer", tags=["Visualizer"])

_session_graphs = {}

RIPPLE_SIDECAR_URL = "http://127.0.0.1:7780"


def _sidecar_post(path: str, payload: dict, timeout: float = 30.0):
    """Synchronous POST to the Ripple sidecar. Returns (status, json_or_text)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{RIPPLE_SIDECAR_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
            return e.code, json.loads(body) if body else {}
        except Exception:
            return e.code, {"error": str(e)}
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        return None, {"error": str(e)}


@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    result = await extract_zip(file)
    project_path = result["extracted_path"]
    file_count = result["file_count"]
    session_id = result["session_id"]

    loop = asyncio.get_event_loop()
    
    # build_graph now returns (graph_data, actual_root_used)
    graph_data, actual_root = await loop.run_in_executor(None, build_graph, project_path)

    _session_graphs[session_id] = {
        "graph": graph_data,
        "project_path": actual_root,  # Same root used to build the graph
        "sidecar_indexed": False,
    }

    # Hand the extracted root to the Ripple sidecar so /impact gets tree-sitter
    # call-graph results instead of the Python file-level fallback.
    status, body = await loop.run_in_executor(
        None, _sidecar_post, "/api/index-path", {"path": actual_root}, 60.0
    )
    if status == 200:
        _session_graphs[session_id]["sidecar_indexed"] = True
        print(f"✓ Ripple sidecar indexed {body.get('indexedFiles')} files ({body.get('symbols')} symbols)")
    else:
        print(f"⚠ Ripple sidecar unavailable ({body.get('error')}) — /impact will use Python fallback")

    print(f"╔══════════════════════════════════════════")
    print(f"║ SESSION STORED")
    print(f"╠══════════════════════════════════════════")
    print(f"║ Session ID: {session_id}")
    print(f"║ Stored root: {actual_root}")
    print(f"║ Graph nodes: {len(graph_data['nodes'])}")
    print(f"║ Sidecar indexed: {_session_graphs[session_id]['sidecar_indexed']}")
    print(f"╚══════════════════════════════════════════\n")

    return {
        "session_id": session_id,
        "file_count": file_count,
        "graph": graph_data,
    }


@router.get("/graph/{session_id}")
async def get_graph(session_id: str):
    if session_id not in _session_graphs:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_graphs[session_id]["graph"]


def _map_sidecar_to_graph(sidecar_result: dict, graph_data: dict, rel_path: str) -> dict:
    """
    Translate the Ripple sidecar's tree-sitter symbols (function-level) into
    the Visualizer graph's node IDs so the UI can highlight the same nodes
    it already renders.

    Strategy: match by (relPath, symbol_name). Anything that doesn't match a
    graph node still appears in the response with a synthetic id so the
    sidebar counts stay honest, but only matched ones get ring highlights.
    """
    # Build (relPath, label) -> node lookup
    lookup = {}
    for n in graph_data.get("nodes", []):
        if n.get("type") in ("class", "function", "method", "file"):
            key = ((n.get("path") or "").replace("\\", "/"), n.get("label") or "")
            lookup[key] = n

    def translate(item):
        # item has: id, label, kind, file, relPath, basename, line, ...
        item_rel = (item.get("relPath") or "").replace("\\", "/")
        node = lookup.get((item_rel, item.get("label")))
        if node:
            return {**node, "_sidecarKind": item.get("kind"), "line": item.get("line")}
        # Fallback: file-level rolled-up node
        file_node = next(
            (n for n in graph_data.get("nodes", [])
             if n.get("type") == "file" and (n.get("path") or "").replace("\\", "/") == item_rel),
            None,
        )
        if file_node:
            return {**file_node, "_sidecarKind": item.get("kind"), "line": item.get("line")}
        # No match: keep the sidecar entry as-is so counts are accurate
        return {
            "id": item.get("id"),
            "label": item.get("label"),
            "type": item.get("kind", "function"),
            "path": item_rel,
            "_sidecarKind": item.get("kind"),
            "line": item.get("line"),
        }

    changed = [translate(c) for c in (sidecar_result.get("changed") or [])]
    impacted = [{**translate(i), "hop": i.get("hop", 1)} for i in (sidecar_result.get("impacted") or [])]

    # Always include the changed file itself so the UI ring lands on it too
    file_node_id = f"file||{rel_path}"
    if not any(n.get("id") == file_node_id for n in changed):
        file_node = next(
            (n for n in graph_data.get("nodes", [])
             if n.get("id") == file_node_id),
            None,
        )
        if file_node:
            changed.insert(0, file_node)

    return {
        "changed": changed,
        "impacted": impacted,
        "edges": sidecar_result.get("edges") or [],
        "engine": "ripple-sidecar",
    }


@router.post("/impact/{session_id}")
async def compute_impact_endpoint(session_id: str, body: dict = Body(...)):
    """
    Compute blast-radius of an edit. Tries the Ripple sidecar (tree-sitter
    call-graph) first; falls back to the Python file-level analyzer if the
    sidecar is offline or hasn't indexed this session.
    """
    if session_id not in _session_graphs:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    rel_path = (body.get("relPath") or "").replace("\\", "/")
    new_content = body.get("content") or ""

    if not rel_path:
        raise HTTPException(status_code=400, detail="relPath is required")

    graph_data = _session_graphs[session_id]["graph"]
    project_root = _session_graphs[session_id]["project_path"]
    sidecar_indexed = _session_graphs[session_id].get("sidecar_indexed", False)
    loop = asyncio.get_event_loop()

    # Try the sidecar first
    if sidecar_indexed:
        status, sidecar_body = await loop.run_in_executor(
            None, _sidecar_post, "/api/analyze",
            {"relPath": rel_path, "content": new_content}, 30.0
        )
        if status == 200:
            mapped = _map_sidecar_to_graph(sidecar_body, graph_data, rel_path)
            print(f"\n═══ IMPACT (sidecar) ═══  {rel_path}")
            print(f"changed={len(mapped['changed'])} impacted={len(mapped['impacted'])} edges={len(mapped['edges'])}\n")
            return mapped
        print(f"⚠ Sidecar /api/analyze returned {status}: {sidecar_body.get('error')} — falling back to Python")

    # Python fallback
    result = await loop.run_in_executor(
        None, compute_impact, graph_data, project_root, rel_path, new_content, 3
    )
    result["engine"] = "python-fallback"
    print(f"\n═══ IMPACT (python) ═══  {rel_path}")
    print(f"changed={len(result['changed'])} impacted={len(result['impacted'])} edges={len(result['edges'])}\n")
    return result


@router.get("/source/{session_id}/{path:path}")
async def get_source_file(session_id: str, path: str):
    """Serve source file content for the inspector panel."""
    
    print(f"\n═══ FILE REQUEST ═══")
    print(f"Session: {session_id}")
    print(f"Path: {path}")
    
    if session_id not in _session_graphs:
        print(f"ERROR: Session not found")
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    project_root = Path(_session_graphs[session_id]["project_path"])
    print(f"Project root: {project_root}")
    
    # Normalize path
    normalized_path = path.replace('\\', '/')
    file_path = (project_root / normalized_path).resolve()
    
    print(f"Full path: {file_path}")
    print(f"Exists: {file_path.exists()}")
    
    # Security check
    try:
        file_path.relative_to(project_root.resolve())
        print(f"Security: OK")
    except ValueError:
        print(f"Security: DENIED - outside project root")
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not file_path.is_file():
        print(f"ERROR: Not a file")
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        content = file_path.read_text(errors="ignore")
        print(f"Success: {len(content)} chars")
        return Response(content=content, media_type="text/plain; charset=utf-8")
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
