# Parsers module for PMS Analyzer
from parsers.base_parser import BaseParser
from parsers.sameeksha_parser import SameekshaParser

# Registry of available parsers
PARSER_REGISTRY = {
    'sameeksha': SameekshaParser,
}

def get_parser(provider: str) -> type:
    """Get parser class for a given provider."""
    provider_lower = provider.lower()
    if provider_lower not in PARSER_REGISTRY:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(PARSER_REGISTRY.keys())}")
    return PARSER_REGISTRY[provider_lower]

__all__ = ['BaseParser', 'SameekshaParser', 'PARSER_REGISTRY', 'get_parser']

