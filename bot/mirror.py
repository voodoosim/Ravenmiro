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
        """Ultra-fast message handler with instant mirroring"""
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

        # Debug logging for media
        if message.media:
            logger.info(f"📸 Media detected: {type(message.media).__name__}")
            if not self.config.get_option('mirror_media'):
                logger.warning("Media mirroring is disabled")
                return

        msg_id = f"{source_chat}_{message.id}"
        if msg_id in self.processing:
            return
        
        self.processing.add(msg_id)
        
        try:
            # INSTANT MIRRORING - No queue, direct processing for speed
            strategy = await self._analyze_message_strategy(message)
            
            # Always use parallel processing for maximum speed
            tasks = []
            for target_chat in target_chats:
                # Skip flood check for speed - handle errors instead
                tasks.append(self._mirror_instant(message, source_chat, target_chat, strategy))
            
            # Execute all tasks in parallel
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, FloodWaitError):
                        # Handle flood wait by queuing
                        logger.warning(f"Flood wait for {target_chats[i]}: {result.seconds}s")
                        self.flood_wait_until[target_chats[i]] = time.time() + result.seconds
                        await self._queue_task(message, source_chat, target_chats[i], priority=2)
                    elif isinstance(result, Exception):
                        logger.error(f"Mirror error: {result}")
                        # Retry with queue
                        await self._queue_task(message, source_chat, target_chats[i], priority=1)
        finally:
            self.processing.discard(msg_id)

    async def _analyze_message_strategy(self, message: Message) -> MirrorStrategy:
        """Ultra-fast strategy analysis - prioritize speed"""
        # Check for restrictions first
        if message.restriction_reason and self.config.get_option('bypass_restriction'):
            return MirrorStrategy.BYPASS
        
        # Skip batch for instant processing
        # All messages go direct for maximum speed
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
        """Ultra-fast queue processor - minimal delays"""
        while True:
            try:
                task = await self.task_queue.get()
                
                # Skip old tasks
                if time.time() - task.created_at > 60:  # 1 minute timeout
                    continue
                
                # Quick flood check
                if await self._is_flood_waiting(task.target_chat):
                    await asyncio.sleep(0.5)  # Shorter wait
                    await self.task_queue.put(task)  # Re-queue
                    continue
                
                # Process task immediately
                msg_id = f"{task.source_chat}_{task.message.id}"
                if msg_id not in self.processing:
                    self.processing.add(msg_id)
                    try:
                        # Use instant processing
                        await self._process_task_instant(task)
                    finally:
                        self.processing.discard(msg_id)
                
            except Exception as e:
                logger.error(f"Queue processor error: {e}")
            
            # Minimal sleep for fastest processing
            await asyncio.sleep(0.01)
    
    async def _process_task_instant(self, task: MirrorTask):
        """Instant task processing - no delays"""
        try:
            # Direct instant mirroring
            strategy = MirrorStrategy.DIRECT if not task.message.restriction_reason else MirrorStrategy.BYPASS
            result = await self._mirror_instant(task.message, task.source_chat, task.target_chat, strategy)
            
            if result:
                self.config.update_stats('messages_mirrored')
                logger.debug(f"Queue instant: {task.message.id} → {result.id}")
                
        except FloodWaitError as e:
            logger.warning(f"Flood wait {e.seconds}s for {task.target_chat}")
            self.flood_wait_until[task.target_chat] = time.time() + e.seconds
            
            # Re-queue with retry
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.priority = 2
                await self.task_queue.put(task)
        
        except Exception as e:
            logger.error(f"Task instant error: {e}")
            # Retry
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                await asyncio.sleep(0.5 * task.retry_count)  # Short backoff
                await self.task_queue.put(task)
            else:
                self.config.update_stats('errors')
    
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
    
    async def _handle_media_edit(self, message: Message, target_chat: int, target_msg_id: int):
        """Handle media edits - photo changes, caption updates"""
        try:
            # Get the target message to check current state
            target_msg = await self.client.get_messages(target_chat, ids=target_msg_id)
            if not target_msg:
                logger.error(f"Target message {target_msg_id} not found")
                return
            
            # Compare media to detect changes
            media_changed = False
            
            # Check if it's a photo change
            if isinstance(message.media, MessageMediaPhoto) and isinstance(target_msg.media, MessageMediaPhoto):
                # Compare photo IDs
                source_photo_id = message.media.photo.id if message.media.photo else None
                target_photo_id = target_msg.media.photo.id if target_msg.media.photo else None
                media_changed = (source_photo_id != target_photo_id)
            elif isinstance(message.media, MessageMediaDocument) and isinstance(target_msg.media, MessageMediaDocument):
                # Compare document IDs
                source_doc_id = message.media.document.id if message.media.document else None
                target_doc_id = target_msg.media.document.id if target_msg.media.document else None
                media_changed = (source_doc_id != target_doc_id)
            else:
                # Different media types
                media_changed = True
            
            if media_changed:
                logger.info(f"Media content changed, re-sending")
                # Delete and re-send for media changes
                await self.client.delete_messages(target_chat, [target_msg_id])
                new_msg = await self._mirror_instant(message, message.chat_id, target_chat, MirrorStrategy.DIRECT)
                if new_msg:
                    self.config.cache_message(message.id, new_msg.id, message.chat_id)
            else:
                # Only caption changed - just edit the caption
                logger.debug(f"Caption-only edit for {target_msg_id}")
                await self.client.edit_message(
                    target_chat,
                    target_msg_id,
                    message.message or "",  # New caption
                    formatting_entities=message.entities,  # Preserve all emojis
                    file=None  # Don't re-upload media
                )
                
        except Exception as e:
            logger.error(f"Media edit failed: {e}")
            # Fallback - delete and re-send
            try:
                await self.client.delete_messages(target_chat, [target_msg_id])
                new_msg = await self._mirror_instant(message, message.chat_id, target_chat, MirrorStrategy.DIRECT)
                if new_msg:
                    self.config.cache_message(message.id, new_msg.id, message.chat_id)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
    
    async def _handle_text_edit(self, message: Message, target_chat: int, target_msg_id: int):
        """Handle text-only edits"""
        try:
            # Edit with all formatting preserved
            await self.client.edit_message(
                target_chat,
                target_msg_id,
                message.message or "",
                formatting_entities=message.entities,  # Preserve all emojis
                link_preview=bool(getattr(message, 'web_preview', False)),
                buttons=getattr(message, 'buttons', None)
            )
        except Exception as e:
            logger.error(f"Text edit failed: {e}")
    
    async def _retry_edit(self, message: Message, target_chat: int, target_msg_id: int, wait_time: float):
        """Retry edit after flood wait"""
        try:
            await asyncio.sleep(wait_time)
            
            # Retry based on message type
            if message.media:
                await self._handle_media_edit(message, target_chat, target_msg_id)
            else:
                await self._handle_text_edit(message, target_chat, target_msg_id)
            
            logger.info(f"✏️ Edit retry successful for {target_msg_id} in {target_chat}")
            
        except Exception as e:
            logger.error(f"Edit retry failed: {e}")
    
    async def _mirror_instant(self, message: Message, source_chat: int, target_chat: int, strategy: MirrorStrategy):
        """Instant mirroring with full emoji support - no delays"""
        try:
            result = None
            
            # Check for bypass restriction first
            if message.restriction_reason and self.config.get_option('bypass_restriction'):
                result = await self._mirror_restricted_media_enhanced(message, target_chat)
            elif message.media:
                # Handle all media types
                result = await self._mirror_media_instant(message, target_chat)
            elif message.message:
                # Text only
                result = await self._mirror_text_instant(message, target_chat)
            else:
                logger.warning("Message has no content to mirror")
                return None
            
            if result:
                # Cache the message mapping
                self.config.cache_message(message.id, result.id, source_chat)
                self.config.update_stats('messages_mirrored')
                
                # Update media stats if applicable
                if message.media:
                    self.config.update_stats('media_mirrored')
                
                # Log emoji detection
                if message.entities:
                    from telethon.tl.types import MessageEntityCustomEmoji
                    custom_count = sum(1 for e in message.entities if isinstance(e, MessageEntityCustomEmoji))
                    if custom_count > 0:
                        logger.debug(f"Instant mirrored with {custom_count} custom emoji(s)")
                
                return result
                
        except FloodWaitError as e:
            # Re-raise for parent handler
            raise e
        except Exception as e:
            logger.error(f"Instant mirror error: {e}")
            raise e
    
    async def _mirror_text_instant(self, message: Message, target_chat: int) -> Optional[Message]:
        """Instant text mirroring with all emoji types"""
        try:
            # Send with complete entity preservation
            return await self.client.send_message(
                target_chat,
                message.message,
                formatting_entities=message.entities,  # Preserves ALL emojis
                link_preview=isinstance(message.media, MessageMediaWebPage) if message.media else False,
                reply_to=None,  # Don't preserve replies for speed
                silent=True  # Silent send for speed
            )
        except Exception as e:
            logger.error(f"Text instant mirror failed: {e}")
            # Fallback without entities
            return await self.client.send_message(
                target_chat,
                message.message,
                link_preview=False,
                silent=True
            )
    
    async def _mirror_media_instant(self, message: Message, target_chat: int) -> Optional[Message]:
        """Instant media mirroring with emoji preservation"""
        try:
            # Check if bypass restriction is needed
            if message.restriction_reason and self.config.get_option('bypass_restriction'):
                return await self._mirror_restricted_media_enhanced(message, target_chat)
            
            # Handle different media types
            if isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
                # Direct send for photos and documents
                return await self.client.send_file(
                    target_chat,
                    message.media,
                    caption=message.message or "",
                    formatting_entities=message.entities,  # Preserves emojis in caption
                    silent=True
                )
            elif isinstance(message.media, MessageMediaWebPage):
                # Web preview - send as text with link preview
                return await self.client.send_message(
                    target_chat,
                    message.message or "",
                    formatting_entities=message.entities,
                    link_preview=True,
                    silent=True
                )
            else:
                # Other media types - use generic send
                return await self.client.send_file(
                    target_chat,
                    message.media,
                    caption=message.message or "",
                    formatting_entities=message.entities,
                    silent=True
                )
        except Exception as e:
            logger.error(f"Media instant mirror failed: {e}")
            # Try bypass method as fallback
            try:
                return await self._mirror_restricted_media_enhanced(message, target_chat)
            except Exception as bypass_error:
                logger.error(f"Bypass fallback also failed: {bypass_error}")
                return None
    
    async def _mirror_to_target_fast(self, message: Message, source_chat: int, target_chat: int, strategy: MirrorStrategy):
        """Legacy fast mirroring function - redirects to instant"""
        return await self._mirror_instant(message, source_chat, target_chat, strategy)
    
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
        """Ultra-fast media bypass with full emoji support"""
        try:
            if isinstance(message.media, MessageMediaPhoto):
                # Download to memory for speed
                photo_bytes = await self.client.download_media(message, file=io.BytesIO())

                if photo_bytes:
                    self.config.update_stats('media_mirrored')
                    return await self.client.send_file(
                        target_chat,
                        photo_bytes,
                        caption=message.message,  # type: ignore
                        formatting_entities=message.entities,  # ALL emojis preserved
                        force_document=False,
                        silent=True  # Silent for speed
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
                        formatting_entities=message.entities,  # ALL emojis preserved
                        attributes=attributes,
                        force_document=not (is_video or is_sticker or is_gif),
                        video_note=(
                            is_video and getattr(attributes[0], 'round_message', False)  # type: ignore
                            if attributes else False
                        ),
                        voice_note=(
                            is_audio and getattr(attributes[0], 'voice', False)  # type: ignore
                            if attributes else False
                        ),
                        silent=True  # Silent for speed
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
        """Complete edit handler - text, media, and caption changes"""
        if not self.config.get_option('mirror_edits'):
            return

        message = event.message
        if not message:
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

        # Handle different edit types
        for target_chat in target_chats:
            target_msg_id = self.config.get_cached_message(message.id, source_chat)
            if not target_msg_id:
                logger.debug(f"No cached message for {message.id} in {source_chat}")
                continue

            try:
                # Get target message to check what type it was
                target_msg = await self.client.get_messages(target_chat, ids=target_msg_id)
                
                # Handle type changes (text<->media)
                if message.media and not target_msg.media:
                    # Text changed to media - delete and re-send
                    logger.info("Text → Media change detected")
                    await self.client.delete_messages(target_chat, [target_msg_id])
                    new_msg = await self._mirror_instant(message, source_chat, target_chat, MirrorStrategy.DIRECT)
                    if new_msg:
                        self.config.cache_message(message.id, new_msg.id, source_chat)
                elif not message.media and target_msg.media:
                    # Media changed to text - delete and re-send
                    logger.info("Media → Text change detected")
                    await self.client.delete_messages(target_chat, [target_msg_id])
                    new_msg = await self._mirror_instant(message, source_chat, target_chat, MirrorStrategy.DIRECT)
                    if new_msg:
                        self.config.cache_message(message.id, new_msg.id, source_chat)
                elif message.media:
                    # Media edit (caption or media change)
                    await self._handle_media_edit(message, target_chat, target_msg_id)
                else:
                    # Text-only edit
                    await self._handle_text_edit(message, target_chat, target_msg_id)
                
                logger.info(f"✏️ Edited {message.id} → {target_msg_id} in {target_chat}")
                self.config.update_stats('edits_mirrored')
                
            except MessageNotModifiedError:
                logger.debug("Message not modified, skipping")
            except FloodWaitError as e:
                logger.warning(f"Flood wait {e.seconds}s for edit in {target_chat}")
                self.flood_wait_until[target_chat] = time.time() + e.seconds
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
        """Ultra-fast album handling with parallel processing"""
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
            # Parallel download for speed
            media_tasks = []
            
            for message in event.messages:
                if self.config.get_option('bypass_restriction'):
                    if isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
                        media_tasks.append(self.client.download_media(message, file=io.BytesIO()))
                else:
                    media_tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Placeholder
            
            # Download all media in parallel
            if self.config.get_option('bypass_restriction'):
                media_results = await asyncio.gather(*media_tasks, return_exceptions=True)
                media_list = [m for m in media_results if m and not isinstance(m, Exception)]
            else:
                media_list = [msg.media for msg in event.messages]

            if media_list:
                # Get caption with emoji support
                caption = ""
                entities = None
                if hasattr(event.original_update, 'message'):
                    caption = event.original_update.message.message or ""  # type: ignore
                    entities = event.original_update.message.entities  # type: ignore
                
                # Send to all targets in parallel
                send_tasks = []
                for target_chat in target_chats:
                    send_tasks.append(self.client.send_file(
                        target_chat,
                        media_list,
                        caption=caption,
                        formatting_entities=entities,  # Preserve emojis
                        silent=True  # Silent for speed
                    ))
                
                # Execute all sends in parallel
                results = await asyncio.gather(*send_tasks, return_exceptions=True)
                
                for i, result in enumerate(results):
                    if not isinstance(result, Exception):
                        if isinstance(result, list):
                            for j, msg in enumerate(event.messages):
                                if j < len(result):
                                    self.config.cache_message(msg.id, result[j].id, source_chat)
                        self.config.update_stats('media_mirrored', len(media_list))
                        logger.info(f"Album instant: {len(media_list)} items → {target_chats[i]}")
                    else:
                        logger.error(f"Album error for {target_chats[i]}: {result}")

        except Exception as e:
            logger.error(f"Album mirror failed: {e}")
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
