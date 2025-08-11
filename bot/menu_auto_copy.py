"""
Auto copy handlers for automatic source to target copying
"""

import logging
import asyncio

from telethon.errors import FloodWaitError
from telethon.tl.types import Channel, Chat

logger = logging.getLogger("AutoCopy")


class AutoCopyMenu:
    """Handle automatic copy operations"""

    def __init__(self, parent):
        self.parent = parent
        self.client = parent.client
        self.config = parent.config
        self.mirror_engine = parent.mirror_engine
        self.copying_active = False
        self.current_task = None

    async def handle_copy_command(self, event):
        """Handle .카피 command - copy from source to targets with optional start link"""
        user_id = event.sender_id

        # Get configured source and target channels
        source = self.config.get_source_channel()
        targets = self.config.get_target_channels()

        if not source or not targets:
            await event.respond(
                "❌ 소스 또는 타겟 채널이 설정되지 않았습니다.\n"
                ".설정 에서 입력/출력 채널을 먼저 설정하세요."
            )
            return

        # Ask for start link
        self.parent.user_states[user_id] = "auto_copy_link"
        self.parent.temp_data[user_id] = {"source": source, "targets": targets}

        text = "📋 복사 준비\n\n"

        # Show source channel
        try:
            source_entity = await self.client.get_entity(source)
            source_name = getattr(source_entity, "title", "Unknown")
            text += f"📥 소스: {source_name}\n\n"
        except Exception:
            text += f"📥 소스 ID: {source}\n\n"

        # Show target channels
        text += "📤 타겟 채널들:\n"
        for target_id in targets:
            try:
                target_entity = await self.client.get_entity(target_id)
                target_name = getattr(target_entity, "title", "Unknown")
                text += f"  • {target_name}\n"
            except Exception:
                text += f"  • ID: {target_id}\n"

        text += "\n시작할 메시지 링크를 입력하세요.\n"
        text += "(선택사항 - 입력 안하면 처음부터)\n\n"
        text += "예: https://t.me/channel/123\n\n"
        text += "Enter - 처음부터 시작\n"
        text += "0 - 취소"

        await event.respond(text)

    async def handle_kakashi_command(self, event):
        """Handle .카카시 command - immediate copy start"""
        # Get configured source and target channels
        source = self.config.get_source_channel()
        targets = self.config.get_target_channels()

        if not source or not targets:
            await event.respond(
                "❌ 설정된 소스→타겟 채널이 없습니다.\n"
                ".설정 에서 입력/출력 채널을 먼저 설정하세요."
            )
            return

        if self.copying_active:
            await event.respond("⚠️ 이미 복사가 진행 중입니다.")
            return

        await event.respond("🥷 카카시 모드! 소스→타겟 복사를 시작합니다...")

        # Start copying source to all targets
        self.copying_active = True
        self.current_task = asyncio.create_task(
            self.copy_to_all_targets(event, source, targets)
        )

    async def handle_stop_command(self, event):
        """Handle .정지 command - stop all operations"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            self.copying_active = False
            await event.respond("⛔ 모든 작업이 중단되었습니다.")
        else:
            await event.respond("❌ 실행 중인 작업이 없습니다.")

    async def handle_auto_copy_menu(self, event, text: str, state: str):
        """Handle auto copy menu states"""
        user_id = event.sender_id

        if state == "auto_copy_link":
            await self.handle_start_link(event, text)

    # Removed - no longer needed since we don't select source channels

    async def handle_start_link(self, event, text: str):
        """Handle start link input or begin copy"""
        user_id = event.sender_id

        if text == "0":
            await event.respond("취소되었습니다.")
            del self.parent.user_states[user_id]
            return

        source_id = self.parent.temp_data[user_id]["source"]
        target_ids = self.parent.temp_data[user_id]["targets"]
        start_msg_id = None

        # Parse link if provided
        if text and text.startswith("https://t.me/"):
            try:
                # Extract message ID from link
                parts = text.split("/")
                if len(parts) >= 5:
                    start_msg_id = int(parts[-1])
            except Exception:
                pass

        # Start copying
        if self.copying_active:
            await event.respond("⚠️ 이미 복사가 진행 중입니다.")
            return

        self.copying_active = True
        await event.respond(
            f"복사를 시작합니다...\n"
            f"시작 메시지: {start_msg_id if start_msg_id else '처음부터'}\n"
            f"타겟 채널: {len(target_ids)}개\n"
            f"중단하려면 .정지 입력"
        )

        # Clear state
        del self.parent.user_states[user_id]
        if user_id in self.parent.temp_data:
            del self.parent.temp_data[user_id]

        # Start copy task
        self.current_task = asyncio.create_task(
            self.copy_to_multiple_targets(source_id, target_ids, start_msg_id)
        )

    async def copy_to_all_targets(self, event, source_id, target_ids):
        """Copy source channel to all target channels FROM THE BEGINNING"""
        total_copied = 0

        try:
            source = await self.client.get_entity(source_id)
            source_name = getattr(source, "title", "Unknown")

            await event.respond(
                f"🥷 카카시 모드 시작!\n"
                f"📥 소스: {source_name}\n"
                f"📤 타겟: {len(target_ids)}개 채널\n"
                f"처음부터 전체 복사를 시작합니다..."
            )

            # Use copy_to_multiple_targets with start_msg_id=None for full copy
            total_copied = await self.copy_to_multiple_targets(
                source_id, target_ids, start_msg_id=None
            )

        except Exception as e:
            logger.error(f"Failed to copy: {e}")
            await event.respond(f"❌ 복사 중 오류 발생: {e}")

        finally:
            self.copying_active = False
            await event.respond(
                f"🏁 카카시 모드 완료! 총 {total_copied}개 메시지 복사됨"
            )

    async def copy_to_multiple_targets(
        self, source_id: int, target_ids: list, start_msg_id: int | None = None
    ):
        """Copy from source to multiple targets from specific point or beginning"""
        total_messages = 0
        total_targets = len(target_ids)

        try:
            source = await self.client.get_entity(source_id)

            # Iterate messages from start point
            async for message in self.client.iter_messages(
                source, min_id=start_msg_id if start_msg_id else 0, reverse=True
            ):
                if not self.copying_active:
                    break

                # Send to all targets
                for target_id in target_ids:
                    try:
                        target = await self.client.get_entity(target_id)

                        if message.text:
                            await self.client.send_message(target, message.text)
                        elif message.media:
                            await self.client.send_file(
                                target, message.media, caption=message.text or ""
                            )

                    except FloodWaitError as e:
                        logger.warning(
                            f"Flood wait for target {target_id}: {e.seconds}s"
                        )
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        logger.error(f"Failed to copy to target {target_id}: {e}")

                total_messages += 1

                # Progress update
                if total_messages % 100 == 0:
                    logger.info(
                        f"Copied {total_messages} messages to {total_targets} targets..."
                    )

                # Avoid flood
                if total_messages % 10 == 0:
                    await asyncio.sleep(1)

            return total_messages * total_targets

        except asyncio.CancelledError:
            logger.info("Copy operation cancelled")
            raise
        except Exception as e:
            logger.error(f"Copy failed: {e}")
            return total_messages
        finally:
            self.copying_active = False

    async def copy_new_messages(self, source_id: int, target_id: int) -> int:
        """Copy only new messages since last copy"""
        # This would check for new messages only
        # For now, just copy recent messages
        total = 0

        try:
            source = await self.client.get_entity(source_id)
            target = await self.client.get_entity(target_id)

            # Get recent messages (last 100)
            async for message in self.client.iter_messages(
                source, limit=100, reverse=True
            ):
                if not self.copying_active:
                    break

                try:
                    # Check if already copied (would need proper tracking)
                    # For now, just copy

                    if message.text:
                        await self.client.send_message(target, message.text)
                    elif message.media:
                        await self.client.send_file(
                            target, message.media, caption=message.text or ""
                        )

                    total += 1

                    if total % 10 == 0:
                        await asyncio.sleep(1)

                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    logger.error(f"Copy error: {e}")

            return total

        except Exception as e:
            logger.error(f"Copy new messages failed: {e}")
            return total
