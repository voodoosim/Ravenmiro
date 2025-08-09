#!/usr/bin/env python3
"""
Telegram Mirror Bot - Main Entry Point
Complete mirroring bot with copy restriction bypass
"""

import asyncio
import logging
import signal
import sys
from typing import Optional
from colorama import init, Fore, Style

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

from config import Config
from session_handler import SessionManager
from mirror import MirrorEngine
from commands import CommandHandler

init(autoreset=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MirrorBot')


class MirrorBot:
    """Main bot class for Telegram mirroring with restriction bypass"""
    def __init__(self):
        self.config = Config()
        self.session_manager = SessionManager(self.config)
        self.client: Optional[TelegramClient] = None
        self.mirror_engine: Optional[MirrorEngine] = None
        self.command_handler: Optional[CommandHandler] = None
        self.running = False

    async def initialize(self):
        """Initialize bot with session string"""
        try:
            session_string = await self.session_manager.get_session()
            if not session_string:
                logger.error("%sNo session string available. Use .설정 session to set one", Fore.RED)
                return False

            self.client = TelegramClient(
                StringSession(session_string),
                self.config.api_id,
                self.config.api_hash,
                flood_sleep_threshold=60,
                request_retries=10,
                connection_retries=10
            )

            await self.client.connect()

            if not await self.client.is_user_authorized():
                logger.error("%sSession invalid or expired", Fore.RED)
                return False

            me = await self.client.get_me()
            logger.info("%s✓ Logged in as: %s (@%s)", Fore.GREEN, me.first_name, me.username)  # type: ignore

            self.mirror_engine = MirrorEngine(self.client, self.config)
            self.command_handler = CommandHandler(self.client, self.config, self.mirror_engine)

            self._register_handlers()

            return True

        except Exception as e:
            logger.error("%sInitialization failed: %s", Fore.RED, e)
            return False

    def _register_handlers(self):
        """Register event handlers"""
        if not self.client:
            logger.error("Client not initialized")
            return
            
        @self.client.on(events.NewMessage())
        async def message_handler(event):
            try:
                if event.message.text and event.message.text.startswith('.설정'):
                    if self.command_handler:
                        await self.command_handler.handle_command(event)
                elif self.running and self.mirror_engine:
                    await self.mirror_engine.handle_message(event)
            except FloodWaitError as e:
                logger.warning("Flood wait: %ss", e.seconds)
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.error("Message handler error: %s", e)

        @self.client.on(events.MessageEdited())
        async def edit_handler(event):
            if self.running and self.mirror_engine:
                await self.mirror_engine.handle_edit(event)

        @self.client.on(events.MessageDeleted())
        async def delete_handler(event):
            if self.running and self.mirror_engine:
                await self.mirror_engine.handle_delete(event)

        @self.client.on(events.Album())
        async def album_handler(event):
            if self.running and self.mirror_engine:
                await self.mirror_engine.handle_album(event)

    async def start(self):
        """Start the bot"""
        if not await self.initialize():
            return

        self.running = True
        logger.info("%sBot started. Send .설정 for configuration", Fore.CYAN)

        try:
            if self.client:
                await self.client.run_until_disconnected()  # type: ignore
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await self.stop()

    async def stop(self):
        """Clean shutdown"""
        self.running = False
        if self.mirror_engine:
            await self.mirror_engine.save_state()
        if self.client:
            try:
                await self.client.disconnect()  # type: ignore
            except Exception:
                pass
        logger.info("%sBot stopped", Fore.YELLOW)

    def handle_signal(self, sig, frame):  # pylint: disable=unused-argument
        """Handle shutdown signals"""
        logger.info("Received signal %s", sig)
        asyncio.create_task(self.stop())
        sys.exit(0)


async def main():
    """Main entry point for the bot"""
    bot = MirrorBot()

    signal.signal(signal.SIGINT, bot.handle_signal)
    signal.signal(signal.SIGTERM, bot.handle_signal)

    while True:
        try:
            await bot.start()
            break
        except Exception as e:
            logger.error("Bot crashed: %s", e)
            logger.info("Restarting in 10 seconds...")
            await asyncio.sleep(10)


if __name__ == '__main__':
    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print("╔══════════════════════════════════╗")
    print("║     Telegram Mirror Bot v1.0     ║")
    print("║   Complete Copy Restriction Bypass║")
    print("╚══════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")
    
    asyncio.run(main())
