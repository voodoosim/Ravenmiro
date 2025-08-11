#!/usr/bin/env python3
"""
Verify that mirroring is working correctly
"""

import sys
from pathlib import Path

# Fix Windows Unicode
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

# Add parent directory to path  
sys.path.insert(0, str(Path(__file__).parent))

from bot.config import Config

def check_mirror_config():
    """Check the mirroring configuration"""
    config = Config()
    
    print("=" * 60)
    print("CROWBOT MIRROR CONFIGURATION CHECK")
    print("=" * 60)
    
    # Check if mirroring is enabled
    mirror_enabled = config.get_option("mirror_enabled")
    print(f"\n1. Mirror Status: {'✅ ENABLED' if mirror_enabled else '❌ DISABLED'}")
    
    # Check source channel
    source = config.get_source_channel()
    if source:
        print(f"\n2. Source Channel: {source} ✅")
    else:
        print("\n2. Source Channel: NOT SET ❌")
    
    # Check target channels
    targets = config.get_target_channels()
    if targets:
        print(f"\n3. Target Channels ({len(targets)}):")
        for target in targets:
            print(f"   • {target}")
    else:
        print("\n3. Target Channels: NOT SET ❌")
    
    # Check session
    has_session = bool(config.session_string)
    print(f"\n4. Session: {'✅ CONFIGURED' if has_session else '❌ NOT CONFIGURED'}")
    
    # Summary
    print("\n" + "=" * 60)
    
    if mirror_enabled and source and targets and has_session:
        print("✅ BOT IS READY TO MIRROR!")
        print(f"\nMessages from channel {source} will be mirrored to:")
        for target in targets:
            print(f"  → {target}")
        print("\nTo test:")
        print("1. Run the bot with: python bot/main.py")
        print("2. Send a message to the source channel")
        print("3. Check if it appears in the target channel(s)")
    else:
        print("⚠️ BOT IS NOT READY. Issues found:")
        if not mirror_enabled:
            print("  • Mirroring is disabled (use .설정 menu option 4)")
        if not source:
            print("  • Source channel not set (use .설정 menu option 1)")
        if not targets:
            print("  • No target channels (use .설정 menu option 2)")
        if not has_session:
            print("  • Session not configured (set SESSION_STRING env var)")
    
    print("=" * 60)

if __name__ == "__main__":
    check_mirror_config()