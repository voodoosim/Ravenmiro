"""
Sync menu handlers for channel synchronization
"""

import logging

from telethon.tl.types import Channel

logger = logging.getLogger('SyncMenu')


class SyncMenu:
    """Handle sync-related operations"""

    def __init__(self, parent):
        self.parent = parent
        self.client = parent.client
        self.config = parent.config
        self.mirror_engine = parent.mirror_engine

    async def handle_sync_command(self, event):
        """Handle .동기화 command"""
        user_id = event.sender_id

        # Show available channels for sync
        self.parent.user_states[user_id] = 'sync_select_source'

        channels = await self.parent.get_user_channels()

        if not channels:
            await event.respond("동기화할 채널이 없습니다.")
            del self.parent.user_states[user_id]
            return

        self.parent.temp_data[user_id] = {'channels': channels}

        text = "🔄 동기화 - 소스 선택\n\n"
        for i, ch in enumerate(channels[:15], 1):
            name = getattr(ch, 'title', 'Unknown')
            name = name[:20] if len(name) > 20 else name
            icon = "📢" if isinstance(ch, Channel) and ch.broadcast else "👥"
            text += f"{i}. {icon} {name}\n"
        
        if len(channels) > 15:
            text += f"\n... 외 {len(channels) - 15}개"

        text += "\n\n0. 취소"
        await event.respond(text)

    async def handle_sync_menu(self, event, text: str, state: str):
        """Handle sync menu states"""
        user_id = event.sender_id

        if state == 'sync_select_source':
            await self.handle_sync_source_select(event, text)

        elif state == 'sync_select_target':
            await self.handle_sync_target_select(event, text)

        elif state == 'sync_confirm':
            await self.handle_sync_confirm(event, text)

    async def handle_sync_source_select(self, event, text: str):
        """Handle source channel selection for sync"""
        user_id = event.sender_id

        try:
            idx = int(text) - 1
            channels = self.parent.temp_data[user_id]['channels']

            if 0 <= idx < len(channels):
                source = channels[idx]
                self.parent.temp_data[user_id]['sync_source'] = source

                # Now select target
                self.parent.user_states[user_id] = 'sync_select_target'

                text = "타겟 채널 선택:\n\n"
                for i, ch in enumerate(channels[:20], 1):
                    name = getattr(ch, 'title', 'Unknown')
                    text += f"{i}. {name}\n"

                text += "\n0. 취소"
                await event.respond(text)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")

    async def handle_sync_target_select(self, event, text: str):
        """Handle target channel selection for sync"""
        user_id = event.sender_id

        try:
            idx = int(text) - 1
            channels = self.parent.temp_data[user_id]['channels']

            if 0 <= idx < len(channels):
                target = channels[idx]
                source = self.parent.temp_data[user_id]['sync_source']

                if source.id == target.id:
                    await event.respond("⚠️ 소스와 타겟이 같을 수 없습니다.")
                    return

                self.parent.temp_data[user_id]['sync_target'] = target

                # Show confirmation
                self.parent.user_states[user_id] = 'sync_confirm'

                source_name = getattr(source, 'title', 'Unknown')
                target_name = getattr(target, 'title', 'Unknown')

                text = "동기화 확인\n\n"
                text += f"소스: {source_name}\n"
                text += f"타겟: {target_name}\n\n"
                text += "⚠️ 타겟 채널의 모든 메시지가 삭제되고\n"
                text += "소스 채널의 전체 내용으로 교체됩니다.\n\n"
                text += "1. 계속하기\n"
                text += "0. 취소"

                await event.respond(text)
        except (ValueError, IndexError):
            await event.respond("올바른 번호를 입력하세요.")

    async def handle_sync_confirm(self, event, text: str):
        """Handle sync confirmation"""
        user_id = event.sender_id

        if text == '1':
            source = self.parent.temp_data[user_id]['sync_source']
            target = self.parent.temp_data[user_id]['sync_target']

            source_id = self.parent.get_proper_channel_id(source)
            target_id = self.parent.get_proper_channel_id(target)

            await event.respond("동기화를 시작합니다... 시간이 걸릴 수 있습니다.")

            try:
                # Perform sync
                total = await self.sync_channel_history(source_id, target_id)
                await event.respond(f"✅ 동기화 완료! {total}개 메시지 복사됨")
            except Exception as e:
                await event.respond(f"❌ 동기화 실패: {e!s}")

            # Clear state
            del self.parent.user_states[user_id]
            if user_id in self.parent.temp_data:
                del self.parent.temp_data[user_id]
        else:
            await event.respond("동기화가 취소되었습니다.")
            del self.parent.user_states[user_id]

    async def sync_channel_history(self, source_id: int, target_id: int) -> int:
        """Sync entire channel history from source to target"""
        total = 0

        try:
            # Get source and target entities
            source = await self.client.get_entity(source_id)
            target = await self.client.get_entity(target_id)

            # Clear target channel (optional - you might want to skip this)
            # This would require admin permissions in the target channel

            # Copy all messages from source to target
            async for message in self.client.iter_messages(source, reverse=True):
                try:
                    if message.text:
                        # Text message
                        await self.client.send_message(target, message.text)
                    elif message.media:
                        # Media message
                        await self.client.send_file(
                            target,
                            message.media,
                            caption=message.text or ""
                        )

                    total += 1

                    # Progress update every 100 messages
                    if total % 100 == 0:
                        logger.info(f"Synced {total} messages...")

                except Exception as e:
                    logger.error(f"Failed to sync message: {e}")
                    continue

            return total

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise
