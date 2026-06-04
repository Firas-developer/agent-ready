"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.INDEX_FILE_BASENAMES = exports.RESOLVABLE_EXTENSIONS = void 0;
exports.initParser = initParser;
exports.detectLanguageByPath = detectLanguageByPath;
exports.isSupportedLanguageId = isSupportedLanguageId;
exports.supportedExtensionsGlob = supportedExtensionsGlob;
exports.isCodeFile = isCodeFile;
exports.parseFile = parseFile;
exports.extractImports = extractImports;
exports.readFileSafe = readFileSafe;
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const Parser = require("web-tree-sitter");
const LANGUAGES = [
    { id: "python", wasmFile: "tree-sitter-python.wasm", extensions: [".py"], vsLanguageIds: ["python"] },
    { id: "javascript", wasmFile: "tree-sitter-javascript.wasm", extensions: [".js", ".jsx", ".mjs", ".cjs"], vsLanguageIds: ["javascript", "javascriptreact"] },
    { id: "typescript", wasmFile: "tree-sitter-typescript.wasm", extensions: [".ts"], vsLanguageIds: ["typescript"] },
    { id: "tsx", wasmFile: "tree-sitter-tsx.wasm", extensions: [".tsx"], vsLanguageIds: ["typescriptreact"] },
];
const parsers = new Map(); // language id -> Parser with that language pre-set
let initialized = false;
async function initParser(extensionPath) {
    if (initialized)
        return;
    await Parser.init({
        locateFile(scriptName) {
            return path.join(extensionPath, "media", scriptName);
        },
    });
    for (const def of LANGUAGES) {
        const wasm = path.join(extensionPath, "media", def.wasmFile);
        if (!fs.existsSync(wasm))
            continue;
        try {
            const lang = await Parser.Language.load(wasm);
            const p = new Parser();
            p.setLanguage(lang);
            parsers.set(def.id, p);
        }
        catch (e) {
            console.error(`[ripple] failed to load grammar for ${def.id}:`, e);
        }
    }
    initialized = true;
}
function detectLanguageByPath(file) {
    const ext = path.extname(file).toLowerCase();
    for (const def of LANGUAGES) {
        if (def.extensions.includes(ext))
            return def.id;
    }
    return null;
}
function isSupportedLanguageId(vsId) {
    return LANGUAGES.some(d => d.vsLanguageIds.includes(vsId));
}
function supportedExtensionsGlob() {
    const exts = Array.from(new Set(LANGUAGES.flatMap(d => d.extensions.map(e => e.replace(/^\./, "")))));
    return `**/*.{${exts.join(",")}}`;
}
function isCodeFile(file) {
    return detectLanguageByPath(file) !== null;
}
/**
 * Possible filename extensions to probe when resolving an import.
 * Includes both code and common asset types so we can build edges
 * from code → JSON / CSS / SCSS / PNG / etc.
 */
exports.RESOLVABLE_EXTENSIONS = [
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py",
    ".json", ".css", ".scss", ".sass", ".less",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".md", ".html", ".yaml", ".yml", ".toml",
];
/**
 * Index files within a folder for resolveImportPath to use.
 */
exports.INDEX_FILE_BASENAMES = ["index", "__init__"];
function hashString(s) {
    let h = 0;
    for (let i = 0; i < s.length; i++)
        h = (h * 31 + s.charCodeAt(i)) | 0;
    return h.toString(36);
}
function qname(parentChain, name) {
    return [...parentChain, name].join(".");
}
function parseFile(file, source) {
    const langId = detectLanguageByPath(file);
    if (!langId)
        return null;
    const parser = parsers.get(langId);
    if (!parser)
        return null;
    const tree = parser.parse(source);
    const symbols = new Map();
    const outgoing = new Map();
    if (langId === "python") {
        walkPython(tree.rootNode, file, source, symbols, outgoing);
    }
    else {
        // JS, JSX, TS, TSX all share the same walker.
        walkJsLike(tree.rootNode, file, source, symbols, outgoing);
    }
    tree.delete();
    const imports = extractImports(source, langId);
    return { file, language: langId, symbols, outgoing, imports };
}
/* -------------------------------------------------------------------------- */
/* Import extraction (regex-based — runs over raw source, not the AST).       */
/* Returns array of unresolved path strings. Path resolution happens in       */
/* extension.ts where we have the workspace file index available.             */
/* -------------------------------------------------------------------------- */
const RE_PY_FROM = /^\s*from\s+([\w.]+|\.+[\w.]*)\s+import\s+/gm;
const RE_PY_IMPORT = /^\s*import\s+([\w.]+(?:\s*,\s*[\w.]+)*)/gm;
const RE_JS_FROM = /(?:import|export)\s+(?:[\s\S]+?\s+from\s+)?['"]([^'"]+)['"]/g;
const RE_JS_REQUIRE = /\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)/g;
const RE_JS_DYNAMIC = /\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)/g;
const RE_JS_BARE_IMP = /^\s*import\s+['"]([^'"]+)['"]/gm;
function extractImports(source, languageId) {
    const out = [];
    if (languageId === "python") {
        for (const m of source.matchAll(RE_PY_FROM))
            out.push(m[1]);
        for (const m of source.matchAll(RE_PY_IMPORT)) {
            // Skip `from x import ...` lines (already captured above); the `import x, y` form may list multiple
            for (const part of m[1].split(","))
                out.push(part.trim());
        }
    }
    else {
        // JavaScript / TypeScript / JSX / TSX
        for (const m of source.matchAll(RE_JS_FROM))
            out.push(m[1]);
        for (const m of source.matchAll(RE_JS_REQUIRE))
            out.push(m[1]);
        for (const m of source.matchAll(RE_JS_DYNAMIC))
            out.push(m[1]);
        for (const m of source.matchAll(RE_JS_BARE_IMP))
            out.push(m[1]);
    }
    // Dedupe while preserving order
    const seen = new Set();
    const result = [];
    for (const p of out) {
        if (!seen.has(p)) {
            seen.add(p);
            result.push(p);
        }
    }
    return result;
}
function readFileSafe(file) {
    try {
        return fs.readFileSync(file, "utf8");
    }
    catch {
        return null;
    }
}
/* -------------------------------------------------------------------------- */
/* Python walker                                                              */
/* -------------------------------------------------------------------------- */
function walkPython(root, file, source, symbols, outgoing) {
    function visit(node, parentChain, classChain, enclosingSymbolId) {
        if (node.type === "function_definition") {
            const nameNode = node.childForFieldName("name");
            if (nameNode) {
                const name = nameNode.text;
                const id = `${file}::${qname(parentChain, name)}`;
                symbols.set(id, {
                    id, name, kind: "function", file,
                    className: classChain.length ? classChain[classChain.length - 1] : null,
                    startLine: node.startPosition.row + 1,
                    endLine: node.endPosition.row + 1,
                    bodyHash: hashString(source.slice(node.startIndex, node.endIndex)),
                });
                outgoing.set(id, new Set());
                for (const child of node.namedChildren)
                    visit(child, [...parentChain, name], classChain, id);
                return;
            }
        }
        if (node.type === "class_definition") {
            const nameNode = node.childForFieldName("name");
            if (nameNode) {
                const name = nameNode.text;
                for (const child of node.namedChildren)
                    visit(child, [...parentChain, name], [...classChain, name], enclosingSymbolId);
                return;
            }
        }
        // Module-level or class-level assignment → variable symbol.
        // Only at the top level of the file or directly inside a class body
        // (enclosingSymbolId === null means we're not inside a function).
        if (node.type === "assignment" && enclosingSymbolId === null) {
            const left = node.childForFieldName("left");
            const right = node.childForFieldName("right");
            if (left && right) {
                for (const targetName of pythonExtractAssignTargets(left)) {
                    const id = `${file}::${qname(parentChain, targetName)}`;
                    symbols.set(id, {
                        id,
                        name: targetName,
                        kind: "variable",
                        file,
                        className: classChain.length ? classChain[classChain.length - 1] : null,
                        startLine: node.startPosition.row + 1,
                        endLine: node.endPosition.row + 1,
                        bodyHash: hashString(source.slice(right.startIndex, right.endIndex)),
                    });
                    outgoing.set(id, new Set());
                }
            }
            // Fall through so RHS gets descended for further capture.
        }
        if (node.type === "call" && enclosingSymbolId) {
            const fn = node.childForFieldName("function");
            if (fn) {
                const callName = extractPythonCallName(fn);
                if (callName)
                    outgoing.get(enclosingSymbolId).add(callName);
            }
        }
        // Inside a function body, capture every identifier reference that's not
        // a definition position. Unresolved names are filtered by byName lookup
        // at edge-resolution time; over-approximation is the documented tradeoff.
        if (node.type === "identifier" && enclosingSymbolId !== null) {
            if (!isPythonDefinitionPosition(node)) {
                outgoing.get(enclosingSymbolId).add(node.text);
            }
        }
        for (const child of node.namedChildren)
            visit(child, parentChain, classChain, enclosingSymbolId);
    }
    visit(root, [], [], null);
}
function pythonExtractAssignTargets(node) {
    if (node.type === "identifier")
        return [node.text];
    if (node.type === "pattern_list" || node.type === "tuple_pattern" || node.type === "list_pattern") {
        const out = [];
        for (const child of node.namedChildren)
            out.push(...pythonExtractAssignTargets(child));
        return out;
    }
    // Attribute LHS (e.g. `self.x = 5`) is not a module/class variable target.
    return [];
}
function isPythonDefinitionPosition(node) {
    const parent = node.parent;
    if (!parent)
        return false;
    const ptype = parent.type;
    // Function or class definition name
    if ((ptype === "function_definition" || ptype === "class_definition") && parent.childForFieldName("name") === node)
        return true;
    // LHS of an assignment / augmented assignment
    if ((ptype === "assignment" || ptype === "augmented_assignment") && parent.childForFieldName("left") === node)
        return true;
    // Parameter declaration contexts
    if (ptype === "parameters")
        return true;
    if (["typed_parameter", "default_parameter", "typed_default_parameter"].includes(ptype)) {
        const nameField = parent.childForFieldName("name");
        if (nameField === node)
            return true;
        if (!nameField && parent.namedChildren[0] === node)
            return true;
    }
    // Import-related contexts
    if (["import_statement", "import_from_statement", "aliased_import", "dotted_name", "wildcard_import"].includes(ptype))
        return true;
    // For-loop target
    if (ptype === "for_statement" && parent.childForFieldName("left") === node)
        return true;
    // With statement `as` binding
    if (ptype === "as_pattern_target")
        return true;
    // Function position of a call (handled by call-name capture above)
    if (ptype === "call" && parent.childForFieldName("function") === node)
        return true;
    // Attribute's `.foo` property (handled separately if it's a call)
    if (ptype === "attribute" && parent.childForFieldName("attribute") === node)
        return true;
    // Keyword argument name: f(key=value) — `key` isn't a reference
    if (ptype === "keyword_argument" && parent.childForFieldName("name") === node)
        return true;
    // Global / nonlocal statements declare bindings, not reads
    if (ptype === "global_statement" || ptype === "nonlocal_statement")
        return true;
    return false;
}
function extractPythonCallName(node) {
    if (node.type === "identifier")
        return node.text;
    if (node.type === "attribute") {
        const attr = node.childForFieldName("attribute");
        if (attr)
            return attr.text;
    }
    return null;
}
/* -------------------------------------------------------------------------- */
/* JavaScript / JSX / TypeScript / TSX walker                                 */
/* -------------------------------------------------------------------------- */
const JS_FUNC_TYPES = new Set([
    "function_declaration",
    "function_expression",
    "generator_function_declaration",
    "generator_function",
]);
const JS_ARROW_TYPES = new Set(["arrow_function"]);
const JS_METHOD_TYPES = new Set(["method_definition", "method_signature", "abstract_method_signature"]);
const JS_CLASS_TYPES = new Set(["class_declaration", "class", "abstract_class_declaration"]);
function walkJsLike(root, file, source, symbols, outgoing) {
    function defineSymbol(node, name, parentChain, classChain, kind = "function", bodyRange) {
        const id = `${file}::${qname(parentChain, name)}`;
        const range = bodyRange ?? { start: node.startIndex, end: node.endIndex };
        symbols.set(id, {
            id, name, kind, file,
            className: classChain.length ? classChain[classChain.length - 1] : null,
            startLine: node.startPosition.row + 1,
            endLine: node.endPosition.row + 1,
            bodyHash: hashString(source.slice(range.start, range.end)),
        });
        outgoing.set(id, new Set());
        return id;
    }
    function visit(node, parentChain, classChain, enclosingSymbolId, pendingName) {
        const type = node.type;
        if (JS_CLASS_TYPES.has(type)) {
            const nameNode = node.childForFieldName("name");
            if (nameNode) {
                const name = nameNode.text;
                for (const child of node.namedChildren) {
                    visit(child, [...parentChain, name], [...classChain, name], enclosingSymbolId, null);
                }
                return;
            }
        }
        if (JS_FUNC_TYPES.has(type)) {
            const nameNode = node.childForFieldName("name");
            const name = (nameNode && nameNode.text) || pendingName;
            if (name) {
                const id = defineSymbol(node, name, parentChain, classChain);
                for (const child of node.namedChildren) {
                    visit(child, [...parentChain, name], classChain, id, null);
                }
                return;
            }
        }
        if (JS_ARROW_TYPES.has(type)) {
            if (pendingName) {
                const id = defineSymbol(node, pendingName, parentChain, classChain);
                for (const child of node.namedChildren) {
                    visit(child, [...parentChain, pendingName], classChain, id, null);
                }
                return;
            }
            // Anonymous arrow — descend without creating a symbol, but keep enclosing
            for (const child of node.namedChildren) {
                visit(child, parentChain, classChain, enclosingSymbolId, null);
            }
            return;
        }
        if (JS_METHOD_TYPES.has(type)) {
            const nameNode = node.childForFieldName("name");
            if (nameNode) {
                const name = nameNode.text;
                const id = defineSymbol(node, name, parentChain, classChain);
                for (const child of node.namedChildren) {
                    visit(child, [...parentChain, name], classChain, id, null);
                }
                return;
            }
        }
        if (type === "variable_declarator" || type === "assignment_expression") {
            const nameNode = type === "variable_declarator"
                ? node.childForFieldName("name")
                : node.childForFieldName("left");
            const valueNode = type === "variable_declarator"
                ? node.childForFieldName("value")
                : node.childForFieldName("right");
            const name = nameNode && nameNode.type === "identifier" ? nameNode.text : null;
            if (name && valueNode) {
                const isFnValue = JS_ARROW_TYPES.has(valueNode.type) || JS_FUNC_TYPES.has(valueNode.type);
                // Module-level non-function variable → variable symbol.
                if (!isFnValue && type === "variable_declarator" && enclosingSymbolId === null) {
                    defineSymbol(node, name, parentChain, classChain, "variable", { start: valueNode.startIndex, end: valueNode.endIndex });
                    for (const child of node.namedChildren) {
                        visit(child, parentChain, classChain, enclosingSymbolId, null);
                    }
                    return;
                }
                // If the value is a function-like, attach this name to it.
                visit(valueNode, parentChain, classChain, enclosingSymbolId, name);
                for (const child of node.namedChildren) {
                    if (child !== valueNode)
                        visit(child, parentChain, classChain, enclosingSymbolId, null);
                }
                return;
            }
        }
        if (type === "pair" || type === "property_definition" || type === "public_field_definition") {
            // Object literal property or class field, possibly assigned an arrow.
            const keyNode = node.childForFieldName("key") || node.childForFieldName("name");
            const valNode = node.childForFieldName("value");
            const name = keyNode ? keyNode.text : null;
            if (name && valNode) {
                const isFnValue = JS_ARROW_TYPES.has(valNode.type) || JS_FUNC_TYPES.has(valNode.type);
                // Class field with non-function value → variable symbol.
                if (!isFnValue && type === "public_field_definition" && classChain.length > 0) {
                    defineSymbol(node, name, parentChain, classChain, "variable", { start: valNode.startIndex, end: valNode.endIndex });
                    for (const child of node.namedChildren) {
                        visit(child, parentChain, classChain, enclosingSymbolId, null);
                    }
                    return;
                }
                visit(valNode, parentChain, classChain, enclosingSymbolId, name);
                for (const child of node.namedChildren) {
                    if (child !== valNode)
                        visit(child, parentChain, classChain, enclosingSymbolId, null);
                }
                return;
            }
        }
        if (type === "call_expression" && enclosingSymbolId) {
            const fn = node.childForFieldName("function");
            if (fn) {
                const callName = extractJsCallName(fn);
                if (callName)
                    outgoing.get(enclosingSymbolId).add(callName);
            }
        }
        if (type === "new_expression" && enclosingSymbolId) {
            // `new Foo()` — treat constructor as a call to the class name
            const ctor = node.childForFieldName("constructor");
            if (ctor) {
                const callName = extractJsCallName(ctor);
                if (callName)
                    outgoing.get(enclosingSymbolId).add(callName);
            }
        }
        // JSX component usage: <Foo /> and <Foo>...</Foo> are both "calls" to Foo.
        // Lowercase tags (<div>, <span>) are HTML and are skipped.
        if ((type === "jsx_self_closing_element" || type === "jsx_opening_element") && enclosingSymbolId) {
            const nameNode = node.childForFieldName("name");
            if (nameNode) {
                const callName = extractJsxComponentName(nameNode);
                if (callName)
                    outgoing.get(enclosingSymbolId).add(callName);
            }
        }
        // Identifier-read capture inside a function body. Over-approximates
        // (every captured name will be filtered by byName lookup); same name
        // collision tradeoff as the function model.
        if (type === "identifier" && enclosingSymbolId !== null) {
            if (!isJsDefinitionPosition(node)) {
                outgoing.get(enclosingSymbolId).add(node.text);
            }
        }
        for (const child of node.namedChildren) {
            visit(child, parentChain, classChain, enclosingSymbolId, null);
        }
    }
    visit(root, [], [], null, null);
}
function extractJsCallName(node) {
    if (node.type === "identifier" || node.type === "type_identifier")
        return node.text;
    if (node.type === "member_expression") {
        const prop = node.childForFieldName("property");
        if (prop)
            return prop.text;
    }
    if (node.type === "subscript_expression")
        return null; // dynamic, skip
    // Type-asserted call in TS: (foo as Bar)()
    if (node.type === "parenthesized_expression" && node.namedChildren.length) {
        return extractJsCallName(node.namedChildren[0]);
    }
    return null;
}
/**
 * Extract the component name from a JSX element's `name` field.
 * Filters out lowercase HTML tags (<div>, <span>, etc.) — only React-style
 * uppercased component identifiers or member expressions (<Lib.Button />)
 * are treated as cross-symbol references.
 */
function extractJsxComponentName(node) {
    if (node.type === "identifier") {
        const name = node.text;
        if (name && /^[A-Z]/.test(name))
            return name;
        return null;
    }
    if (node.type === "member_expression" || node.type === "jsx_namespace_name") {
        const prop = node.childForFieldName("property") || node.childForFieldName("name");
        if (prop)
            return prop.text;
    }
    return null;
}
/**
 * Returns true if this identifier node is at a position where it *defines*
 * a name (parameter, declaration, etc.) rather than *references* one.
 * Used to filter identifier captures so we don't link a function to itself
 * through its own name, parameters, or LHS-of-assignment targets.
 */
function isJsDefinitionPosition(node) {
    const parent = node.parent;
    if (!parent)
        return false;
    const ptype = parent.type;
    // Declaration name fields
    const declTypes = [
        "function_declaration", "function_expression",
        "generator_function_declaration", "generator_function",
        "class_declaration", "abstract_class_declaration",
        "method_definition", "method_signature", "abstract_method_signature",
    ];
    if (declTypes.includes(ptype) && parent.childForFieldName("name") === node)
        return true;
    // variable_declarator name (const x = ...)
    if (ptype === "variable_declarator" && parent.childForFieldName("name") === node)
        return true;
    // assignment_expression left (x = ...)
    if (ptype === "assignment_expression" && parent.childForFieldName("left") === node)
        return true;
    // Augmented assignment left (x += ...)
    if (ptype === "augmented_assignment_expression" && parent.childForFieldName("left") === node)
        return true;
    // Parameters
    if (["formal_parameters", "required_parameter", "optional_parameter", "rest_pattern", "object_pattern", "array_pattern"].includes(ptype))
        return true;
    // Single-param arrow: x => ...
    if (ptype === "arrow_function" && parent.childForFieldName("parameter") === node)
        return true;
    // Imports / exports
    if (["import_specifier", "import_clause", "import_statement", "namespace_import", "export_specifier", "export_statement"].includes(ptype))
        return true;
    // Object property / class field name positions
    if ((ptype === "pair" || ptype === "property_definition" || ptype === "public_field_definition") &&
        (parent.childForFieldName("name") === node || parent.childForFieldName("key") === node))
        return true;
    // For-in / for-of target
    if ((ptype === "for_in_statement" || ptype === "for_of_statement") && parent.childForFieldName("left") === node)
        return true;
    // Call function position (handled by call-name capture)
    if (ptype === "call_expression" && parent.childForFieldName("function") === node)
        return true;
    // new Foo() constructor position (handled by new-expression capture)
    if (ptype === "new_expression" && parent.childForFieldName("constructor") === node)
        return true;
    // member.property — property handled when used as a call; the object part still gets captured
    if (ptype === "member_expression" && parent.childForFieldName("property") === node)
        return true;
    // JSX element name (handled by JSX-element capture)
    if ((ptype === "jsx_self_closing_element" || ptype === "jsx_opening_element" || ptype === "jsx_closing_element") &&
        parent.childForFieldName("name") === node)
        return true;
    // JSX attribute name (e.g. onClick={x}) — not a reference
    if (ptype === "jsx_attribute" && parent.namedChildren[0] === node)
        return true;
    // Catch clause parameter
    if (ptype === "catch_clause" && parent.childForFieldName("parameter") === node)
        return true;
    // Labeled statement label
    if (ptype === "labeled_statement" && parent.childForFieldName("label") === node)
        return true;
    return false;
}
//# sourceMappingURL=indexer.js.map