"""
Session Handler Module
Manages Telethon session strings and authentication
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from telethon.sessions import StringSession  # type: ignore[import-untyped]
from telethon import TelegramClient  # type: ignore[import-untyped]
from telethon.errors import SessionPasswordNeededError  # type: ignore[import-untyped]

logger = logging.getLogger('SessionHandler')


class SessionManager:
    """Manages Telegram session authentication and storage"""
    def __init__(self, config):
        self.config = config
        self.session_file = Path('data/session.txt')
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

    async def get_session(self) -> Optional[str]:
        """Get session string from config or file"""
        session = self.config.session_string

        if not session and self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    session = f.read().strip()
                    if session:
                        self.config.session_string = session
            except (OSError, IOError) as e:
                logger.error("Failed to read session file: %s", e)

        return session if session else None

    async def save_session(self, session_string: str) -> bool:
        """Save session string to config and file"""
        try:
            self.config.session_string = session_string

            with open(self.session_file, 'w', encoding='utf-8') as f:
                f.write(session_string)

            logger.info("Session saved successfully")
            return True
        except (OSError, IOError) as e:
            logger.error("Failed to save session: %s", e)
            return False

    async def validate_session(self, session_string: str) -> bool:
        """Validate session string"""
        try:
            if not session_string or len(session_string) < 100:
                return False

            client = TelegramClient(
                StringSession(session_string),
                self.config.api_id,
                self.config.api_hash
            )

            await client.connect()
            authorized = await client.is_user_authorized()

            if authorized:
                me = await client.get_me()
                logger.info("Session valid for: %s (@%s)",
                          me.first_name, me.username)  # type: ignore[attr-defined]

            if client:
                try:
                    await client.disconnect()  # type: ignore
                except:
                    pass
            return authorized

        except (ConnectionError, ValueError, TypeError) as e:
            logger.error("Session validation failed: %s", e)
            return False

    async def create_session(self, phone: Optional[str] = None) -> Optional[str]:
        """Create new session (interactive)"""
        try:
            client = TelegramClient(
                StringSession(),
                self.config.api_id,
                self.config.api_hash
            )

            await client.connect()

            if not phone:
                phone = input("Enter phone number (with country code): ")

            await client.send_code_request(phone)
            code = input("Enter verification code: ")

            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("2FA Password required: ")
                await client.sign_in(password=password)

            session_string = client.session.save()  # type: ignore
            await self.save_session(session_string)

            me = await client.get_me()
            logger.info("Session created for: %s (@%s)",
                       me.first_name, me.username)  # type: ignore[attr-defined]

            if client:
                try:
                    await client.disconnect()  # type: ignore
                except:
                    pass
            return session_string

        except (ConnectionError, ValueError, TypeError) as e:
            logger.error("Session creation failed: %s", e)
            return None

    async def import_session(self, session_string: str) -> bool:
        """Import external session string"""
        if await self.validate_session(session_string):
            return await self.save_session(session_string)
        return False

    def clear_session(self):
        """Clear stored session"""
        self.config.session_string = ''
        if self.session_file.exists():
            self.session_file.unlink()
        logger.info("Session cleared")

    async def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Get information about current session"""
        session = await self.get_session()
        if not session:
            return None

        try:
            client = TelegramClient(
                StringSession(session),
                self.config.api_id,
                self.config.api_hash
            )

            await client.connect()

            if not await client.is_user_authorized():
                return None

            me = await client.get_me()
            dialogs_count = len(await client.get_dialogs(limit=1))

            info = {
                'id': me.id,  # type: ignore
                'username': me.username,  # type: ignore
                'first_name': me.first_name,  # type: ignore
                'last_name': me.last_name,  # type: ignore
                'phone': me.phone,  # type: ignore
                'premium': getattr(me, 'premium', False),
                'verified': getattr(me, 'verified', False),
                'dialogs': dialogs_count
            }

            if client:
                try:
                    await client.disconnect()  # type: ignore
                except:
                    pass
            return info

        except (ConnectionError, ValueError, TypeError) as e:
            logger.error("Failed to get session info: %s", e)
            return None
