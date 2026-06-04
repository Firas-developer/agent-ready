"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ProjectGraph = exports.CodeGraph = void 0;
class CodeGraph {
    constructor() {
        // All symbols across the workspace, keyed by id
        this.symbols = new Map();
        // Reverse index: short name -> set of ids that have that name
        this.byName = new Map();
        // callerId -> set of calleeIds (resolved)
        this.outgoing = new Map();
        // calleeId -> set of callerIds (reverse edges, for impact BFS)
        this.incoming = new Map();
        // Track per-file membership so we can drop+re-add cleanly
        this.fileSymbols = new Map();
        // Per-file unresolved outgoing names (caller id -> set of names)
        this.fileOutgoing = new Map();
    }
    upsertFile(idx) {
        this.removeFile(idx.file);
        const ids = new Set();
        for (const [id, sym] of idx.symbols) {
            this.symbols.set(id, sym);
            ids.add(id);
            if (!this.byName.has(sym.name))
                this.byName.set(sym.name, new Set());
            this.byName.get(sym.name).add(id);
            this.outgoing.set(id, new Set());
            if (!this.incoming.has(id))
                this.incoming.set(id, new Set());
        }
        this.fileSymbols.set(idx.file, ids);
        this.fileOutgoing.set(idx.file, idx.outgoing);
        this.resolveAll();
    }
    removeFile(file) {
        const ids = this.fileSymbols.get(file);
        if (!ids)
            return;
        for (const id of ids) {
            const sym = this.symbols.get(id);
            if (sym) {
                const nameSet = this.byName.get(sym.name);
                nameSet?.delete(id);
                if (nameSet && nameSet.size === 0)
                    this.byName.delete(sym.name);
            }
            // Remove outgoing edges
            const out = this.outgoing.get(id);
            if (out) {
                for (const callee of out)
                    this.incoming.get(callee)?.delete(id);
            }
            this.outgoing.delete(id);
            // Remove this node as a target in others' outgoing
            const inc = this.incoming.get(id);
            if (inc) {
                for (const caller of inc)
                    this.outgoing.get(caller)?.delete(id);
            }
            this.incoming.delete(id);
            this.symbols.delete(id);
        }
        this.fileSymbols.delete(file);
        this.fileOutgoing.delete(file);
    }
    /**
     * Resolve all unresolved call-name references across the workspace into
     * concrete edges. v1 strategy: name-only matching; if a call name matches
     * multiple symbols, link to all of them (over-approximation, conservative
     * for impact analysis).
     */
    resolveAll() {
        // Clear current resolved edges, keep nodes
        for (const id of this.symbols.keys()) {
            this.outgoing.set(id, new Set());
            this.incoming.set(id, new Set());
        }
        for (const [, callerMap] of this.fileOutgoing) {
            for (const [callerId, calleeNames] of callerMap) {
                if (!this.symbols.has(callerId))
                    continue;
                for (const name of calleeNames) {
                    const matches = this.byName.get(name);
                    if (!matches)
                        continue;
                    for (const calleeId of matches) {
                        if (calleeId === callerId)
                            continue;
                        this.outgoing.get(callerId).add(calleeId);
                        this.incoming.get(calleeId).add(callerId);
                    }
                }
            }
        }
    }
    /**
     * Given a set of changed symbol ids, perform reverse BFS up to maxHops
     * to find all symbols that may be affected.
     */
    computeImpact(changedIds, maxHops) {
        const changedNodes = [];
        for (const id of changedIds) {
            const sym = this.symbols.get(id);
            if (sym)
                changedNodes.push(sym);
        }
        const visited = new Map(); // id -> hop
        const queue = [];
        for (const id of changedIds) {
            if (this.symbols.has(id)) {
                visited.set(id, 0);
                queue.push([id, 0]);
            }
        }
        const edges = [];
        while (queue.length) {
            const [id, hop] = queue.shift();
            if (hop >= maxHops)
                continue;
            const callers = this.incoming.get(id);
            if (!callers)
                continue;
            for (const caller of callers) {
                edges.push({ from: caller, to: id, kind: this.classifyEdge(caller, id) });
                if (!visited.has(caller)) {
                    visited.set(caller, hop + 1);
                    queue.push([caller, hop + 1]);
                }
            }
        }
        const impactedNodes = [];
        for (const [id, hop] of visited) {
            if (hop === 0)
                continue; // changed nodes reported separately
            const node = this.symbols.get(id);
            if (node)
                impactedNodes.push({ node, hop });
        }
        return { changedNodes, impactedNodes, edges };
    }
    getSymbol(id) {
        return this.symbols.get(id);
    }
    classifyEdge(fromId, toId) {
        const a = this.symbols.get(fromId);
        const b = this.symbols.get(toId);
        if (!a || !b)
            return "same-file";
        if (a.className && b.className && a.className !== b.className)
            return "cross-class";
        if (a.file !== b.file)
            return "cross-file";
        if (a.className && b.className && a.className === b.className)
            return "same-class";
        return "same-file";
    }
    getFileSymbols(file) {
        const ids = this.fileSymbols.get(file);
        if (!ids)
            return [];
        return Array.from(ids).map(i => this.symbols.get(i)).filter(Boolean);
    }
    size() {
        return { files: this.fileSymbols.size, symbols: this.symbols.size };
    }
    /**
     * Compare a previous snapshot of a file's symbols against the current
     * symbols and return the ids of symbols whose body changed, were added,
     * or were removed.
     */
    static diffFile(prev, next) {
        const changed = new Set();
        if (prev) {
            for (const [id, oldSym] of prev) {
                const newSym = next.get(id);
                if (!newSym) {
                    changed.add(id); // removed -> still treat as a change source
                }
                else if (newSym.bodyHash !== oldSym.bodyHash) {
                    changed.add(id);
                }
            }
        }
        for (const [id] of next) {
            if (!prev || !prev.has(id))
                changed.add(id);
        }
        return Array.from(changed);
    }
}
exports.CodeGraph = CodeGraph;
class ProjectGraph {
    constructor() {
        this.folders = new Map();
        this.files = new Map();
        this.imports = new Map(); // fromFileId -> Set<toFileId>
        this.reverseImports = new Map(); // toFileId -> Set<fromFileId>
    }
    upsertFolder(node) {
        this.folders.set(node.id, node);
    }
    upsertFile(node) {
        this.files.set(node.id, node);
        if (!this.imports.has(node.id))
            this.imports.set(node.id, new Set());
        if (!this.reverseImports.has(node.id))
            this.reverseImports.set(node.id, new Set());
    }
    removeFile(fileId) {
        const out = this.imports.get(fileId);
        if (out) {
            for (const target of out)
                this.reverseImports.get(target)?.delete(fileId);
        }
        const inc = this.reverseImports.get(fileId);
        if (inc) {
            for (const source of inc)
                this.imports.get(source)?.delete(fileId);
        }
        this.imports.delete(fileId);
        this.reverseImports.delete(fileId);
        this.files.delete(fileId);
    }
    setImports(fromFileId, toFileIds) {
        // Clear previous outgoing
        const existing = this.imports.get(fromFileId);
        if (existing) {
            for (const target of existing)
                this.reverseImports.get(target)?.delete(fromFileId);
        }
        const fresh = new Set();
        for (const target of toFileIds) {
            if (target === fromFileId)
                continue;
            fresh.add(target);
            if (!this.reverseImports.has(target))
                this.reverseImports.set(target, new Set());
            this.reverseImports.get(target).add(fromFileId);
        }
        this.imports.set(fromFileId, fresh);
    }
    getFile(id) {
        return this.files.get(id);
    }
    getFolder(id) {
        return this.folders.get(id);
    }
    allFolders() {
        return Array.from(this.folders.values());
    }
    allFiles() {
        return Array.from(this.files.values());
    }
    allImportEdges() {
        const out = [];
        for (const [from, toSet] of this.imports) {
            for (const to of toSet)
                out.push({ from, to });
        }
        return out;
    }
    /**
     * Files that (transitively) import any of `changedFileIds`. Reverse BFS
     * over the import graph.
     */
    fileImpact(changedFileIds, maxHops) {
        const changedFiles = [];
        for (const id of changedFileIds) {
            const f = this.files.get(id);
            if (f)
                changedFiles.push(f);
        }
        const visited = new Map();
        const queue = [];
        for (const id of changedFileIds) {
            if (this.files.has(id)) {
                visited.set(id, 0);
                queue.push([id, 0]);
            }
        }
        const edges = [];
        while (queue.length) {
            const [id, hop] = queue.shift();
            if (hop >= maxHops)
                continue;
            const importers = this.reverseImports.get(id);
            if (!importers)
                continue;
            for (const importer of importers) {
                edges.push({ from: importer, to: id });
                if (!visited.has(importer)) {
                    visited.set(importer, hop + 1);
                    queue.push([importer, hop + 1]);
                }
            }
        }
        const impactedFiles = [];
        for (const [id, hop] of visited) {
            if (hop === 0)
                continue;
            const f = this.files.get(id);
            if (f)
                impactedFiles.push({ file: f, hop });
        }
        return { changedFiles, impactedFiles, edges };
    }
    size() {
        let importCount = 0;
        for (const set of this.imports.values())
            importCount += set.size;
        return { folders: this.folders.size, files: this.files.size, imports: importCount };
    }
    clear() {
        this.folders.clear();
        this.files.clear();
        this.imports.clear();
        this.reverseImports.clear();
    }
}
exports.ProjectGraph = ProjectGraph;
//# sourceMappingURL=graph.js.map