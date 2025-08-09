"""
Configuration Management Module
Handles all bot settings and channel mappings
"""

import json
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger('Config')


class Config:
    """Configuration manager for the bot"""
    def __init__(self, config_path: str = 'data/settings.json'):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        self._default_config = {
            'api_id': 0,
            'api_hash': '',
            'session_string': '',
            'channel_mappings': {},
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
                'cache_media': False
            }
        }

        self._config = self.load()

    def load(self) -> dict:
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**self._default_config, **config}
            except (json.JSONDecodeError, OSError, IOError) as e:
                logger.error("Failed to load config: %s", e)

        return self._default_config.copy()

    def save(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except (OSError, IOError) as e:
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

    def add_mapping(self, source: int, target: int) -> bool:
        """Add channel mapping"""
        source_str = str(source)
        target_str = str(target)

        if source_str in self._config['channel_mappings']:
            logger.warning("Mapping already exists for %s", source)
            return False

        self._config['channel_mappings'][source_str] = target_str
        self.save()
        logger.info("Added mapping: %s → %s", source, target)
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

    def get_mapping(self, source: int) -> Optional[int]:
        """Get target channel for source"""
        source_str = str(source)
        target = self._config['channel_mappings'].get(source_str)
        return int(target) if target else None

    def get_all_mappings(self) -> Dict[int, int]:
        """Get all channel mappings"""
        return {
            int(k): int(v)
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

    def get_cached_message(self, source_msg_id: int, source_chat: int) -> Optional[int]:
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
