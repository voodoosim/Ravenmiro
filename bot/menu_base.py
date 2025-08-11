"""
Base menu handler with core navigation logic
"""

import logging

from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat

from .config import Config
from .menu_sync import SyncMenu
from .menu_settings import SettingsMenu
from .menu_auto_copy import AutoCopyMenu

logger = logging.getLogger("Menu")


class SimpleMenuHandler:
    """Simplified menu handler - main coordinator"""

    def __init__(self, client: TelegramClient, config: Config, mirror_engine):
        self.client = client
        self.config = config
        self.mirror_engine = mirror_engine

        # User state management
        self.user_states: dict[int, str] = {}
        self.waiting_for_input: set[int] = set()
        self.temp_data: dict[int, dict] = {}

        # Sub-menu handlers
        self.sync_menu = SyncMenu(self)
        self.settings_menu = SettingsMenu(self)
        self.auto_copy_menu = AutoCopyMenu(self)

    async def handle_command(self, event: events.NewMessage.Event):
        """Handle user commands and menu navigation"""
        user_id = event.sender_id
        text = event.message.text.strip() if event.message.text else ""

        # Handle main commands
        if text.startswith(".설정"):
            await self.show_main_menu(event)
            return
        elif text.startswith(".동기화"):
            await self.sync_menu.handle_sync_command(event)
            return
        elif text.startswith(".카피"):
            await self.auto_copy_menu.handle_copy_command(event)
            return
        elif text.startswith(".카카시"):
            await self.auto_copy_menu.handle_kakashi_command(event)
            return
        elif text.startswith(".정지"):
            await self.auto_copy_menu.handle_stop_command(event)
            return

        # Handle menu navigation
        if user_id in self.user_states:
            state = self.user_states[user_id]

            # Back navigation
            if text in ["0", "뒤로", "취소", "cancel"]:
                await self.handle_back(event)
                return

            # Route to appropriate handler
            if state == "main":
                await self.handle_main_menu(event, text)
            elif state.startswith("input"):
                await self.settings_menu.handle_input_menu(event, text, state)
            elif state.startswith("output"):
                await self.settings_menu.handle_output_menu(event, text, state)
            elif state.startswith("log"):
                await self.settings_menu.handle_log_menu(event, text, state)
            elif state.startswith("sync"):
                await self.sync_menu.handle_sync_menu(event, text, state)
            elif state.startswith("auto_copy"):
                await self.auto_copy_menu.handle_auto_copy_menu(event, text, state)

    async def show_main_menu(self, event):
        """Show main menu"""
        user_id = event.sender_id
        self.user_states[user_id] = "main"

        # Get status
        mappings = self.config.get_all_mappings()
        input_count = len(mappings)
        output_count = sum(1 for v in mappings.values() if v is not None)
        log_channel = self.config.get_log_channel()
        mirror_enabled = self.config.get_option("mirror_enabled")

        status = {
            "input": f"{input_count}개 채널" if input_count else "설정안됨",
            "output": f"{output_count}개 연결" if output_count else "설정안됨",
            "log": "설정됨" if log_channel else "설정안됨",
            "mirror": "✅" if mirror_enabled else "❌",
        }

        menu_text = f"""카피닌자🥷 까막 V.1

1. 입력 설정
2. 출력 설정
3. 로그 설정
4. 미러링 토글 (현재: {status['mirror']})

• 입력: {status['input']}
• 출력: {status['output']}
• 미러링: {status['mirror']}
• 로그: {status['log']}

0번 - 종료"""

        await event.respond(menu_text)

    async def handle_main_menu(self, event, text: str):
        """Handle main menu selection"""
        user_id = event.sender_id

        if text == "1":
            await self.settings_menu.show_input_menu(event)
        elif text == "2":
            await self.settings_menu.show_output_menu(event)
        elif text == "3":
            await self.settings_menu.show_log_menu(event)
        elif text == "4":
            # Toggle mirroring
            current_state = self.config.get_option("mirror_enabled")
            new_state = not current_state
            self.config.set_option("mirror_enabled", new_state)

            if new_state:
                await event.respond("✅ 미러링이 활성화되었습니다.")
            else:
                await event.respond("❌ 미러링이 비활성화되었습니다.")

            await self.show_main_menu(event)
        elif text == "0":
            del self.user_states[user_id]
            await event.respond("종료되었습니다.")

    async def handle_back(self, event):
        """Handle back navigation"""
        user_id = event.sender_id

        if user_id not in self.user_states:
            return

        state = self.user_states[user_id]

        # Clear any waiting state
        if user_id in self.waiting_for_input:
            self.waiting_for_input.remove(user_id)

        # Navigate back
        if state in ["input_menu", "output_menu", "log_menu"]:
            await self.show_main_menu(event)
        elif (
            state.startswith("input_")
            or state.startswith("output_")
            or state.startswith("log_")
        ):
            # Go back to respective menu
            if state.startswith("input"):
                await self.settings_menu.show_input_menu(event)
            elif state.startswith("output"):
                await self.settings_menu.show_output_menu(event)
            elif state.startswith("log"):
                await self.settings_menu.show_log_menu(event)
        else:
            # Default: go to main menu
            await self.show_main_menu(event)

    async def get_user_channels(self) -> list:
        """Get list of channels user has joined"""
        channels = []
        async for dialog in self.client.iter_dialogs():
            if isinstance(dialog.entity, Channel | Chat):
                if isinstance(dialog.entity, Channel):
                    if dialog.entity.broadcast or dialog.entity.megagroup:
                        channels.append(dialog.entity)
                elif isinstance(dialog.entity, Chat):
                    channels.append(dialog.entity)
        return channels

    def get_proper_channel_id(self, entity) -> int:
        """Get proper channel ID with -100 prefix for channels/supergroups"""
        if isinstance(entity, Channel) and (entity.broadcast or entity.megagroup):
            return -1000000000000 - entity.id
        return -entity.id if hasattr(entity, "id") else 0
