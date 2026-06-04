"""
Visualizer service — builds code graph including ALL files.
Returns (graph_data, actual_root_used) tuple to ensure path consistency.
"""
import ast
import re
from pathlib import Path

EXCLUDE_DIRS = {
    "node_modules", "__pycache__", ".venv", ".git",
    "dist", "build", ".pytest_cache", ".mypy_cache",
}

SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}

SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin", ".o", ".a",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".tiff",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".zip", ".tar", ".gz", ".bz2", ".rar", ".7z",
    ".mp4", ".mp3", ".wav", ".avi", ".mov", ".mkv",
    ".db", ".sqlite", ".sqlite3",
}


class GraphBuilder:
    def __init__(self):
        self.nodes: dict = {}
        self.edges: list = []
        self._edge_set: set = set()
        self._file_nodes: dict = {}
        self._symbol_ids: dict = {}

    def _id(self, *parts) -> str:
        return "||".join(str(p) for p in parts)

    def add_node(self, nid, label, ntype, path="", size=10):
        if nid not in self.nodes:
            self.nodes[nid] = {"id": nid, "label": label, "type": ntype, "path": path, "size": size}
        return nid

    def add_edge(self, source, target, etype):
        if not source or not target or source == target:
            return
        k = (source, target, etype)
        if k not in self._edge_set:
            self._edge_set.add(k)
            self.edges.append({"source": source, "target": target, "type": etype})

    def to_dict(self):
        return {"nodes": list(self.nodes.values()), "edges": self.edges}


def _scan_python(path: Path, rel: str, graph: GraphBuilder) -> list:
    file_id = graph._file_nodes.get(rel, "")
    imported_modules = []
    try:
        source = path.read_text(errors="ignore")
        tree = ast.parse(source)
    except:
        return []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            cid = graph._id(rel, "class", node.name)
            graph.add_node(cid, node.name, "class", rel, size=8)
            graph.add_edge(file_id, cid, "contains")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mid = graph._id(rel, "class", node.name, "method", item.name)
                    graph.add_node(mid, item.name, "method", rel, size=4)
                    graph.add_edge(cid, mid, "contains")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.col_offset == 0:
                fid = graph._id(rel, "func", node.name)
                graph.add_node(fid, node.name, "function", rel, size=6)
                graph.add_edge(file_id, fid, "contains")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.append(node.module)

    return imported_modules


def _scan_js(path: Path, rel: str, graph: GraphBuilder) -> list:
    file_id = graph._file_nodes.get(rel, "")
    imports = []
    try:
        source = path.read_text(errors="ignore")
    except:
        return []

    for m in re.finditer(r'\bclass\s+(\w+)', source):
        cname = m.group(1)
        cid = graph._id(rel, "class", cname)
        graph.add_node(cid, cname, "class", rel, size=8)
        graph.add_edge(file_id, cid, "contains")

    for m in re.finditer(r'(?:^|[\n;{])\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(', source, re.MULTILINE):
        fname = m.group(1)
        fid = graph._id(rel, "func", fname)
        graph.add_node(fid, fname, "function", rel, size=6)
        graph.add_edge(file_id, fid, "contains")

    for m in re.finditer(r'(?:^|[\n;])\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?(?:\(|React\.memo)', source, re.MULTILINE):
        fname = m.group(1)
        fid = graph._id(rel, "func", fname)
        graph.add_node(fid, fname, "function", rel, size=6)
        graph.add_edge(file_id, fid, "contains")

    for m in re.finditer(r"""import\s+.*?from\s+['"]([^'"]+)['"]""", source, re.DOTALL):
        imports.append(m.group(1))
    for m in re.finditer(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""", source):
        imports.append(m.group(1))

    return imports


def _resolve_imports(src_rel, imported, graph, project_root):
    src_id = graph._file_nodes.get(src_rel, "")
    if not src_id:
        return
    src_path = project_root / src_rel

    for mod in imported:
        if mod.startswith("."):
            base = (src_path.parent / mod).resolve()
            for ext in ("", ".py", ".js", ".jsx", ".ts", ".tsx", "/index.js", "/index.ts", "/__init__.py"):
                candidate = Path(str(base) + ext)
                try:
                    target_rel = str(candidate.relative_to(project_root)).replace('\\', '/')
                    if target_rel in graph._file_nodes:
                        graph.add_edge(src_id, graph._file_nodes[target_rel], "imports")
                        break
                except ValueError:
                    pass


def _find_project_root(extracted_path: str) -> str:
    """
    Deterministic root detection - goes up to 2 levels deep to find backend/ or frontend/.
    """
    root = Path(extracted_path)
    
    print(f"\n╔═══════════════════════════════════════════")
    print(f"║ Finding Project Root")
    print(f"╠═══════════════════════════════════════════")
    print(f"║ Extraction path: {root}")
    print(f"║ Exists: {root.exists()}")
    
    try:
        contents = [x.name for x in sorted(root.iterdir())[:20]]
        print(f"║ Contents (first 20): {', '.join(contents)}")
    except Exception as e:
        print(f"║ Error listing: {e}")
        return str(root)
    
    # Check current level
    has_backend = (root / "backend").is_dir()
    has_frontend = (root / "frontend").is_dir()
    
    print(f"║ Has backend/: {has_backend}")
    print(f"║ Has frontend/: {has_frontend}")
    
    if has_backend or has_frontend:
        print(f"╠═══════════════════════════════════════════")
        print(f"║ ✅ DECISION: Using current dir (has backend/ or frontend/)")
        print(f"║ Project root: {root.name}")
        print(f"╚═══════════════════════════════════════════\n")
        return str(root)
    
    # Check subdirectories
    subdirs = [
        d for d in root.iterdir()
        if d.is_dir() 
        and not d.name.startswith('.')
        and d.name not in EXCLUDE_DIRS
    ]
    
    print(f"║ Non-hidden subdirs: {len(subdirs)}")
    if subdirs:
        print(f"║ Subdirs: {', '.join([d.name for d in subdirs[:10]])}")
    
    # Level 1: Check immediate subdirs
    if len(subdirs) == 1:
        subdir = subdirs[0]
        print(f"║ Single subdir found: {subdir.name}")
        
        sub_has_backend = (subdir / "backend").is_dir()
        sub_has_frontend = (subdir / "frontend").is_dir()
        
        print(f"║   Has backend/: {sub_has_backend}")
        print(f"║   Has frontend/: {sub_has_frontend}")
        
        if sub_has_backend or sub_has_frontend:
            print(f"╠═══════════════════════════════════════════")
            print(f"║ ✅ DECISION: Using single subdir")
            print(f"║ Project root: {subdir.name}")
            print(f"╚═══════════════════════════════════════════\n")
            return str(subdir)
        else:
            # Level 2: Go one more level deep (handles zip/ProjectName/ structure)
            print(f"║ Subdir '{subdir.name}' has no backend/frontend, checking deeper...")
            inner_subdirs = [
                d for d in subdir.iterdir()
                if d.is_dir() and not d.name.startswith('.') and d.name not in EXCLUDE_DIRS
            ]
            
            if len(inner_subdirs) == 1:
                inner = inner_subdirs[0]
                print(f"║ Inner single subdir: {inner.name}")
                inner_has_backend = (inner / "backend").is_dir()
                inner_has_frontend = (inner / "frontend").is_dir()
                print(f"║   Has backend/: {inner_has_backend}")
                print(f"║   Has frontend/: {inner_has_frontend}")
                
                if inner_has_backend or inner_has_frontend:
                    print(f"╠═══════════════════════════════════════════")
                    print(f"║ ✅ DECISION: Using inner subdir")
                    print(f"║ Project root: {inner.name}")
                    print(f"╚═══════════════════════════════════════════\n")
                    return str(inner)
    
    # Default: use current dir
    print(f"╠═══════════════════════════════════════════")
    print(f"║ ✅ DECISION: Using current dir (default)")
    print(f"║ Project root: {root.name}")
    print(f"╚═══════════════════════════════════════════\n")
    return str(root)


def _parse_python_symbol_ids(source: str, rel: str) -> set:
    """Return symbol IDs (class/function/method) from Python source, matching GraphBuilder's id format."""
    ids = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ids
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            ids.add(f"{rel}||class||{node.name}")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    ids.add(f"{rel}||class||{node.name}||method||{item.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.col_offset == 0:
                ids.add(f"{rel}||func||{node.name}")
    return ids


def _parse_js_symbol_ids(source: str, rel: str) -> set:
    """Return symbol IDs from JS/TS source, matching GraphBuilder's id format."""
    ids = set()
    for m in re.finditer(r'\bclass\s+(\w+)', source):
        ids.add(f"{rel}||class||{m.group(1)}")
    for m in re.finditer(r'(?:^|[\n;{])\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(', source, re.MULTILINE):
        ids.add(f"{rel}||func||{m.group(1)}")
    for m in re.finditer(r'(?:^|[\n;])\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?(?:\(|React\.memo)', source, re.MULTILINE):
        ids.add(f"{rel}||func||{m.group(1)}")
    return ids


def compute_impact(graph_data: dict, project_root: str, rel_path: str, new_content: str, max_hops: int = 3) -> dict:
    """
    Compute the blast-radius of editing rel_path with new_content.
    Returns {changed, impacted, edges} where each is a list of graph node/edge objects.
    """
    project_root_path = Path(project_root)
    file_id = f"file||{rel_path}"

    file_path = project_root_path / rel_path
    try:
        old_content = file_path.read_text(errors="ignore") if file_path.is_file() else ""
    except Exception:
        old_content = ""

    rel_lower = rel_path.lower()
    if rel_lower.endswith(".py"):
        old_syms = _parse_python_symbol_ids(old_content, rel_path)
        new_syms = _parse_python_symbol_ids(new_content, rel_path)
    elif any(rel_lower.endswith(ext) for ext in (".js", ".jsx", ".ts", ".tsx")):
        old_syms = _parse_js_symbol_ids(old_content, rel_path)
        new_syms = _parse_js_symbol_ids(new_content, rel_path)
    else:
        old_syms, new_syms = set(), set()

    # The file itself is always "changed" (the user edited it)
    changed_ids = {file_id}
    # Added / removed symbols
    changed_ids.update(old_syms - new_syms)
    changed_ids.update(new_syms - old_syms)
    # If content differs at all, every symbol in the file is potentially affected
    if old_content != new_content:
        for n in graph_data["nodes"]:
            if n.get("path") == rel_path and n["type"] in ("class", "function", "method"):
                changed_ids.add(n["id"])

    # Reverse adjacency for `imports` edges
    rev_imports = {}
    for e in graph_data["edges"]:
        if e["type"] == "imports":
            rev_imports.setdefault(e["target"], []).append((e["source"], e))

    impacted_file_ids = set()
    edges_to_show = []
    visited = {file_id}
    queue = [(file_id, 0)]
    while queue:
        nid, hop = queue.pop(0)
        if hop >= max_hops:
            continue
        for src, edge in rev_imports.get(nid, []):
            if src not in visited:
                visited.add(src)
                impacted_file_ids.add(src)
                edges_to_show.append({**edge, "hop": hop + 1})
                queue.append((src, hop + 1))

    node_by_id = {n["id"]: n for n in graph_data["nodes"]}
    changed_nodes = [node_by_id[i] for i in changed_ids if i in node_by_id]
    impacted_nodes = [node_by_id[i] for i in impacted_file_ids if i in node_by_id]

    return {
        "changed": changed_nodes,
        "impacted": impacted_nodes,
        "edges": edges_to_show,
    }


def build_graph(project_path: str) -> tuple:
    """
    Build code graph - returns (graph_data, actual_root_used).
    This ensures the router stores the same root that was used to build the graph.
    """
    
    # Detect actual project root first
    actual_project_root = _find_project_root(project_path)
    project_root = Path(actual_project_root)
    
    print(f"\n╔═══════════════════════════════════════════")
    print(f"║ Building Graph")
    print(f"╠═══════════════════════════════════════════")
    print(f"║ Extraction path: {project_path}")
    print(f"║ Detected root: {actual_project_root}")
    
    try:
        root_items = sorted(project_root.iterdir())[:15]
        print(f"║ Root items (first 15):")
        for item in root_items:
            symbol = "📁" if item.is_dir() else "📄"
            print(f"║   {symbol} {item.name}")
    except Exception as e:
        print(f"║ Error: {e}")
    
    graph = GraphBuilder()
    folder_ids = {}
    file_paths = []

    # Collect all items
    all_items = []
    for item in sorted(project_root.rglob("*")):
        try:
            rel = str(item.relative_to(project_root)).replace('\\', '/')
        except ValueError:
            continue

        parts = rel.split('/')
        
        if any(p in EXCLUDE_DIRS for p in parts):
            continue
        if any(p.startswith(".") for p in parts):
            continue
        
        all_items.append((item, rel))

    print(f"║ Total items collected: {len(all_items)}")
    print(f"║ Sample paths (first 15):")
    for item, rel in all_items[:15]:
        typ = "DIR " if item.is_dir() else "FILE"
        print(f"║   {typ} {rel}")
    
    # Build nodes
    for item, rel in all_items:
        if item.is_dir():
            fid = graph._id("folder", rel)
            folder_ids[rel] = fid
            graph.add_node(fid, item.name, "folder", rel, size=16)
            
            if '/' in rel:
                parent_rel = rel[:rel.rfind('/')]
                if parent_rel in folder_ids:
                    graph.add_edge(folder_ids[parent_rel], fid, "contains")

        elif item.is_file():
            if item.suffix in SKIP_EXTENSIONS:
                continue
            
            fid = graph._id("file", rel)
            graph._file_nodes[rel] = fid
            graph.add_node(fid, item.name, "file", rel, size=9)
            
            if item.suffix in SOURCE_EXTENSIONS:
                file_paths.append(item)
            
            if '/' in rel:
                parent_rel = rel[:rel.rfind('/')]
                if parent_rel in folder_ids:
                    graph.add_edge(folder_ids[parent_rel], fid, "contains")

    print(f"║ Nodes created: {len(graph.nodes)}")
    print(f"║ Edges created: {len(graph.edges)}")

    # Scan source files
    all_imports = {}
    for path in file_paths:
        try:
            rel = str(path.relative_to(project_root)).replace('\\', '/')
        except ValueError:
            continue
        if path.suffix == ".py":
            all_imports[rel] = _scan_python(path, rel, graph)
        elif path.suffix in {".js", ".jsx", ".ts", ".tsx"}:
            all_imports[rel] = _scan_js(path, rel, graph)

    # Import edges
    for rel, imported in all_imports.items():
        _resolve_imports(rel, imported, graph, project_root)

    graph_data = graph.to_dict()

    # Verify root-level nodes
    root_nodes = [n for n in graph_data['nodes'] if '/' not in n['path']]
    print(f"║")
    print(f"║ Root-level nodes: {len(root_nodes)}")
    for n in root_nodes[:15]:
        print(f"║   {n['type']:8s} {n['path']}")
    
    # Stats
    counts = {}
    for n in graph_data["nodes"]:
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    edge_counts = {}
    for e in graph_data["edges"]:
        edge_counts[e["type"]] = edge_counts.get(e["type"], 0) + 1

    graph_data["stats"] = {
        "total_nodes": len(graph_data["nodes"]),
        "total_edges": len(graph_data["edges"]),
        "by_type": counts,
        "edge_types": edge_counts,
    }

    print(f"║")
    print(f"║ Final stats: {len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges")
    print(f"║ By type: {counts}")
    print(f"╚═══════════════════════════════════════════\n")

    # Return BOTH graph data AND the actual root used
    return graph_data, str(project_root)
