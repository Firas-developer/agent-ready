"use strict";
const http = require("http");
const fs = require("fs");
const path = require("path");

const { initParser, parseFile, readFileSafe, detectLanguageByPath } = require("./indexer");
const { CodeGraph } = require("./graph");

const PORT = 7780;
const HOST = "127.0.0.1";
const MAX_HOPS = 3;

const EXCLUDE_DIRS = new Set([
  ".venv", "venv", "node_modules", "__pycache__", ".git",
  "dist", "build", ".next", "out", "coverage", ".turbo",
  ".pytest_cache", ".mypy_cache",
]);

// One graph + previousFileSymbols map, mutated by index-path / analyze
let codeGraph = new CodeGraph();
let previousFileSymbols = new Map();
let currentRoot = null;

function getRelPath(file) {
  if (!currentRoot) return path.basename(file);
  if (file.startsWith(currentRoot)) {
    return file.substring(currentRoot.length).replace(/^[\\/]/, "");
  }
  return path.basename(file);
}

function decorateNode(node) {
  const rel = getRelPath(node.file);
  const parts = rel.split(/[\\/]/);
  const displayPath = parts.length >= 2 ? parts.slice(-2).join("/") : parts[parts.length - 1];
  return {
    id: node.id,
    label: node.name,
    kind: node.kind,
    file: node.file,
    relPath: rel,
    basename: path.basename(node.file),
    displayPath,
    className: node.className,
    line: node.startLine,
  };
}

function buildPayload(result) {
  return {
    changed: result.changedNodes.map(decorateNode),
    impacted: result.impactedNodes.map(({ node, hop }) => ({ ...decorateNode(node), hop })),
    edges: result.edges,
  };
}

function walkDir(root) {
  const out = [];
  const stack = [root];
  while (stack.length) {
    const dir = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (entry.name.startsWith(".") && entry.name !== ".") continue;
      if (EXCLUDE_DIRS.has(entry.name)) continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        stack.push(full);
      } else if (entry.isFile()) {
        out.push(full);
      }
    }
  }
  return out;
}

async function indexFolder(folder) {
  const abs = path.resolve(folder);
  if (!fs.existsSync(abs) || !fs.statSync(abs).isDirectory()) {
    throw new Error(`Folder does not exist: ${abs}`);
  }
  // Start fresh — replace the graph & symbol map for the new project
  codeGraph = new CodeGraph();
  previousFileSymbols = new Map();
  currentRoot = abs;

  const files = walkDir(abs);
  let indexed = 0;
  for (const file of files) {
    if (!detectLanguageByPath(file)) continue;
    const src = readFileSafe(file);
    if (src === null) continue;
    const idx = parseFile(file, src);
    if (!idx) continue;
    codeGraph.upsertFile(idx);
    previousFileSymbols.set(file, new Map(idx.symbols));
    indexed++;
  }

  const { symbols } = codeGraph.size();
  console.log(`[ripple-sidecar] indexed ${indexed} files (${symbols} symbols) at ${abs}`);
  return { indexedFiles: indexed, symbols, root: abs };
}

function findAbsForRelPath(relPath) {
  const want = relPath.replace(/\\/g, "/");
  for (const key of previousFileSymbols.keys()) {
    if (getRelPath(key).replace(/\\/g, "/") === want) return key;
  }
  // Fallback: basename match
  const wantBase = path.basename(want);
  for (const key of previousFileSymbols.keys()) {
    if (path.basename(key) === wantBase) return key;
  }
  return null;
}

function analyzeEdit(relPath, content) {
  const abs = findAbsForRelPath(relPath);
  if (!abs) {
    return { error: "file_not_indexed", relPath, indexedFiles: previousFileSymbols.size };
  }
  const idx = parseFile(abs, content);
  if (!idx) {
    return { error: "parse_failed", relPath };
  }
  const prev = previousFileSymbols.get(abs);
  const changedIds = CodeGraph.diffFile(prev, idx.symbols);
  codeGraph.upsertFile(idx);
  previousFileSymbols.set(abs, new Map(idx.symbols));
  const result = codeGraph.computeImpact(changedIds, MAX_HOPS);
  return buildPayload(result);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => { body += chunk.toString(); });
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

function send(res, code, payload) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Content-Type", "application/json");
  res.writeHead(code);
  res.end(typeof payload === "string" ? payload : JSON.stringify(payload));
}

async function handle(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.url === "/api/health" && req.method === "GET") {
    const { symbols } = codeGraph.size();
    return send(res, 200, {
      ok: true,
      indexedFiles: previousFileSymbols.size,
      symbols,
      root: currentRoot,
    });
  }

  if (req.url === "/api/index-path" && req.method === "POST") {
    try {
      const body = await readBody(req);
      const { path: folder } = JSON.parse(body || "{}");
      if (!folder) return send(res, 400, { error: "path is required" });
      const summary = await indexFolder(folder);
      return send(res, 200, summary);
    } catch (err) {
      return send(res, 500, { error: String(err && err.message || err) });
    }
  }

  if (req.url === "/api/analyze" && req.method === "POST") {
    try {
      const body = await readBody(req);
      const { relPath, content } = JSON.parse(body || "{}");
      if (typeof relPath !== "string" || typeof content !== "string") {
        return send(res, 400, { error: "relPath and content are required" });
      }
      const result = analyzeEdit(relPath, content);
      if (result.error === "file_not_indexed") return send(res, 404, result);
      if (result.error === "parse_failed") return send(res, 422, result);
      return send(res, 200, result);
    } catch (err) {
      return send(res, 500, { error: String(err && err.message || err) });
    }
  }

  send(res, 404, { error: "not_found", url: req.url });
}

async function main() {
  const here = __dirname;
  await initParser(here); // looks for ./media/*.wasm
  console.log(`[ripple-sidecar] tree-sitter initialised (media at ${path.join(here, "media")})`);

  const server = http.createServer((req, res) => {
    handle(req, res).catch((err) => {
      console.error("[ripple-sidecar] handler error:", err);
      try { send(res, 500, { error: String(err && err.message || err) }); } catch {}
    });
  });

  server.on("error", (err) => {
    if (err.code === "EADDRINUSE") {
      console.error(`[ripple-sidecar] port ${PORT} already in use — another sidecar is probably running`);
      process.exit(1);
    } else {
      console.error("[ripple-sidecar] server error:", err);
    }
  });

  server.listen(PORT, HOST, () => {
    console.log(`[ripple-sidecar] listening on http://${HOST}:${PORT}`);
  });
}

main().catch((err) => {
  console.error("[ripple-sidecar] fatal:", err);
  process.exit(1);
});
