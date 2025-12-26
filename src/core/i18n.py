"""
Internationalization (i18n) module - English Only

Provides translation functions for CLI and other components.
"""

from __future__ import annotations

from typing import Any

from ..locales.en import MESSAGES


def t(key: str, **kwargs: Any) -> str:
    """
    Get translated text by key.
    
    Args:
        key: Message key from locales
        **kwargs: Format arguments for the message
        
    Returns:
        Translated and formatted string
        
    Example:
        >>> t("welcome")
        "FOX PRO AI"
        
        >>> t("issues_found", n=3)
        "Found 3 issue(s):"
    """
    text = MESSAGES.get(key, key)
    
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    
    return text
