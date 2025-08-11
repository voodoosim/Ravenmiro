# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference
한국어로 대답해주세요. (Please respond in Korean)

## Project Overview

This is a Telegram Mirror Bot that provides complete channel mirroring functionality with copy restriction bypass capabilities. The bot uses Telethon library for Telegram API interaction and features an MCP-enhanced mirroring engine for optimal performance.

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies
pip install -r requirements.txt

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Set up environment variables
cp .env.example .env
# Edit .env with your API_ID and API_HASH from https://my.telegram.org
```

### Running the Bot
```bash
# Main execution
python bot/main.py

# Alternative: Run from project root
python -m bot.main
```

### Testing
```bash
# Run test imports
python test_imports.py

# Test bot functionality
python test_bot.py
```

### Code Quality Checks
```bash
# Run pylint (configured in pyproject.toml)
python -m pylint bot/

# Run mypy type checking
python -m mypy bot/

# Run ruff linter
python -m ruff check bot/
```

### Deployment
```bash
# VPS deployment script (Linux)
chmod +x deploy.sh
./deploy.sh

# Start with screen session
./start_screen.sh

# Systemd service management
sudo systemctl start crowbot
sudo systemctl status crowbot
sudo systemctl enable crowbot  # Auto-start on boot
```

## Code Architecture

### Core Components

1. **bot/main.py** - Entry point and main bot orchestration
   - `MirrorBot` class: Manages bot lifecycle, initialization, and event handling
   - Handles connection management, session validation, and graceful shutdown
   - Registers all event handlers for messages, edits, deletes, and albums

2. **bot/config.py** - Configuration management system  
   - `Config` class: Manages settings persistence with JSON storage
   - Handles channel mappings, message caching, statistics, and bot options
   - Environment variable integration for API credentials

3. **bot/mirror.py** - MCP-enhanced mirroring engine
   - `MirrorEngine` class: Advanced mirroring with intelligent strategies
   - Features: Task queuing, batch processing, flood wait handling, performance monitoring
   - Strategies: DIRECT, BYPASS (restriction bypass), OPTIMIZED, BATCH, SMART
   - Background workers for queue processing, batch handling, and performance monitoring

4. **bot/simple_menu.py** - Interactive menu system
   - `SimpleMenuHandler` class: User interaction through numbered menu system
   - Korean/English bilingual interface
   - State management for multi-step operations
   - Handles channel configuration, sync operations, and status monitoring

5. **bot/session_handler.py** - Session string management
   - Manages Telegram session authentication
   - Secure session storage and validation

### Key Design Patterns

1. **Task Queue System**: Asynchronous task processing with priority queuing
   - Priority levels: 0 (normal), 1 (high), 2 (critical)
   - Exponential backoff for retries
   - Flood wait handling with automatic retry

2. **Batch Processing**: Efficient message batching for bulk operations
   - Automatic batching for small text messages
   - Configurable batch size and timeout
   - Fallback to individual processing on failure

3. **Strategy Pattern**: Dynamic mirroring strategies based on content type
   - Auto-detection of optimal strategy per message
   - Context-aware processing for different media types

4. **State Management**: Menu navigation with state tracking
   - Per-user state tracking for concurrent operations
   - Input validation and context preservation

## Important Implementation Details

### Channel ID Conversion
Telegram channel IDs require special handling:
- Broadcast channels and megagroups: `-1000000000000 - channel_id`
- Regular groups: Negative of the ID
- Users: Positive ID

### Flood Wait Management
- Automatic flood wait detection and retry
- Per-chat flood wait tracking
- Queue re-prioritization during flood waits

### Message Caching
- Maps source message IDs to target message IDs for edits/deletes
- Auto-cleanup when cache exceeds 10,000 entries
- Persistent storage in settings.json

### Restriction Bypass
- Downloads media to memory using BytesIO
- Re-uploads to target channel with original attributes
- Preserves media types (video, audio, stickers, GIFs)

## Bot Commands

### User Commands
- `.설정` - Open configuration menu
- `.동기화` - Synchronize channel history

### Menu Navigation
- Number selection (1-9) for menu options
- `0` or `뒤로` to go back
- `cancel` to cancel current operation

## Configuration Structure

### settings.json Schema
```json
{
  "api_id": 12345678,
  "api_hash": "hash_here",
  "session_string": "session_here",
  "channel_mappings": {
    "source_id": "target_id"
  },
  "message_cache": {
    "chatid_msgid": "target_msg_id"
  },
  "stats": {
    "messages_mirrored": 0,
    "media_mirrored": 0,
    "errors": 0
  },
  "options": {
    "mirror_enabled": true,
    "mirror_text": true,
    "mirror_media": true,
    "mirror_edits": true,
    "mirror_deletes": true,
    "bypass_restriction": true
  }
}
```

## Error Handling

- FloodWaitError: Automatic retry with exponential backoff
- ChatWriteForbiddenError: Auto-removes invalid mappings
- MediaEmptyError: Falls back to text-only sending
- MessageNotModifiedError: Silently ignored for identical edits
- Connection errors: Auto-reconnection with retry logic

## Performance Considerations

- Task queue prevents overwhelming Telegram API
- Batch processing reduces API calls for small messages
- Performance monitoring tracks average mirror time
- Automatic queue size monitoring with degradation warnings
- Message history deque limited to 1000 entries

## Security Notes

- Session strings have full account access - handle securely
- API credentials stored in environment variables
- No sensitive data logging
- Graceful shutdown preserves state integrity