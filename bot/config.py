"""
Configuration Management Module
Handles all bot settings and channel mappings
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger('Config')


class Config:
    """Configuration manager for the bot"""
    def __init__(self, config_path: str = 'data/settings.json'):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        # Load API credentials from environment
        api_id_str = os.getenv('API_ID', '0')
        try:
            self._api_id = int(api_id_str)
        except ValueError:
            logger.warning("Invalid API_ID in environment: %s - using default 0", api_id_str)
            self._api_id = 0
        self._api_hash = os.getenv('API_HASH', '')

        self._default_config = {
            'api_id': self._api_id,
            'api_hash': self._api_hash,
            'session_string': os.getenv('SESSION_STRING', ''),
            'log_channel_id': os.getenv('LOG_CHANNEL_ID', ''),
            'admin_users': [],  # List of admin user IDs who can control the bot
            'source_channel': None,  # Single source channel ID
            'target_channels': [],  # List of target channel IDs
            'channel_mappings': {},  # Legacy mappings (for compatibility)
            'message_cache': {},
            'stats': {
                'messages_mirrored': 0,
                'media_mirrored': 0,
                'errors': 0,
                'start_time': None
            },
            'options': {
                'mirror_enabled': True,
                'mirror_text': True,
                'mirror_media': True,
                'mirror_edits': True,
                'mirror_deletes': True,
                'bypass_restriction': True,
                'cache_media': False,
                'allow_all_users': True  # If True, all users can use commands
            },
            'log_channel': os.getenv('LOG_CHANNEL_ID', None)
        }

        self._config = self.load()
        # Ensure API credentials and session are always from environment
        self._config['api_id'] = self._api_id
        self._config['api_hash'] = self._api_hash
        # If session_string is in environment and not in config, use environment
        env_session = os.getenv('SESSION_STRING', '')
        if env_session and not self._config.get('session_string'):
            self._config['session_string'] = env_session

    def load(self) -> dict:
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, encoding='utf-8') as f:
                    config = json.load(f)
                    return {**self._default_config, **config}
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load config: %s", e)

        return self._default_config.copy()

    def save(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except OSError as e:
            logger.error("Failed to save config: %s", e)
            return False

    @property
    def api_id(self) -> int:
        """Get API ID"""
        return self._config.get('api_id', 0)

    @api_id.setter
    def api_id(self, value: int):
        self._config['api_id'] = value
        self.save()

    @property
    def api_hash(self) -> str:
        """Get API hash"""
        return self._config.get('api_hash', '')

    @api_hash.setter
    def api_hash(self, value: str):
        self._config['api_hash'] = value
        self.save()

    @property
    def session_string(self) -> str:
        """Get session string"""
        return self._config.get('session_string', '')

    @session_string.setter
    def session_string(self, value: str):
        self._config['session_string'] = value
        self.save()

    def add_mapping(self, source: int, target: int | None) -> bool:
        """Add channel mapping (target can be None for later configuration)"""
        source_str = str(source)
        target_str = str(target) if target is not None else None

        if source_str in self._config['channel_mappings']:
            logger.warning("Mapping already exists for %s", source)
            return False

        self._config['channel_mappings'][source_str] = target_str
        self.save()
        if target:
            logger.info("Added mapping: %s → %s", source, target)
        else:
            logger.info("Added source channel: %s (target not set)", source)
        return True

    def remove_mapping(self, source: int) -> bool:
        """Remove channel mapping"""
        source_str = str(source)

        if source_str not in self._config['channel_mappings']:
            return False

        del self._config['channel_mappings'][source_str]
        self.save()
        logger.info("Removed mapping for %s", source)
        return True

    def get_mapping(self, source: int) -> int | None:
        """Get target channel for source"""
        source_str = str(source)
        target = self._config['channel_mappings'].get(source_str)
        return int(target) if target else None

    def get_all_mappings(self) -> dict[int, int | None]:
        """Get all channel mappings"""
        return {
            int(k): int(v) if v is not None else None
            for k, v in self._config['channel_mappings'].items()
        }

    def clear_mappings(self):
        """Clear all mappings"""
        self._config['channel_mappings'] = {}
        self.save()
        logger.info("Cleared all mappings")

    def cache_message(self, source_msg_id: int, target_msg_id: int, source_chat: int):
        """Cache message ID mapping for edits/deletes"""
        key = f"{source_chat}_{source_msg_id}"
        self._config['message_cache'][key] = target_msg_id

        if len(self._config['message_cache']) > 10000:
            keys = list(self._config['message_cache'].keys())
            for k in keys[:1000]:
                del self._config['message_cache'][k]

    def get_cached_message(self, source_msg_id: int, source_chat: int) -> int | None:
        """Get cached target message ID"""
        key = f"{source_chat}_{source_msg_id}"
        return self._config['message_cache'].get(key)

    def update_stats(self, stat: str, increment: int = 1):
        """Update statistics"""
        if stat in self._config['stats']:
            self._config['stats'][stat] += increment
            self.save()

    def get_stats(self) -> dict:
        """Get bot statistics"""
        return self._config['stats']

    def reset_stats(self):
        """Reset statistics"""
        self._config['stats'] = {
            'messages_mirrored': 0,
            'media_mirrored': 0,
            'edits_mirrored': 0,
            'deletes_mirrored': 0,
            'errors': 0,
            'start_time': None
        }
        self.save()

    def get_option(self, option: str) -> bool:
        """Get option value"""
        return self._config['options'].get(option, False)

    def set_option(self, option: str, value: bool):
        """Set option value"""
        if option in self._config['options']:
            self._config['options'][option] = value
            self.save()
            logger.info("Set %s = %s", option, value)

    def get_log_channel(self) -> int | None:
        """Get log channel ID"""
        log_id = self._config.get('log_channel_id', '')
        if log_id:
            try:
                return int(log_id)
            except ValueError:
                return None
        return None

    def set_log_channel(self, channel_id: int | None):
        """Set log channel ID"""
        if channel_id:
            self._config['log_channel_id'] = str(channel_id)
        else:
            self._config['log_channel_id'] = ''
        self.save()
        logger.info("Set log channel = %s", channel_id)

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        # If allow_all_users is True, everyone is admin
        if self._config['options'].get('allow_all_users', True):
            return True

        # Otherwise check admin list
        admin_users = self._config.get('admin_users', [])
        return user_id in admin_users

    def add_admin(self, user_id: int) -> bool:
        """Add admin user"""
        if 'admin_users' not in self._config:
            self._config['admin_users'] = []

        if user_id not in self._config['admin_users']:
            self._config['admin_users'].append(user_id)
            self.save()
            return True
        return False

    def remove_admin(self, user_id: int) -> bool:
        """Remove admin user"""
        if 'admin_users' in self._config and user_id in self._config['admin_users']:
            self._config['admin_users'].remove(user_id)
            self.save()
            return True
        return False

    def get_source_channel(self) -> int | None:
        """Get source channel ID"""
        source = self._config.get('source_channel')
        return int(source) if source else None

    def set_source_channel(self, channel_id: int | None):
        """Set source channel ID"""
        self._config['source_channel'] = channel_id
        self.save()
        logger.info("Set source channel: %s", channel_id)

    def get_target_channels(self) -> list:
        """Get list of target channel IDs"""
        return self._config.get('target_channels', [])

    def add_target_channel(self, channel_id: int) -> bool:
        """Add a target channel"""
        if 'target_channels' not in self._config:
            self._config['target_channels'] = []

        if channel_id not in self._config['target_channels']:
            self._config['target_channels'].append(channel_id)
            self.save()
            logger.info("Added target channel: %s", channel_id)
            return True
        return False

    def remove_target_channel(self, channel_id: int) -> bool:
        """Remove a target channel"""
        if 'target_channels' in self._config and channel_id in self._config['target_channels']:
            self._config['target_channels'].remove(channel_id)
            self.save()
            logger.info("Removed target channel: %s", channel_id)
            return True
        return False

    def export_config(self) -> str:
        """Export configuration as JSON string"""
        export_data = {
            'channel_mappings': self._config['channel_mappings'],
            'options': self._config['options']
        }
        return json.dumps(export_data, indent=2)

    def import_config(self, json_str: str) -> bool:
        """Import configuration from JSON string"""
        try:
            data = json.loads(json_str)
            if 'channel_mappings' in data:
                self._config['channel_mappings'] = data['channel_mappings']
            if 'options' in data:
                self._config['options'].update(data['options'])
            self.save()
            return True
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("Import failed: %s", e)
            return False
