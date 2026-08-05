"""File path -> dotted module path, relative to the indexed repo root."""


def module_path(rel_path: str) -> str:
    parts = rel_path.removesuffix(".py").split("/")
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)
