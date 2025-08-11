#!/usr/bin/env python3
"""
Test media mirroring functionality
"""

import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from bot.config import Config
from bot.mirror import MirrorEngine

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_media():
    """Test media mirroring configuration"""
    config = Config()
    
    print("📋 Current Configuration:")
    print(f"  Mirror Enabled: {config.get_option('mirror_enabled')}")
    print(f"  Mirror Text: {config.get_option('mirror_text')}")
    print(f"  Mirror Media: {config.get_option('mirror_media')}")
    print(f"  Mirror Edits: {config.get_option('mirror_edits')}")
    print(f"  Mirror Deletes: {config.get_option('mirror_deletes')}")
    print(f"  Bypass Restriction: {config.get_option('bypass_restriction')}")
    
    # Check mappings
    mappings = config.get_all_mappings()
    print(f"\n📍 Channel Mappings: {len(mappings)} configured")
    for source, target in mappings.items():
        print(f"  {source} → {target}")
    
    # Check source/target config
    source = config.get_source_channel()
    targets = config.get_target_channels()
    print(f"\n🎯 Source Channel: {source}")
    print(f"🎯 Target Channels: {targets}")
    
    # Test client connection
    if config.session_string:
        client = TelegramClient(
            StringSession(config.session_string),
            config.api_id,
            config.api_hash
        )
        
        await client.connect()
        
        if await client.is_user_authorized():
            print("\n✅ Client authorized and ready")
            
            # Initialize engine
            engine = MirrorEngine(client, config)
            print("✅ Mirror engine initialized")
            
            # Check status
            status = engine.get_status()
            print(f"\n📊 Engine Status:")
            print(f"  Enabled: {status['enabled']}")
            print(f"  Queue Size: {status['queue_size']}")
            print(f"  Processing: {status['processing_count']}")
            
        else:
            print("\n❌ Client not authorized")
        
        await client.disconnect()
    else:
        print("\n❌ No session string configured")

if __name__ == "__main__":
    asyncio.run(test_media())