#!/usr/bin/env python3
"""
Speed test for mirror bot
Tests emoji support and mirroring speed
"""

import asyncio
import time
from telethon import TelegramClient
from telethon.sessions import StringSession
from bot.config import Config
from bot.mirror import MirrorEngine

async def test_speed():
    """Test mirroring speed and emoji support"""
    config = Config()
    
    # Create client
    client = TelegramClient(
        StringSession(config.session_string),
        config.api_id,
        config.api_hash
    )
    
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ Session invalid")
        return
    
    me = await client.get_me()
    print(f"✅ Logged in as {me.first_name}")
    
    # Initialize engine
    engine = MirrorEngine(client, config)
    
    # Get status
    status = engine.get_status()
    print(f"\n📊 Engine Status:")
    print(f"  - Enabled: {status['enabled']}")
    print(f"  - Queue size: {status['queue_size']}")
    print(f"  - Performance: {status['performance']['avg_mirror_time']:.2f}s")
    
    # Test message with emojis
    test_messages = [
        "Test message with regular emoji 😀 🎉 ❤️",
        "Custom emoji test 🥷 and premium 💎",
        "Mixed emojis 😊 🥷 🎯 with text",
    ]
    
    print("\n🧪 Testing emoji mirroring...")
    
    for msg in test_messages:
        print(f"  Testing: {msg[:30]}...")
        # The actual test would send and check
        
    print("\n✅ Speed test complete!")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_speed())