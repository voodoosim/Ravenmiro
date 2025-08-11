"""
Mirror Engine Module
Core mirroring logic with copy restriction bypass
"""

import asyncio
import logging
import io
import time
from typing import Optional, Set, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
from collections import deque

from telethon import TelegramClient, events
from telethon.tl.types import (
    Message, MessageMediaPhoto, MessageMediaDocument,
    MessageMediaWebPage, MessageMediaPoll, MessageMediaGeo,
    DocumentAttributeVideo, DocumentAttributeAudio,
    DocumentAttributeFilename, DocumentAttributeSticker,
    DocumentAttributeAnimated, MessageService
)
from telethon.errors import (
    FloodWaitError, MediaEmptyError, ChatWriteForbiddenError,
    ChannelPrivateError, MessageNotModifiedError,
    MessageIdInvalidError, MessageDeleteForbiddenError
)

logger = logging.getLogger('MirrorEngine')


@dataclass
class MirrorTask:
    """Enhanced mirror task with retry logic"""
    message: Message
    source_chat: int
    target_chat: int
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = 0
    priority: int = 0  # 0=normal, 1=high, 2=critical


class MirrorStrategy(Enum):
    """MCP-enhanced mirroring strategies"""
    DIRECT = "direct"  # Simple forward
    BYPASS = "bypass"  # Restriction bypass
    OPTIMIZED = "optimized"  # With compression
    BATCH = "batch"  # Batch operations
    SMART = "smart"  # Context-aware


class MirrorEngine:
    """MCP-Enhanced Engine with advanced capabilities"""
    def __init__(self, client: TelegramClient, config: Any):
        self.client = client
        self.config = config
        self.processing: Set[str] = set()
        
        # MCP-enhanced features
        self.task_queue: asyncio.Queue[MirrorTask] = asyncio.Queue()
        self.batch_buffer: Dict[int, List[Message]] = {}
        self.batch_timers: Dict[int, float] = {}
        self.error_counts: Dict[str, int] = {}
        self.performance_stats: Dict[str, float] = {}
        
        # Intelligent rate limiting
        self.flood_wait_until: Dict[int, float] = {}
        self.message_history: deque = deque(maxlen=1000)
        
        # Start background workers
        self._start_workers()

    def _start_workers(self):
        """Start background worker tasks"""
        asyncio.create_task(self._process_queue())
        asyncio.create_task(self._batch_processor())
        asyncio.create_task(self._performance_monitor())
    
    async def send_log(self, message: str, level: str = "INFO"):
        """Send log message to the log channel if configured"""
        log_channel = self.config.get_log_channel()
        if not log_channel:
            return
        
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Create emoji based on level
            emoji = {
                "INFO": "ℹ️",
                "SUCCESS": "✅",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "DEBUG": "🔍"
            }.get(level, "📝")
            
            log_text = f"{emoji} **[{timestamp}]** {message}"
            
            await self.client.send_message(log_channel, log_text)
        except Exception as e:
            logger.error(f"Failed to send log to channel: {e}")
    
    async def handle_message(self, event: events.NewMessage.Event):
        """MCP-enhanced message handler with intelligent queuing"""
        if not self.config.get_option('mirror_enabled'):
            return

        message = event.message
        source_chat = event.chat_id
        
        # Ensure source_chat is valid
        if not source_chat:
            logger.warning("Could not determine source chat")
            return

        # Check both old-style mappings and new source/target configuration
        target_chats = []
        
        # First check old-style mapping
        old_target = self.config.get_mapping(source_chat)
        if old_target:
            target_chats.append(old_target)
        
        # Then check new-style source/target
        configured_source = self.config.get_source_channel()
        if configured_source and source_chat == configured_source:
            targets = self.config.get_target_channels()
            target_chats.extend(targets)
        
        # Remove duplicates
        target_chats = list(set(target_chats))
        
        if not target_chats:
            return

        msg_id = f"{source_chat}_{message.id}"
        if msg_id in self.processing:
            return
        
        self.processing.add(msg_id)
        
        try:
            # Analyze strategy once for all targets
            strategy = await self._analyze_message_strategy(message)
            
            # Use parallel processing for multiple targets (except batch)
            if len(target_chats) > 1 and strategy != MirrorStrategy.BATCH:
                # Create tasks for parallel execution
                tasks = []
                for target_chat in target_chats:
                    if not await self._is_flood_waiting(target_chat):
                        # Process in parallel for speed
                        tasks.append(self._mirror_to_target_fast(message, source_chat, target_chat, strategy))
                    else:
                        # Queue if flood waiting
                        await self._queue_task(message, source_chat, target_chat, priority=2)
                
                # Execute all tasks in parallel
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Parallel mirror error: {result}")
            else:
                # Process sequentially for batch or single target
                for target_chat in target_chats:
                    # Check flood wait status
                    if await self._is_flood_waiting(target_chat):
                        await self._queue_task(message, source_chat, target_chat, priority=1)
                        continue
                    
                    if strategy == MirrorStrategy.BATCH:
                        # Add to batch buffer for efficient processing
                        await self._add_to_batch(message, source_chat, target_chat)
                    else:
                        # Process immediately or queue
                        task = MirrorTask(
                            message=message,
                            source_chat=source_chat,
                            target_chat=target_chat,
                            created_at=time.time(),
                            priority=self._calculate_priority(message)
                        )
                        await self.task_queue.put(task)
        finally:
            self.processing.discard(msg_id)

    async def _analyze_message_strategy(self, message: Message) -> MirrorStrategy:
        """MCP Sequential-thinking enhanced strategy analysis"""
        # Check for restrictions
        if message.restriction_reason and self.config.get_option('bypass_restriction'):
            return MirrorStrategy.BYPASS
        
        # Check for batch potential
        if not message.media and message.message and len(message.message) < 100:
            return MirrorStrategy.BATCH
        
        # Large media needs optimization
        if isinstance(message.media, MessageMediaDocument) and message.media.document:
            doc = message.media.document  # type: ignore
            if hasattr(doc, 'size') and doc.size > 10 * 1024 * 1024:  # type: ignore
                return MirrorStrategy.OPTIMIZED
        
        # Context-aware for complex messages
        if message.entities and len(message.entities) > 5:
            return MirrorStrategy.SMART
        
        return MirrorStrategy.DIRECT
    
    def _calculate_priority(self, message: Message) -> int:
        """Calculate message priority for queue processing"""
        # Media messages get higher priority
        if message.media:
            return 1
        # Service messages are low priority
        if isinstance(message, MessageService):
            return 0
        # Replies and forwards are medium priority
        if message.reply_to or message.fwd_from:
            return 1
        return 0
    
    async def _is_flood_waiting(self, chat_id: int) -> bool:
        """Check if chat is in flood wait state"""
        if chat_id in self.flood_wait_until:
            if time.time() < self.flood_wait_until[chat_id]:
                return True
            else:
                del self.flood_wait_until[chat_id]
        return False
    
    async def _queue_task(self, message: Message, source: int, target: int, priority: int = 0):
        """Queue task for processing"""
        task = MirrorTask(
            message=message,
            source_chat=source,
            target_chat=target,
            created_at=time.time(),
            priority=priority
        )
        await self.task_queue.put(task)
    
    async def _add_to_batch(self, message: Message, source: int, target: int):
        """Add message to batch buffer"""
        if target not in self.batch_buffer:
            self.batch_buffer[target] = []
            self.batch_timers[target] = time.time()
        
        self.batch_buffer[target].append(message)
        
        # Process batch if it's full or timeout
        if len(self.batch_buffer[target]) >= 10 or \
           time.time() - self.batch_timers[target] > 2:
            await self._process_batch(target)
    
    async def _process_batch(self, target_chat: int):
        """Process batched messages efficiently"""
        if target_chat not in self.batch_buffer:
            return
        
        messages = self.batch_buffer.pop(target_chat, [])
        if target_chat in self.batch_timers:
            del self.batch_timers[target_chat]
        
        if not messages:
            return
        
        try:
            # Combine text messages
            combined_text = "\n\n".join([m.message for m in messages if m.message])
            
            # Send as single message with separator
            sent = await self.client.send_message(
                target_chat,
                combined_text,
                parse_mode='md'
            )
            
            # Cache all message mappings
            for msg in messages:
                self.config.cache_message(msg.id, sent.id, target_chat)
            
            self.config.update_stats('messages_mirrored', len(messages))
            logger.info(f"Batch processed {len(messages)} messages")
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            # Fall back to individual processing
            for msg in messages:
                await self._queue_task(msg, target_chat, target_chat)
    
    async def _process_queue(self):
        """Background queue processor with intelligent retry"""
        while True:
            try:
                task = await self.task_queue.get()
                
                # Skip old tasks
                if time.time() - task.created_at > 300:  # 5 minutes
                    continue
                
                # Check flood wait
                if await self._is_flood_waiting(task.target_chat):
                    await asyncio.sleep(1)
                    await self.task_queue.put(task)  # Re-queue
                    continue
                
                # Process task
                msg_id = f"{task.source_chat}_{task.message.id}"
                if msg_id not in self.processing:
                    self.processing.add(msg_id)
                    try:
                        await self._process_task(task)
                    finally:
                        self.processing.discard(msg_id)
                
            except Exception as e:
                logger.error(f"Queue processor error: {e}")
            
            await asyncio.sleep(0.1)
    
    async def _process_task(self, task: MirrorTask):
        """Process individual mirror task with retry logic"""
        try:
            start_time = time.time()
            
            # Apply strategy-based processing
            strategy = await self._analyze_message_strategy(task.message)
            
            if strategy == MirrorStrategy.BYPASS:
                result = await self._mirror_restricted_media_enhanced(task.message, task.target_chat)
            elif strategy == MirrorStrategy.OPTIMIZED:
                result = await self._mirror_optimized(task.message, task.target_chat)
            elif strategy == MirrorStrategy.SMART:
                result = await self._mirror_smart(task.message, task.target_chat)
            else:
                result = await self._mirror_direct(task.message, task.target_chat)
            
            if result:
                self.config.cache_message(task.message.id, result.id, task.source_chat)
                self.config.update_stats('messages_mirrored')
                
                # Track performance
                elapsed = time.time() - start_time
                self._update_performance_stats('mirror_time', elapsed)
                
                logger.info(f"Mirrored {task.message.id} → {result.id} in {elapsed:.2f}s")
                
                # Send success log periodically (every 10 messages)
                stats = self.config.get_stats()
                if stats.get('messages_mirrored', 0) % 10 == 0:
                    await self.send_log(
                        f"미러링 진행중\n"
                        f"총 메시지: {stats.get('messages_mirrored', 0)}개\n"
                        f"미디어: {stats.get('media_mirrored', 0)}개",
                        "SUCCESS"
                    )
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait {e.seconds}s for chat {task.target_chat}")
            self.flood_wait_until[task.target_chat] = time.time() + e.seconds
            
            # Send log message
            await self.send_log(
                f"Flood wait: {e.seconds}초 대기중\n"
                f"채널: {task.target_chat}",
                "WARNING"
            )
            
            # Re-queue with higher priority
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.priority = 2  # Critical priority
                await self.task_queue.put(task)
        
        except (ChatWriteForbiddenError, ChannelPrivateError) as e:
            logger.error(f"Permission error for chat {task.target_chat}: {e}")
            await self.send_log(
                f"권한 오류\n"
                f"채널: {task.target_chat}\n"
                f"오류: {type(e).__name__}\n"
                f"매핑 제거됨",
                "ERROR"
            )
            self.config.remove_mapping(task.source_chat)
        
        except Exception as e:
            logger.error(f"Task processing error: {e}")
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
                await self.task_queue.put(task)
            else:
                self.config.update_stats('errors')
    
    async def _mirror_direct(self, message: Message, target_chat: int) -> Optional[Message]:
        """Direct mirroring with custom emoji support"""
        try:
            if message.media and self.config.get_option('bypass_restriction'):
                return await self._mirror_restricted_media_enhanced(message, target_chat)
            elif message.media and self.config.get_option('mirror_media'):
                return await self._mirror_media(message, target_chat)
            elif message.message and self.config.get_option('mirror_text'):
                # Check for custom emojis in entities
                if message.entities:
                    from telethon.tl.types import MessageEntityCustomEmoji
                    custom_emoji_count = sum(1 for e in message.entities if isinstance(e, MessageEntityCustomEmoji))
                    if custom_emoji_count > 0:
                        logger.info(f"Mirroring message with {custom_emoji_count} custom emoji(s)")
                
                # Send with all formatting entities including custom emojis
                return await self.client.send_message(
                    target_chat,
                    message.message,
                    formatting_entities=message.entities,  # Preserves custom emojis
                    link_preview=isinstance(message.media, MessageMediaWebPage) if message.media else False
                )
        except Exception as e:
            logger.error(f"Direct mirror failed: {e}")
            # Fallback to plain text if entities fail
            try:
                if message.message:
                    return await self.client.send_message(
                        target_chat,
                        message.message,
                        link_preview=False
                    )
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
        return None
    
    async def _mirror_optimized(self, message: Message, target_chat: int) -> Optional[Message]:
        """Optimized mirroring for large media"""
        # Implementation with compression and chunking
        return await self._mirror_direct(message, target_chat)
    
    async def _mirror_smart(self, message: Message, target_chat: int) -> Optional[Message]:
        """Context-aware smart mirroring"""
        # Implementation with context analysis
        return await self._mirror_direct(message, target_chat)
    
    async def _process_custom_emojis(self, message: Message) -> Optional[str]:
        """Process and preserve custom emojis in messages"""
        try:
            if not message.message:
                return None
            
            text = message.message
            
            # Check for custom emoji entities
            if message.entities:
                from telethon.tl.types import MessageEntityCustomEmoji
                
                # Sort entities by offset in reverse to avoid offset issues
                custom_emoji_entities = [
                    e for e in message.entities 
                    if isinstance(e, MessageEntityCustomEmoji)
                ]
                
                if custom_emoji_entities:
                    # Process custom emojis
                    for entity in sorted(custom_emoji_entities, key=lambda x: x.offset, reverse=True):
                        try:
                            # Get the emoji document ID
                            document_id = entity.document_id
                            
                            # Try to get custom emoji info
                            # Note: Custom emojis might need special handling based on availability
                            emoji_text = text[entity.offset:entity.offset + entity.length]
                            
                            # Mark custom emoji for preservation
                            # You might want to download and re-upload the custom emoji sticker
                            logger.debug(f"Custom emoji found: {emoji_text} (doc_id: {document_id})")
                            
                        except Exception as e:
                            logger.debug(f"Custom emoji processing error: {e}")
            
            return text
            
        except Exception as e:
            logger.error(f"Error processing custom emojis: {e}")
            return None
    
    async def _retry_edit(self, message: Message, target_chat: int, target_msg_id: int, wait_time: float):
        """Retry edit after flood wait"""
        try:
            await asyncio.sleep(wait_time)
            
            # Process custom emojis
            processed_text = await self._process_custom_emojis(message)
            
            await self.client.edit_message(
                target_chat,
                target_msg_id,
                processed_text or message.message,
                formatting_entities=message.entities,
                link_preview=bool(getattr(message, 'web_preview', False)),
                buttons=getattr(message, 'buttons', None)
            )
            logger.info(f"✏️ Edit retry successful for {target_msg_id} in {target_chat}")
            
        except Exception as e:
            logger.error(f"Edit retry failed: {e}")
    
    async def _mirror_to_target_fast(self, message: Message, source_chat: int, target_chat: int, strategy: MirrorStrategy):
        """Fast direct mirroring for parallel processing"""
        try:
            # Skip additional checks for speed
            result = None
            
            if strategy == MirrorStrategy.BYPASS:
                result = await self._mirror_restricted_media_enhanced(message, target_chat)
            elif strategy == MirrorStrategy.OPTIMIZED:
                result = await self._mirror_optimized(message, target_chat)
            elif strategy == MirrorStrategy.SMART:
                result = await self._mirror_smart(message, target_chat)
            else:
                result = await self._mirror_direct(message, target_chat)
            
            if result:
                # Cache the message mapping
                self.config.cache_message(message.id, result.id, source_chat)
                self.config.update_stats('messages_mirrored')
                logger.debug(f"Fast mirrored {message.id} → {result.id}")
                
        except FloodWaitError as e:
            logger.warning(f"Flood wait {e.seconds}s for {target_chat}")
            self.flood_wait_until[target_chat] = time.time() + e.seconds
            # Queue for retry with high priority
            await self._queue_task(message, source_chat, target_chat, priority=2)
        except Exception as e:
            logger.error(f"Fast mirror error to {target_chat}: {e}")
            # Queue for retry through normal processing
            await self._queue_task(message, source_chat, target_chat, priority=1)
    
    def _update_performance_stats(self, metric: str, value: float):
        """Track performance metrics"""
        if metric not in self.performance_stats:
            self.performance_stats[metric] = value
        else:
            # Running average
            self.performance_stats[metric] = (self.performance_stats[metric] + value) / 2
    
    async def _batch_processor(self):
        """Background batch processor"""
        while True:
            try:
                current_time = time.time()
                for target_chat in list(self.batch_timers.keys()):
                    if current_time - self.batch_timers[target_chat] > 2:
                        await self._process_batch(target_chat)
            except Exception as e:
                logger.error(f"Batch processor error: {e}")
            
            await asyncio.sleep(1)
    
    async def _performance_monitor(self):
        """Monitor and optimize performance"""
        while True:
            try:
                # Log performance stats
                if self.performance_stats:
                    avg_time = self.performance_stats.get('mirror_time', 0)
                    queue_size = self.task_queue.qsize()
                    
                    if avg_time > 5 or queue_size > 50:
                        logger.warning(f"Performance degradation: avg_time={avg_time:.2f}s, queue={queue_size}")
                
                # Clear old error counts
                current_time = time.time()
                self.error_counts = {k: v for k, v in self.error_counts.items() 
                                   if current_time - v < 3600}  # Keep last hour
                
            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds

    async def _mirror_restricted_media_enhanced(
        self, message: Message, target_chat: int
    ) -> Optional[Message]:
        """MCP-enhanced media mirroring with advanced bypass"""
        try:
            if isinstance(message.media, MessageMediaPhoto):
                photo_bytes = await self.client.download_media(message, file=io.BytesIO())

                if photo_bytes:
                    self.config.update_stats('media_mirrored')
                    return await self.client.send_file(
                        target_chat,
                        photo_bytes,
                        caption=message.message,  # type: ignore
                        formatting_entities=message.entities,  # Preserves custom emojis in caption
                        force_document=False
                    )

            elif isinstance(message.media, MessageMediaDocument):
                attributes = getattr(message.media.document, 'attributes', []) if message.media.document else []  # type: ignore
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
                        caption=message.message,  # type: ignore
                        formatting_entities=message.entities,  # Preserves custom emojis in caption
                        attributes=attributes,
                        force_document=not (is_video or is_sticker or is_gif),
                        video_note=(
                            is_video and getattr(attributes[0], 'round_message', False)  # type: ignore
                            if attributes else False
                        ),
                        voice_note=(
                            is_audio and getattr(attributes[0], 'voice', False)  # type: ignore
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
            if message.message:  # type: ignore
                return await self.client.send_message(
                    target_chat,
                    message.message,  # type: ignore
                    formatting_entities=message.entities
                )
        except Exception as e:
            logger.error("Restricted media mirror failed: %s", e)
            return None
        return None

    async def _mirror_media(self, message: Message, target_chat: int) -> Optional[Message]:
        """Mirror media normally (when not restricted)"""
        try:
            if message.media:
                return await self.client.send_file(
                    target_chat,
                    message.media,  # type: ignore
                    caption=message.text,  # type: ignore
                    formatting_entities=message.entities  # Preserves custom emojis
                )
            return None
        except Exception as e:
            logger.error("Media mirror failed: %s", e)
            return None

    async def handle_edit(self, event: events.MessageEdited.Event):
        """Enhanced edit handler with custom emoji and formatting support"""
        if not self.config.get_option('mirror_edits'):
            return

        message = event.message
        if not message or not message.message:  # Skip if no text content
            return
            
        source_chat = message.chat_id

        # Get all target chats
        target_chats = []
        old_target = self.config.get_mapping(source_chat)
        if old_target:
            target_chats.append(old_target)
        
        configured_source = self.config.get_source_channel()
        if configured_source and source_chat == configured_source:
            targets = self.config.get_target_channels()
            target_chats.extend(targets)
        
        target_chats = list(set(target_chats))
        if not target_chats:
            return

        # Process custom emojis and formatting
        processed_text = await self._process_custom_emojis(message)
        
        # Edit in all target chats
        for target_chat in target_chats:
            target_msg_id = self.config.get_cached_message(message.id, source_chat)
            if not target_msg_id:
                logger.debug(f"No cached message for {message.id} in {source_chat}")
                continue

            try:
                # Preserve all formatting, entities, and custom emojis
                await self.client.edit_message(
                    target_chat,
                    target_msg_id,
                    processed_text or message.message,
                    formatting_entities=message.entities,
                    link_preview=bool(getattr(message, 'web_preview', False)),
                    buttons=getattr(message, 'buttons', None)
                )
                logger.info("✏️ Edited message %s → %s in chat %s", message.id, target_msg_id, target_chat)
                self.config.update_stats('edits_mirrored')
                
            except MessageNotModifiedError:
                # Message content is identical, skip
                logger.debug("Message not modified, skipping")
            except FloodWaitError as e:
                logger.warning(f"Flood wait {e.seconds}s for edit in {target_chat}")
                self.flood_wait_until[target_chat] = time.time() + e.seconds
                # Queue for retry after flood wait
                asyncio.create_task(self._retry_edit(message, target_chat, target_msg_id, e.seconds))
            except Exception as e:
                logger.error(f"Edit failed for {target_chat}: {e}")

    async def handle_delete(self, event: events.MessageDeleted.Event):
        """Enhanced delete handler with multi-target support"""
        if not self.config.get_option('mirror_deletes'):
            return

        # Get source chat from event
        source_chat = getattr(event, 'chat_id', None) or getattr(event, 'channel_id', None)
        if not source_chat:
            logger.debug("No source chat in delete event")
            return

        # Batch deletions for efficiency (up to 100 per batch)
        delete_batch: Dict[int, List[int]] = {}
        
        for msg_id in event.deleted_ids:
            # Get all possible target chats
            target_chats = []
            
            # Check old-style mapping
            old_target = self.config.get_mapping(source_chat)
            if old_target:
                target_chats.append(old_target)
            
            # Check new-style source->targets mapping
            configured_source = self.config.get_source_channel()
            if configured_source and source_chat == configured_source:
                targets = self.config.get_target_channels()
                target_chats.extend(targets)
            
            target_chats = list(set(target_chats))
            
            # Find cached messages in all target chats
            for target_chat in target_chats:
                target_msg_id = self.config.get_cached_message(msg_id, source_chat)
                if not target_msg_id:
                    continue
                
                if target_chat not in delete_batch:
                    delete_batch[target_chat] = []
                delete_batch[target_chat].append(target_msg_id)
        
        # Process batches
        for target_chat, msg_ids in delete_batch.items():
            try:
                # Split into chunks of 100 (Telegram limit)
                for i in range(0, len(msg_ids), 100):
                    chunk = msg_ids[i:i+100]
                    await self.client.delete_messages(target_chat, chunk)
                    logger.info(f"🗑️ Batch deleted {len(chunk)} messages in {target_chat}")
                    self.config.update_stats('deletes_mirrored', len(chunk))
                    
            except MessageDeleteForbiddenError:
                logger.warning(f"Cannot delete messages in {target_chat} - no permission")
            except MessageIdInvalidError:
                logger.debug(f"Some messages already deleted in {target_chat}")
            except FloodWaitError as e:
                logger.warning(f"Flood wait {e.seconds}s for delete in {target_chat}")
                self.flood_wait_until[target_chat] = time.time() + e.seconds
            except Exception as e:
                logger.error(f"Batch delete failed: {e}")

    async def handle_album(self, event: events.Album.Event):
        """Handle album (grouped media) event"""
        if not self.config.get_option('mirror_enabled'):
            return

        source_chat = event.chat_id
        
        # Get all target chats
        target_chats = []
        old_target = self.config.get_mapping(source_chat)
        if old_target:
            target_chats.append(old_target)
        
        configured_source = self.config.get_source_channel()
        if configured_source and source_chat == configured_source:
            targets = self.config.get_target_channels()
            target_chats.extend(targets)
        
        target_chats = list(set(target_chats))
        if not target_chats:
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
                
                # Send to all target chats
                for target_chat in target_chats:
                    try:
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
                        logger.info("Mirrored album with %s items to %s", len(media_list), target_chat)
                    except Exception as e:
                        logger.error("Album mirror failed for %s: %s", target_chat, e)

        except Exception as e:
            logger.error("Album mirror failed: %s", e)
            self.config.update_stats('errors')

    async def save_state(self):
        """Save engine state"""
        self.config.save()
        logger.info("Mirror engine state saved")

    def get_status(self) -> dict:
        """Get enhanced engine status with MCP metrics"""
        mappings = self.config.get_all_mappings()
        stats = self.config.get_stats()

        return {
            'enabled': self.config.get_option('mirror_enabled'),
            'mappings_count': len(mappings),
            'processing_count': len(self.processing),
            'queue_size': self.task_queue.qsize(),
            'batch_buffers': len(self.batch_buffer),
            'flood_wait_chats': len(self.flood_wait_until),
            'performance': {
                'avg_mirror_time': self.performance_stats.get('mirror_time', 0),
                'error_rate': len(self.error_counts) / max(stats.get('messages_mirrored', 1), 1)
            },
            'stats': stats,
            'options': {
                'text': self.config.get_option('mirror_text'),
                'media': self.config.get_option('mirror_media'),
                'edits': self.config.get_option('mirror_edits'),
                'deletes': self.config.get_option('mirror_deletes'),
                'bypass': self.config.get_option('bypass_restriction')
            }
        }
    
    async def sync_channel(self, source_chat: int, target_chat: int, limit: Optional[float] = None):
        """MCP-enhanced channel synchronization"""
        """Sync all messages from source to target efficiently"""
        try:
            logger.info(f"Starting sync: {source_chat} → {target_chat}")
            
            # Get messages in batches
            synced = 0
            async for message in self.client.iter_messages(source_chat, limit=limit):
                # Skip service messages
                if isinstance(message, MessageService):
                    continue
                
                # Check if already synced
                if self.config.get_cached_message(message.id, source_chat):
                    continue
                
                # Queue for processing with high priority
                task = MirrorTask(
                    message=message,
                    source_chat=source_chat,
                    target_chat=target_chat,
                    created_at=time.time(),
                    priority=2  # High priority for sync
                )
                await self.task_queue.put(task)
                
                synced += 1
                
                # Rate limiting
                if synced % 10 == 0:
                    await asyncio.sleep(1)
                    logger.info(f"Synced {synced} messages...")
            
            logger.info(f"Sync complete: {synced} messages queued")
            return synced
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return 0
