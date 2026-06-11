import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language(), "python")
parser = Parser()
parser.set_language(PY_LANGUAGE)


def parse_python_file(source_code: str) -> list[dict]:
    tree = parser.parse(source_code.encode("utf-8"))
    root = tree.root_node
    symbols = []

    for node in root.children:
        # top level functions
        if node.type == "function_definition":
            sym = _extract_function(node, source_code)
            if sym:
                symbols.append(sym)

        # top level classes
        elif node.type == "class_definition":
            sym = _extract_class(node, source_code)
            if sym:
                symbols.append(sym)

    return symbols


def _get_text(node, source: str) -> str:
    return source[node.start_byte:node.end_byte]


def _extract_docstring(body_node, source: str) -> str | None:
    if not body_node or not body_node.children:
        return None
    for child in body_node.children:
        if child.type == "expression_statement":
            for subchild in child.children:
                if subchild.type == "string":
                    return _get_text(subchild, source).strip("\"'")
    return None


def _extract_function(node, source: str) -> dict | None:
    name = None
    params = ""
    body = None

    for child in node.children:
        if child.type == "identifier":
            name = _get_text(child, source)
        elif child.type == "parameters":
            params = _get_text(child, source)
        elif child.type == "block":
            body = child

    if not name:
        return None

    return {
        "name": name,
        "kind": "function",
        "start_line": node.start_point[0] + 1,
        "end_line": node.end_point[0] + 1,
        "signature": f"def {name}{params}",
        "docstring": _extract_docstring(body, source),
        "raw_source": _get_text(node, source),
    }


def _extract_class(node, source: str) -> dict | None:
    name = None
    body = None

    for child in node.children:
        if child.type == "identifier":
            name = _get_text(child, source)
        elif child.type == "block":
            body = child

    if not name:
        return None

    methods = []
    if body:
        for child in body.children:
            if child.type == "function_definition":
                method = _extract_function(child, source)
                if method:
                    method["kind"] = "method"
                    methods.append(method)

    return {
        "name": name,
        "kind": "class",
        "start_line": node.start_point[0] + 1,
        "end_line": node.end_point[0] + 1,
        "signature": f"class {name}",
        "docstring": _extract_docstring(body, source),
        "raw_source": _get_text(node, source),
        "methods": methods,
    }