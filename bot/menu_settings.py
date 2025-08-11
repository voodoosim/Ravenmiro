"""
Settings menu handlers for source and target channels
"""

import logging
from telethon.tl.types import Channel, Chat

logger = logging.getLogger("SettingsMenu")


class SettingsMenu:
    """Handle all settings-related menus"""

    def __init__(self, parent):
        self.parent = parent
        self.client = parent.client
        self.config = parent.config

    async def show_input_menu(self, event):
        """Show source channel menu"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = "input_menu"

        # Get current source channel
        source = self.config.get_source_channel()

        text = "📥 **입력 채널 설정** (소스)\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        text += "현재 소스 채널:\n"
        text += "─────────────────────────\n"

        if source:
            try:
                entity = await self.client.get_entity(source)
                name = getattr(entity, "title", "Unknown")

                if isinstance(entity, Channel):
                    if entity.broadcast:
                        entity_type = "📢 채널"
                    else:
                        entity_type = "👥 슈퍼그룹"
                else:
                    entity_type = "👥 그룹"

                text += f"{entity_type}: {name}\n"

                # Add additional info
                try:
                    member_count = getattr(entity, "participants_count", None)
                    if member_count:
                        text += f"멤버 수: {member_count:,}명\n"

                    username = getattr(entity, "username", None)
                    if username:
                        text += f"유저네임: @{username}\n"
                except Exception:
                    pass

            except Exception:
                text += f"ID: {source}\n"
        else:
            text += "❌ 설정되지 않음\n"

        text += "\n─────────────────────────\n"
        text += "1. 소스 채널 설정/변경\n"
        text += "2. 소스 채널 제거\n"
        text += "0. 뒤로 가기\n"

        await event.respond(text)

    async def show_output_menu(self, event):
        """Show target channels menu"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = "output_menu"

        # Get current target channels
        targets = self.config.get_target_channels()

        text = "📤 **출력 채널 설정** (타겟들)\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        text += "현재 타겟 채널들:\n"
        text += "─────────────────────────\n"

        if targets:
            channel_count = 0
            group_count = 0

            for idx, target_id in enumerate(targets, 1):
                try:
                    entity = await self.client.get_entity(target_id)
                    name = getattr(entity, "title", "Unknown")[:30]

                    if isinstance(entity, Channel):
                        if entity.broadcast:
                            text += f"{idx}. 📢 {name}\n"
                            channel_count += 1
                        else:
                            text += f"{idx}. 👥 {name}\n"
                            group_count += 1
                    else:
                        text += f"{idx}. 👥 {name}\n"
                        group_count += 1
                except Exception:
                    text += f"{idx}. ID: {target_id}\n"

            text += f"\n총: 채널 {channel_count}개, 그룹 {group_count}개\n"
        else:
            text += "❌ 설정되지 않음\n"

        text += "\n─────────────────────────\n"
        text += "1. 타겟 채널/그룹 추가\n"
        text += "2. 타겟 채널/그룹 제거\n"
        text += "0. 뒤로 가기\n"

        await event.respond(text)

    async def show_log_menu(self, event):
        """Show log channel menu"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = "log_menu"

        log_channel = self.config.get_log_channel()

        text = "📝 로그 채널 설정\n\n"
        text += "1. 로그 채널 설정\n"
        text += "2. 로그 채널 제거\n"
        text += "0. 뒤로 가기\n\n"
        text += "현재 로그채널:\n"

        if log_channel:
            try:
                entity = await self.client.get_entity(log_channel)
                name = getattr(entity, "title", "Unknown")
                text += f"📝 {name}\n"
            except Exception:
                text += f"• ID: {log_channel}\n"
        else:
            text += "[없음]\n"

        await event.respond(text)

    async def handle_input_menu(self, event, text: str, state: str):
        """Handle input menu selections"""
        user_id = event.sender_id

        if state == "input_menu":
            if text == "1":
                await self.show_channel_list_grouped(event, "input_set")
            elif text == "2":
                self.config.set_source_channel(None)
                await event.respond("✅ 소스 채널이 제거되었습니다.")
                await self.show_input_menu(event)

        elif state == "input_set":
            await self.handle_input_set(event, text)

    async def handle_output_menu(self, event, text: str, state: str):
        """Handle output menu selections"""
        user_id = event.sender_id

        if state == "output_menu":
            if text == "1":
                await self.show_channel_list_grouped(event, "output_add")
            elif text == "2":
                await self.show_output_remove_list(event)

        elif state == "output_add":
            await self.handle_output_add(event, text)

        elif state == "output_remove":
            await self.handle_output_remove(event, text)

    async def handle_log_menu(self, event, text: str, state: str):
        """Handle log menu selections"""
        user_id = event.sender_id

        if state == "log_menu":
            if text == "1":
                await self.show_channel_list(event, "log_set")
            elif text == "2":
                self.config.set_log_channel(None)
                await event.respond("✅ 로그 채널이 제거되었습니다.")
                await self.show_log_menu(event)

        elif state == "log_set":
            await self.handle_log_set(event, text)

    async def show_channel_list_grouped(self, event, next_state: str):
        """Show channels and groups separately for selection"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = next_state

        channels = []
        groups = []

        # Get all dialogs and separate channels from groups
        async for dialog in self.client.iter_dialogs():
            if isinstance(dialog.entity, Channel):
                if dialog.entity.broadcast:
                    channels.append(dialog.entity)
                elif dialog.entity.megagroup:
                    groups.append(dialog.entity)
            elif isinstance(dialog.entity, Chat):
                groups.append(dialog.entity)

        if not channels and not groups:
            await event.respond("가입한 채널/그룹이 없습니다.")
            await self.parent.show_main_menu(event)
            return

        all_entities = []

        # Adjust title based on context
        if next_state == "input_set":
            text = "소스로 설정할 채널/그룹 선택:\n"
        else:
            text = "타겟으로 추가할 채널/그룹 선택:\n"

        text += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Show channels first
        if channels:
            text += "📢 **채널 목록**\n"
            text += "─────────────────────────\n"
            for i, ch in enumerate(channels[:15], 1):
                all_entities.append(ch)
                name = getattr(ch, "title", "Unknown")[:30]
                # Add member count if available
                try:
                    member_count = getattr(ch, "participants_count", None)
                    if member_count:
                        text += f"{i:2}. {name} ({member_count:,}명)\n"
                    else:
                        text += f"{i:2}. {name}\n"
                except Exception:
                    text += f"{i:2}. {name}\n"

        # Show groups
        if groups:
            if channels:
                text += "\n"
            text += "👥 **그룹 목록**\n"
            text += "─────────────────────────\n"
            start_idx = len(all_entities) + 1
            for gr in groups[:15]:
                all_entities.append(gr)
                name = getattr(gr, "title", "Unknown")[:30]
                # Add member count if available
                try:
                    member_count = getattr(gr, "participants_count", None)
                    if member_count:
                        text += f"{start_idx:2}. {name} ({member_count:,}명)\n"
                    else:
                        text += f"{start_idx:2}. {name}\n"
                except Exception:
                    text += f"{start_idx:2}. {name}\n"
                start_idx += 1

        total = len(all_entities)
        shown_channels = min(len(channels), 15)
        shown_groups = min(len(groups), 15)

        if len(channels) > 15 or len(groups) > 15:
            text += f"\n(채널 {shown_channels}/{len(channels)}개, 그룹 {shown_groups}/{len(groups)}개 표시)\n"

        self.parent.temp_data[user_id] = {"channels": all_entities}
        text += "\n0. 취소"
        await event.respond(text)

    async def show_channel_list(self, event, next_state: str):
        """Show numbered list of channels for output/log"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = next_state

        channels = await self.parent.get_user_channels()

        if not channels:
            await event.respond("가입한 채널/그룹이 없습니다.")
            await self.parent.show_main_menu(event)
            return

        self.parent.temp_data[user_id] = {"channels": channels}

        text = "채널 선택:\n\n"
        for i, ch in enumerate(channels[:20], 1):
            name = getattr(ch, "title", "Unknown")
            entity_type = "📢" if isinstance(ch, Channel) else "👥"
            text += f"{i}. {entity_type} {name}\n"

        text += "\n0. 취소"
        await event.respond(text)

    async def show_output_remove_list(self, event):
        """Show list of target channels to remove"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = "output_remove"

        targets = self.config.get_target_channels()

        if not targets:
            await event.respond("제거할 타겟 채널이 없습니다.")
            await self.show_output_menu(event)
            return

        text = "제거할 타겟 채널 선택:\n\n"

        for i, target_id in enumerate(targets, 1):
            try:
                entity = await self.client.get_entity(target_id)
                name = getattr(entity, "title", "Unknown")
                text += f"{i}. 📤 {name}\n"
            except Exception:
                text += f"{i}. ID: {target_id}\n"

        self.parent.temp_data[user_id] = {"targets": targets}
        text += "\n0. 취소"
        await event.respond(text)

    async def handle_input_set(self, event, text: str):
        """Handle source channel setting"""
        user_id = event.sender_id

        try:
            idx = int(text) - 1
            channels = self.parent.temp_data[user_id]["channels"]

            if 0 <= idx < len(channels):
                entity = channels[idx]
                channel_id = self.parent.get_proper_channel_id(entity)

                self.config.set_source_channel(channel_id)
                await event.respond(
                    f"✅ 소스 채널 설정됨: {getattr(entity, 'title', 'Unknown')}"
                )
                await self.show_input_menu(event)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")

    async def handle_output_add(self, event, text: str):
        """Handle target channel addition"""
        user_id = event.sender_id

        if user_id not in self.parent.temp_data:
            await self.show_output_menu(event)
            return

        try:
            idx = int(text) - 1
            channels = self.parent.temp_data[user_id]["channels"]

            if 0 <= idx < len(channels):
                entity = channels[idx]
                channel_id = self.parent.get_proper_channel_id(entity)

                if self.config.add_target_channel(channel_id):
                    entity_type = "채널" if isinstance(entity, Channel) else "그룹"
                    await event.respond(
                        f"✅ 타겟 {entity_type} 추가됨: {getattr(entity, 'title', 'Unknown')}"
                    )
                else:
                    await event.respond("⚠️ 이미 추가된 채널입니다.")

                await self.show_output_menu(event)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")

    async def handle_output_remove(self, event, text: str):
        """Handle target channel removal"""
        user_id = event.sender_id

        if user_id not in self.parent.temp_data:
            await self.show_output_menu(event)
            return

        try:
            idx = int(text) - 1
            targets = self.parent.temp_data[user_id]["targets"]

            if 0 <= idx < len(targets):
                target_id = targets[idx]

                if self.config.remove_target_channel(target_id):
                    await event.respond("✅ 타겟 채널이 제거되었습니다.")
                else:
                    await event.respond("⚠️ 제거 실패")

                await self.show_output_menu(event)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")

    async def handle_log_set(self, event, text: str):
        """Handle log channel setting"""
        user_id = event.sender_id

        try:
            idx = int(text) - 1
            channels = self.parent.temp_data[user_id]["channels"]

            if 0 <= idx < len(channels):
                entity = channels[idx]
                channel_id = self.parent.get_proper_channel_id(entity)

                self.config.set_log_channel(channel_id)
                await event.respond(
                    f"✅ 로그 채널 설정됨: {getattr(entity, 'title', 'Unknown')}"
                )
                await self.show_log_menu(event)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")
