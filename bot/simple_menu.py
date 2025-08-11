"""
Simple Menu Handler - Main entry point
Delegates to specialized menu modules for compact code organization
"""

# Re-export the main handler from menu_base
from .menu_base import SimpleMenuHandler

__all__ = ['SimpleMenuHandler']