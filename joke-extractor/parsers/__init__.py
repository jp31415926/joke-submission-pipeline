"""
Parser module: registers and exposes joke email parsers.
Each parser must implement:
    parse(data: list[str], subject: str) -> tuple[list[str], str]
where `data` is the cleaned text body (one string in list),
and returns (joke_content_list, modified_subject).

Parsers are auto-registered via `register_parser` decorator.
"""

import pkgutil
import importlib
from typing import Callable
from .email_data import EmailData, JokeData

_parser_registry: list[tuple[Callable[[EmailData], bool], Callable[[EmailData], list]]] = []

def register_parser(checker: Callable[[EmailData], bool]):
    """Decorator to register a parser by EmailData matcher."""
    def decorator(parser_func):
        _parser_registry.append((checker, parser_func))
        return parser_func
    return decorator

def get_parser(email: EmailData):
    """Return the matching parser (or None) based on `From` header."""
    for matcher, parser in _parser_registry:
        if matcher(email):
            return parser
    return None

# 🔁 Auto-discover and import all parser modules at load time
# This ensures decorators like @register_parser run
def _load_parsers():
    import os
    import sys
    # Get the directory where this __init__.py lives
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    for module_info in pkgutil.iter_modules([pkg_dir]):
        module_name = module_info.name
        # Skip private/internal modules
        if module_name.startswith('_'):
            continue
        # Import submodule: parsers.<module_name>
        try:
            importlib.import_module(f".{module_name}", package=__name__)
            # logging.debug(f"Loaded parser: {module_name}")
        except Exception as e:
            import sys
            sys.stderr.write(f"Warning: Failed to import parser '{module_name}': {e}\n")

# Run auto-discovery at module import
_load_parsers()

# This makes the types available when importing from parsers
__all__ = ['get_parser', 'register_parser', 'EmailData', 'JokeData']
