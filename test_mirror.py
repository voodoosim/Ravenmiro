#!/usr/bin/env python3
"""
Test script to verify mirroring functionality
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows Unicode
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bot.config import Config
from bot.session_handler import SessionManager
from telethon import TelegramClient
from telethon.sessions import StringSession


async def test_mirror_status():
    """Test if mirroring is enabled and show current configuration"""
    print("=" * 50)
    print("Mirror Bot Configuration Test")
    print("=" * 50)
    
    # Load config
    config = Config()
    
    # Check mirror status
    mirror_enabled = config.get_option("mirror_enabled")
    print(f"\n✅ Mirror Enabled: {mirror_enabled}")
    
    # Check channel mappings
    mappings = config.get_all_mappings()
    print(f"\n📋 Channel Mappings: {len(mappings)} configured")
    
    if mappings:
        print("\nCurrent Mappings:")
        for source, target in mappings.items():
            status = "✅" if target else "❌ (no target)"
            print(f"  {source} → {target} {status}")
    else:
        print("  ⚠️ No channel mappings configured!")
        print("  Use .설정 to configure source and target channels")
    
    # Check source/target channels (new style)
    source = config.get_source_channel()
    targets = config.get_target_channels()
    
    print(f"\n📥 Source Channel: {source if source else 'Not configured'}")
    print(f"📤 Target Channels: {len(targets)} configured")
    if targets:
        for target in targets:
            print(f"  • {target}")
    
    # Check options
    print("\n⚙️ Mirror Options:")
    options = {
        "mirror_text": config.get_option("mirror_text"),
        "mirror_media": config.get_option("mirror_media"),
        "mirror_edits": config.get_option("mirror_edits"),
        "mirror_deletes": config.get_option("mirror_deletes"),
        "bypass_restriction": config.get_option("bypass_restriction"),
    }
    
    for option, value in options.items():
        status = "✅" if value else "❌"
        print(f"  {option}: {status}")
    
    # Check session
    session_manager = SessionManager(config)
    has_session = bool(config.session_string)
    print(f"\n🔐 Session: {'✅ Configured' if has_session else '❌ Not configured'}")
    
    # Summary
    print("\n" + "=" * 50)
    if not has_session:
        print("⚠️ Session not configured. Bot won't be able to connect.")
        print("   Use environment variable SESSION_STRING or .설정")
    elif not mappings and not source:
        print("⚠️ No channel mappings or source/target configured.")
        print("   Bot is ready but won't mirror anything.")
        print("   Use .설정 to configure channels")
    elif mirror_enabled:
        print("✅ Bot is configured and mirroring is ENABLED")
        print("   Messages will be mirrored based on your configuration")
    else:
        print("❌ Mirroring is DISABLED")
        print("   Use .설정 and option 4 to enable mirroring")
    
    print("=" * 50)


async def test_connection():
    """Test if bot can connect with current session"""
    config = Config()
    
    if not config.session_string:
        print("❌ No session string available")
        return
    
    try:
        print("\n🔄 Testing connection...")
        client = TelegramClient(
            StringSession(config.session_string),
            config.api_id,
            config.api_hash
        )
        
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"✅ Connected as: {me.first_name} (@{me.username})")  # type: ignore
            
            # List some channels
            print("\n📋 Your channels (first 5):")
            count = 0
            async for dialog in client.iter_dialogs():
                if hasattr(dialog.entity, 'broadcast') or hasattr(dialog.entity, 'megagroup'):
                    print(f"  • {dialog.name} (ID: {dialog.entity.id})")
                    count += 1
                    if count >= 5:
                        break
        else:
            print("❌ Session invalid or expired")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")


async def main():
    """Run all tests"""
    await test_mirror_status()
    
    # Ask if user wants to test connection
    print("\nTest bot connection? (y/n): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        await test_connection()


if __name__ == "__main__":
    asyncio.run(main())