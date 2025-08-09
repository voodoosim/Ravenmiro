"""
Mirror Engine Module
Core mirroring logic with copy restriction bypass
"""

import asyncio
import logging
import io
from typing import Optional, Set

from telethon import TelegramClient, events
from telethon.tl.types import (
    Message, MessageMediaPhoto, MessageMediaDocument,
    MessageMediaWebPage, MessageMediaPoll, MessageMediaGeo,
    DocumentAttributeVideo, DocumentAttributeAudio,
    DocumentAttributeFilename, DocumentAttributeSticker,
    DocumentAttributeAnimated, MessageService
)
from telethon.errors import FloodWaitError, MediaEmptyError

logger = logging.getLogger('MirrorEngine')


class MirrorEngine:
    """Engine for mirroring messages between Telegram chats with restriction bypass"""
    def __init__(self, client: TelegramClient, config):
        self.client = client
        self.config = config
        self.processing: Set[str] = set()

    async def handle_message(self, event: events.NewMessage.Event):
        """Handle new message event"""
        if not self.config.get_option('mirror_enabled'):
            return

        message = event.message
        source_chat = message.chat_id

        target_chat = self.config.get_mapping(source_chat)
        if not target_chat:
            return

        msg_id = f"{source_chat}_{message.id}"
        if msg_id in self.processing:
            return

        self.processing.add(msg_id)

        try:
            if isinstance(message, MessageService):
                return

            target_msg = await self._mirror_message(message, target_chat)

            if target_msg:
                self.config.cache_message(message.id, target_msg.id, source_chat)
                self.config.update_stats('messages_mirrored')
                logger.info("Mirrored message %s → %s", message.id, target_msg.id)

        except FloodWaitError as e:
            logger.warning("Flood wait: %ss", e.seconds)
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error("Mirror error: %s", e)
            self.config.update_stats('errors')
        finally:
            self.processing.discard(msg_id)

    async def _mirror_message(
        self, message: Message, target_chat: int
    ) -> Optional[Message]:  # type: ignore
        """Mirror complete message with restriction bypass"""
        try:
            if message.media and self.config.get_option('bypass_restriction'):
                return await self._mirror_restricted_media(message, target_chat)

            elif message.media and self.config.get_option('mirror_media'):
                return await self._mirror_media(message, target_chat)

            elif message.text and self.config.get_option('mirror_text'):  # type: ignore
                return await self.client.send_message(
                    target_chat,
                    message.text,  # type: ignore
                    formatting_entities=message.entities,
                    link_preview=isinstance(message.media, MessageMediaWebPage)
                )

        except Exception as e:
            logger.error("Failed to mirror message: %s", e)
            return None

    async def _mirror_restricted_media(
        self, message: Message, target_chat: int
    ) -> Optional[Message]:  # type: ignore
        """Mirror media with copy restriction bypass"""
        try:
            if isinstance(message.media, MessageMediaPhoto):
                photo_bytes = await self.client.download_media(message, file=io.BytesIO())

                if photo_bytes:
                    self.config.update_stats('media_mirrored')
                    return await self.client.send_file(
                        target_chat,
                        photo_bytes,
                        caption=message.text,  # type: ignore
                        formatting_entities=message.entities,
                        force_document=False
                    )

            elif isinstance(message.media, MessageMediaDocument):
                attributes = getattr(message.media.document, 'attributes', []) if message.media.document else []
                is_video = any(isinstance(a, DocumentAttributeVideo) for a in attributes)
                is_audio = any(isinstance(a, DocumentAttributeAudio) for a in attributes)
                is_sticker = any(isinstance(a, DocumentAttributeSticker) for a in attributes)
                is_gif = any(isinstance(a, DocumentAttributeAnimated) for a in attributes)

                document_bytes = await self.client.download_media(message, file=io.BytesIO())

                if document_bytes:
                    filename = None
                    for attr in attributes:
                        if isinstance(attr, DocumentAttributeFilename):
                            filename = attr.file_name
                            break

                    self.config.update_stats('media_mirrored')

                    if isinstance(document_bytes, bytes):
                        file_handle = io.BytesIO(document_bytes)
                        if filename:
                            file_handle.name = filename  # type: ignore
                    else:
                        file_handle = document_bytes

                    return await self.client.send_file(
                        target_chat,
                        file_handle,
                        caption=message.text,  # type: ignore
                        formatting_entities=message.entities,
                        attributes=attributes,
                        force_document=not (is_video or is_sticker or is_gif),
                        video_note=(
                            is_video and getattr(attributes[0], 'round_message', False)
                            if attributes else False
                        ),
                        voice_note=(
                            is_audio and getattr(attributes[0], 'voice', False)
                            if attributes else False
                        )
                    )

            elif isinstance(message.media, MessageMediaPoll):
                return await self.client.send_message(
                    target_chat,
                    f"📊 Poll: {message.media.poll.question}\n"
                    f"(Polls cannot be forwarded directly)"
                )

            elif isinstance(message.media, MessageMediaGeo):
                return await self.client.send_message(
                    target_chat,
                    f"📍 Location: {message.media.geo.lat}, {message.media.geo.long}"  # type: ignore
                )

            else:
                return await self._mirror_media(message, target_chat)

        except MediaEmptyError:
            logger.warning("Media is empty, sending text only")
            if message.text:  # type: ignore
                return await self.client.send_message(
                    target_chat,
                    message.text,  # type: ignore
                    formatting_entities=message.entities
                )
        except Exception as e:
            logger.error("Restricted media mirror failed: %s", e)
            return None

    async def _mirror_media(self, message: Message, target_chat: int) -> Optional[Message]:
        """Mirror media normally (when not restricted)"""
        try:
            if message.media:
                return await self.client.send_file(
                    target_chat,
                    message.media,  # type: ignore
                    caption=message.text,  # type: ignore
                    formatting_entities=message.entities
                )
            return None
        except Exception as e:
            logger.error("Media mirror failed: %s", e)
            return None

    async def handle_edit(self, event: events.MessageEdited.Event):
        """Handle message edit event"""
        if not self.config.get_option('mirror_edits'):
            return

        message = event.message
        source_chat = message.chat_id

        target_chat = self.config.get_mapping(source_chat)
        if not target_chat:
            return

        target_msg_id = self.config.get_cached_message(message.id, source_chat)
        if not target_msg_id:
            return

        try:
            await self.client.edit_message(
                target_chat,
                target_msg_id,
                message.text,  # type: ignore
                formatting_entities=message.entities,
                link_preview=isinstance(message.media, MessageMediaWebPage)
            )
            logger.info("Edited message %s → %s", message.id, target_msg_id)
        except Exception as e:
            logger.error("Edit failed: %s", e)

    async def handle_delete(self, event: events.MessageDeleted.Event):
        """Handle message delete event"""
        if not self.config.get_option('mirror_deletes'):
            return

        for msg_id in event.deleted_ids:
            source_chat = event.chat_id if hasattr(event, 'chat_id') else None
            if not source_chat:
                continue

            target_chat = self.config.get_mapping(source_chat)
            if not target_chat:
                continue

            target_msg_id = self.config.get_cached_message(msg_id, source_chat)
            if not target_msg_id:
                continue

            try:
                await self.client.delete_messages(target_chat, [target_msg_id])
                logger.info("Deleted message %s → %s", msg_id, target_msg_id)
            except Exception as e:
                logger.error("Delete failed: %s", e)

    async def handle_album(self, event: events.Album.Event):
        """Handle album (grouped media) event"""
        if not self.config.get_option('mirror_enabled'):
            return

        source_chat = event.chat_id
        target_chat = self.config.get_mapping(source_chat)
        if not target_chat:
            return

        try:
            media_list = []

            for message in event.messages:
                if self.config.get_option('bypass_restriction'):
                    if isinstance(message.media, MessageMediaPhoto):
                        photo_bytes = await self.client.download_media(message, file=io.BytesIO())
                        if photo_bytes:
                            media_list.append(photo_bytes)
                    elif isinstance(message.media, MessageMediaDocument):
                        doc_bytes = await self.client.download_media(message, file=io.BytesIO())
                        if doc_bytes:
                            media_list.append(doc_bytes)
                else:
                    media_list.append(message.media)

            if media_list:
                caption = (
                    event.original_update.message.message  # type: ignore
                    if hasattr(event.original_update, 'message')
                    else ""
                )
                sent_messages = await self.client.send_file(
                    target_chat,
                    media_list,
                    caption=caption or ""
                )

                if isinstance(sent_messages, list):
                    for i, msg in enumerate(event.messages):
                        if i < len(sent_messages):
                            self.config.cache_message(msg.id, sent_messages[i].id, source_chat)

                self.config.update_stats('media_mirrored', len(media_list))
                logger.info("Mirrored album with %s items", len(media_list))

        except Exception as e:
            logger.error("Album mirror failed: %s", e)
            self.config.update_stats('errors')

    async def save_state(self):
        """Save engine state"""
        self.config.save()
        logger.info("Mirror engine state saved")

    def get_status(self) -> dict:
        """Get engine status"""
        mappings = self.config.get_all_mappings()
        stats = self.config.get_stats()

        return {
            'enabled': self.config.get_option('mirror_enabled'),
            'mappings_count': len(mappings),
            'processing_count': len(self.processing),
            'stats': stats,
            'options': {
                'text': self.config.get_option('mirror_text'),
                'media': self.config.get_option('mirror_media'),
                'edits': self.config.get_option('mirror_edits'),
                'deletes': self.config.get_option('mirror_deletes'),
                'bypass': self.config.get_option('bypass_restriction')
            }
        }
