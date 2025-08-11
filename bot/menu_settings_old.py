"""
Settings menu handlers for input, output, and log channels
"""

import logging

from telethon.tl.types import Channel, Chat

logger = logging.getLogger('SettingsMenu')


class SettingsMenu:
    """Handle all settings-related menus"""

    def __init__(self, parent):
        self.parent = parent
        self.client = parent.client
        self.config = parent.config

    async def show_input_menu(self, event):
        """Show input channel menu"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = 'input_menu'

        mappings = self.config.get_all_mappings()

        text = "1. 입력 채널 추가\n"
        text += "2. 입력 채널 제거\n"
        text += "0. 뒤로 가기\n\n"
        text += "현재 입력채널\n"

        if mappings:
            for source_id in mappings:
                try:
                    entity = await self.client.get_entity(source_id)
                    name = getattr(entity, 'title', 'Unknown')
                    text += f"• {name}\n"
                except Exception:
                    text += f"• ID: {source_id}\n"
        else:
            text += "[없음]\n"

        await event.respond(text)

    async def show_output_menu(self, event):
        """Show output channel menu"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = 'output_menu'

        mappings = self.config.get_all_mappings()

        text = "1. 출력 채널 설정\n"
        text += "2. 출력 채널 제거\n"
        text += "0. 뒤로 가기\n\n"
        text += "현재 연결상태\n"

        if mappings:
            for source_id, target_id in mappings.items():
                try:
                    source = await self.client.get_entity(source_id)
                    source_name = getattr(source, 'title', 'Unknown')

                    if target_id:
                        target = await self.client.get_entity(target_id)
                        target_name = getattr(target, 'title', 'Unknown')
                        text += f"• {source_name} → {target_name}\n"
                    else:
                        text += f"• {source_name} → [미설정]\n"
                except Exception:
                    if target_id:
                        text += f"• {source_id} → {target_id}\n"
                    else:
                        text += f"• {source_id} → [미설정]\n"
        else:
            text += "[없음]\n"

        await event.respond(text)

    async def show_log_menu(self, event):
        """Show log channel menu"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = 'log_menu'

        log_channel = self.config.get_log_channel()

        text = "1. 로그 채널 설정\n"
        text += "2. 로그 채널 제거\n"
        text += "0. 뒤로 가기\n\n"
        text += "현재 로그채널\n"

        if log_channel:
            try:
                entity = await self.client.get_entity(log_channel)
                name = getattr(entity, 'title', 'Unknown')
                text += f"• {name}\n"
            except Exception:
                text += f"• ID: {log_channel}\n"
        else:
            text += "[없음]\n"

        await event.respond(text)

    async def handle_input_menu(self, event, text: str, state: str):
        """Handle input menu selections"""
        user_id = event.sender_id

        if state == 'input_menu':
            if text == '1':
                await self.show_channel_list(event, 'input_add')
            elif text == '2':
                await self.show_input_remove_list(event)

        elif state == 'input_add':
            await self.handle_input_add(event, text)

        elif state == 'input_remove':
            await self.handle_input_remove(event, text)

    async def handle_output_menu(self, event, text: str, state: str):
        """Handle output menu selections"""
        user_id = event.sender_id

        if state == 'output_menu':
            if text == '1':
                await self.show_output_source_list(event)
            elif text == '2':
                await self.show_output_remove_list(event)

        elif state == 'output_select_source':
            await self.handle_output_source_select(event, text)

        elif state == 'output_select_target':
            await self.handle_output_target_select(event, text)

        elif state == 'output_remove':
            await self.handle_output_remove(event, text)

    async def handle_log_menu(self, event, text: str, state: str):
        """Handle log menu selections"""
        user_id = event.sender_id

        if state == 'log_menu':
            if text == '1':
                await self.show_channel_list(event, 'log_set')
            elif text == '2':
                self.config.set_log_channel(None)
                await event.respond("로그 채널이 제거되었습니다.")
                await self.show_log_menu(event)

        elif state == 'log_set':
            await self.handle_log_set(event, text)

    async def show_channel_list(self, event, next_state: str):
        """Show numbered list of channels"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = next_state

        channels = await self.parent.get_user_channels()

        if not channels:
            await event.respond("가입한 채널/그룹이 없습니다.")
            await self.parent.show_main_menu(event)
            return

        self.parent.temp_data[user_id] = {'channels': channels}

        text = "채널 선택:\n\n"
        for i, ch in enumerate(channels[:20], 1):
            name = getattr(ch, 'title', 'Unknown')
            text += f"{i}. {name}\n"

        text += "\n0. 취소"
        await event.respond(text)

    async def show_input_remove_list(self, event):
        """Show list of input channels to remove"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = 'input_remove'

        mappings = self.config.get_all_mappings()

        if not mappings:
            await event.respond("제거할 입력 채널이 없습니다.")
            await self.show_input_menu(event)
            return

        sources = []
        text = "제거할 채널 선택:\n\n"

        for i, source_id in enumerate(mappings.keys(), 1):
            sources.append(source_id)
            try:
                entity = await self.client.get_entity(source_id)
                name = getattr(entity, 'title', 'Unknown')
                text += f"{i}. {name}\n"
            except Exception:
                text += f"{i}. ID: {source_id}\n"

        self.parent.temp_data[user_id] = {'sources': sources}
        text += "\n0. 취소"
        await event.respond(text)

    async def show_output_source_list(self, event):
        """Show list of input channels to set output for"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = 'output_select_source'

        mappings = self.config.get_all_mappings()

        if not mappings:
            await event.respond("먼저 입력 채널을 추가하세요.")
            await self.show_output_menu(event)
            return

        sources = []
        text = "출력을 설정할 입력 채널 선택:\n\n"

        for i, (source_id, target_id) in enumerate(mappings.items(), 1):
            sources.append(source_id)
            try:
                entity = await self.client.get_entity(source_id)
                name = getattr(entity, 'title', 'Unknown')
                status = "✓" if target_id else "✗"
                text += f"{i}. [{status}] {name}\n"
            except Exception:
                status = "✓" if target_id else "✗"
                text += f"{i}. [{status}] ID: {source_id}\n"

        self.parent.temp_data[user_id] = {'sources': sources}
        text += "\n0. 취소"
        await event.respond(text)

    async def show_output_remove_list(self, event):
        """Show list of output channels to remove"""
        user_id = event.sender_id
        self.parent.user_states[user_id] = 'output_remove'

        mappings = {k: v for k, v in self.config.get_all_mappings().items() if v is not None}

        if not mappings:
            await event.respond("제거할 출력 연결이 없습니다.")
            await self.show_output_menu(event)
            return

        sources = []
        text = "제거할 출력 연결 선택:\n\n"

        for i, (source_id, target_id) in enumerate(mappings.items(), 1):
            sources.append(source_id)
            try:
                source = await self.client.get_entity(source_id)
                target = await self.client.get_entity(target_id)
                text += f"{i}. {getattr(source, 'title', 'Unknown')} → {getattr(target, 'title', 'Unknown')}\n"
            except Exception:
                text += f"{i}. {source_id} → {target_id}\n"

        self.parent.temp_data[user_id] = {'sources': sources}
        text += "\n0. 취소"
        await event.respond(text)

    async def handle_input_add(self, event, text: str):
        """Handle input channel addition"""
        user_id = event.sender_id

        if user_id not in self.parent.temp_data:
            await self.show_input_menu(event)
            return

        try:
            idx = int(text) - 1
            channels = self.parent.temp_data[user_id]['channels']

            if 0 <= idx < len(channels):
                entity = channels[idx]
                channel_id = self.parent.get_proper_channel_id(entity)

                if self.config.add_mapping(channel_id, None):
                    await event.respond(f"✅ 입력 채널 추가됨: {getattr(entity, 'title', 'Unknown')}")
                else:
                    await event.respond("⚠️ 이미 추가된 채널입니다.")

                await self.show_input_menu(event)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")

    async def handle_input_remove(self, event, text: str):
        """Handle input channel removal"""
        user_id = event.sender_id

        if user_id not in self.parent.temp_data:
            await self.show_input_menu(event)
            return

        try:
            idx = int(text) - 1
            sources = self.parent.temp_data[user_id]['sources']

            if 0 <= idx < len(sources):
                source_id = sources[idx]

                if self.config.remove_mapping(source_id):
                    await event.respond("✅ 입력 채널이 제거되었습니다.")
                else:
                    await event.respond("⚠️ 제거 실패")

                await self.show_input_menu(event)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")

    async def handle_output_source_select(self, event, text: str):
        """Handle output source selection"""
        user_id = event.sender_id

        try:
            idx = int(text) - 1
            sources = self.parent.temp_data[user_id]['sources']

            if 0 <= idx < len(sources):
                self.parent.temp_data[user_id]['selected_source'] = sources[idx]
                await self.show_channel_list(event, 'output_select_target')
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")

    async def handle_output_target_select(self, event, text: str):
        """Handle output target selection"""
        user_id = event.sender_id

        try:
            idx = int(text) - 1
            channels = self.parent.temp_data[user_id]['channels']

            if 0 <= idx < len(channels):
                entity = channels[idx]
                target_id = self.parent.get_proper_channel_id(entity)
                source_id = self.parent.temp_data[user_id]['selected_source']

                # Update mapping
                self.config.remove_mapping(source_id)
                self.config.add_mapping(source_id, target_id)

                await event.respond(f"✅ 출력 채널 설정됨: {getattr(entity, 'title', 'Unknown')}")
                await self.show_output_menu(event)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")

    async def handle_output_remove(self, event, text: str):
        """Handle output removal"""
        user_id = event.sender_id

        try:
            idx = int(text) - 1
            sources = self.parent.temp_data[user_id]['sources']

            if 0 <= idx < len(sources):
                source_id = sources[idx]

                # Set target to None
                self.config.remove_mapping(source_id)
                self.config.add_mapping(source_id, None)

                await event.respond("✅ 출력 연결이 제거되었습니다.")
                await self.show_output_menu(event)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")

    async def handle_log_set(self, event, text: str):
        """Handle log channel setting"""
        user_id = event.sender_id

        try:
            idx = int(text) - 1
            channels = self.parent.temp_data[user_id]['channels']

            if 0 <= idx < len(channels):
                entity = channels[idx]
                channel_id = self.parent.get_proper_channel_id(entity)

                self.config.set_log_channel(channel_id)
                await event.respond(f"✅ 로그 채널 설정됨: {getattr(entity, 'title', 'Unknown')}")
                await self.show_log_menu(event)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")
