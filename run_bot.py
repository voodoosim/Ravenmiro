#!/usr/bin/env python3
"""
Bot launcher script
"""

import sys
import os

# Add bot directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

if __name__ == "__main__":
    import asyncio
    from bot.main import main
    asyncio.run(main())
