#!/usr/bin/env python3
"""
Telegram Mirror Bot - Main Entry Point
Complete mirroring bot with copy restriction bypass
"""

import asyncio
import logging
import signal
import sys
from contextlib import suppress

try:
    from colorama import Fore, Style, init  # type: ignore
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    # Fallback if colorama is not installed
    COLORAMA_AVAILABLE = False
    class Fore:  # type: ignore
        RED = GREEN = YELLOW = CYAN = ''
    class Style:  # type: ignore
        BRIGHT = RESET_ALL = ''

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession

from .config import Config
from .mirror import MirrorEngine
from .session_handler import SessionManager
from .menu_base import SimpleMenuHandler

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
        self.client: TelegramClient | None = None
        self.mirror_engine: MirrorEngine | None = None
        self.menu_handler: SimpleMenuHandler | None = None
        self.running = False
        self._shutdown_task = None  # For clean shutdown

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
            logger.info(
                "Successfully logged in as: %s (@%s)",
                me.first_name, me.username  # type: ignore
            )

            self.mirror_engine = MirrorEngine(self.client, self.config)
            self.menu_handler = SimpleMenuHandler(self.client, self.config, self.mirror_engine)

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
        @self.client.on(events.NewMessage())  # Listen to all messages
        async def message_handler(event):
            try:
                # Check if it's a menu command or selection
                if event.message.text:
                    text = event.message.text.strip()

                    # Always handle main commands
                    if (text.startswith('.설정') or text.startswith('.동기화') or
                        text.startswith('.카피') or text.startswith('.카카시') or
                        text.startswith('.정지')):
                        logger.info(f"Command received from {event.sender_id}: {text}")
                        if self.menu_handler:
                            await self.menu_handler.handle_command(event)
                            return

                    # Only handle menu selections if user is in a menu
                    if self.menu_handler and (
                        event.sender_id in self.menu_handler.user_states or
                        event.sender_id in self.menu_handler.waiting_for_input
                    ):
                        # Let the menu handler decide if it should process this
                        await self.menu_handler.handle_command(event)
                        return

                # Regular mirroring
                if self.running and self.mirror_engine:
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
        logger.info("Bot started. Send .설정 for configuration")

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
            with suppress(Exception):
                await self.client.disconnect()  # type: ignore
        logger.info("%sBot stopped", Fore.YELLOW)

    def handle_signal(self, sig, frame):  # pylint: disable=unused-argument
        """Handle shutdown signals"""
        logger.info("Received signal %s", sig)
        self._shutdown_task = asyncio.create_task(self.stop())
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
    # Fix Windows Unicode issue
    if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print("╔══════════════════════════════════╗")
    print("║     Telegram Mirror Bot v1.0     ║")
    print("║   Complete Copy Restriction Bypass║")
    print("╚══════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")
    asyncio.run(main())
