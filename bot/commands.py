"""
Commands Handler Module
CLI-style command processing for bot configuration
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from colorama import Fore, Style

from telethon import TelegramClient, events
from telethon.tl.types import User, Chat, Channel

logger = logging.getLogger('Commands')


class CommandHandler:
    def __init__(self, client: TelegramClient, config, mirror_engine):
        self.client = client
        self.config = config
        self.mirror_engine = mirror_engine
        self.session_input_mode = False
        
    async def handle_command(self, event: events.NewMessage.Event):
        """Main command router"""
        message = event.message
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) == 1 and parts[0] == '.설정':
            await self.show_help(event)
            return
        
        if len(parts) < 2:
            await event.reply("Usage: .설정 [command] [args...]")
            return
        
        command = parts[1].lower()
        args = parts[2:] if len(parts) > 2 else []
        
        commands = {
            'help': self.show_help,
            'map': self.handle_map,
            'session': self.handle_session,
            'bot': self.handle_bot,
            'stats': self.handle_stats,
            'config': self.handle_config,
            
            'ls': lambda e, a: self.handle_map(e, ['list']),
            'add': lambda e, a: self.handle_map(e, ['add'] + a),
            'rm': lambda e, a: self.handle_map(e, ['del'] + a),
            'st': lambda e, a: self.handle_bot(e, ['status']),
        }
        
        handler = commands.get(command)
        if handler:
            try:
                await handler(event, args)
            except Exception as e:
                logger.error(f"Command error: {e}")
                await event.reply(f"❌ Error: {e}")
        else:
            await event.reply(f"Unknown command: {command}\nType '.설정 help' for help")
    
    async def show_help(self, event, args=None):
        """Show help message"""
        if args and len(args) > 0:
            command = args[0]
            help_text = self.get_command_help(command)
        else:
            help_text = """
**Mirror Bot CLI v1.0**
```
Usage: .설정 [command] [subcommand] [args]

Commands:
  map     - Channel mapping management
  session - Session configuration  
  bot     - Bot control
  stats   - Statistics and monitoring
  config  - Configuration management
  help    - Show help

Shortcuts:
  ls  = map list
  add = map add
  rm  = map del
  st  = bot status

Type '.설정 help [command]' for details
```"""
        
        await event.reply(help_text)
    
    def get_command_help(self, command: str) -> str:
        """Get detailed help for specific command"""
        helps = {
            'map': """
**Channel Mapping Commands**
```
.설정 map list              - List all mappings
.설정 map add [src] [tgt]   - Add new mapping
.설정 map del [index/src]   - Remove mapping
.설정 map clear             - Clear all mappings
```""",
            'session': """
**Session Commands**
```
.설정 session set           - Set new session string
.설정 session info          - Show session info
.설정 session test          - Test session validity
.설정 session clear         - Clear session
```""",
            'bot': """
**Bot Control Commands**
```
.설정 bot start             - Start mirroring
.설정 bot stop              - Stop mirroring
.설정 bot restart           - Restart bot
.설정 bot status            - Show status
```""",
            'stats': """
**Statistics Commands**
```
.설정 stats                 - Show statistics
.설정 stats reset           - Reset statistics
```""",
            'config': """
**Configuration Commands**
```
.설정 config show           - Show configuration
.설정 config save           - Export config
.설정 config load           - Import config
.설정 config option [name] [on/off] - Set option
```"""
        }
        
        return helps.get(command, f"No help available for '{command}'")
    
    async def handle_map(self, event, args):
        """Handle mapping commands"""
        if not args:
            await self.show_help(event, ['map'])
            return
        
        subcommand = args[0].lower()
        
        if subcommand == 'list':
            await self.list_mappings(event)
        
        elif subcommand == 'add':
            if len(args) < 3:
                await event.reply("Usage: .설정 map add [source_id] [target_id]")
                return
            await self.add_mapping(event, args[1], args[2])
        
        elif subcommand in ['del', 'delete', 'remove']:
            if len(args) < 2:
                await event.reply("Usage: .설정 map del [index or source_id]")
                return
            await self.remove_mapping(event, args[1])
        
        elif subcommand == 'clear':
            await self.clear_mappings(event)
        
        else:
            await event.reply(f"Unknown map command: {subcommand}")
    
    async def list_mappings(self, event):
        """List all channel mappings"""
        mappings = self.config.get_all_mappings()
        
        if not mappings:
            await event.reply("📋 No mappings configured")
            return
        
        text = "**Channel Mappings:**\n```"
        for idx, (source, target) in enumerate(mappings.items(), 1):
            try:
                src_entity = await self.client.get_entity(source)
                tgt_entity = await self.client.get_entity(target)
                
                src_name = self.get_entity_name(src_entity)
                tgt_name = self.get_entity_name(tgt_entity)
                
                text += f"[{idx}] {source} → {target}\n"
                text += f"    {src_name} → {tgt_name}\n"
            except:
                text += f"[{idx}] {source} → {target}\n"
        
        text += "```"
        await event.reply(text)
    
    async def add_mapping(self, event, source: str, target: str):
        """Add new channel mapping"""
        try:
            src_id = int(source) if source.lstrip('-').isdigit() else None
            tgt_id = int(target) if target.lstrip('-').isdigit() else None
            
            if not src_id:
                src_entity = await self.client.get_entity(source)
                src_id = src_entity.id
                if isinstance(src_entity, Channel):
                    if getattr(src_entity, 'broadcast', False):
                        src_id = -1000000000000 - src_id
                    elif getattr(src_entity, 'megagroup', False):
                        src_id = -1000000000000 - src_id
                else:
                    src_id = -src_id if src_id > 0 else src_id
            
            if not tgt_id:
                tgt_entity = await self.client.get_entity(target)
                tgt_id = tgt_entity.id
                if isinstance(tgt_entity, Channel):
                    if getattr(tgt_entity, 'broadcast', False):
                        tgt_id = -1000000000000 - tgt_id
                    elif getattr(tgt_entity, 'megagroup', False):
                        tgt_id = -1000000000000 - tgt_id
                else:
                    tgt_id = -tgt_id if tgt_id > 0 else tgt_id
            
            if self.config.add_mapping(src_id, tgt_id):
                await event.reply(f"✅ Mapping added:\n`{src_id}` → `{tgt_id}`")
            else:
                await event.reply(f"⚠️ Mapping already exists for {src_id}")
                
        except Exception as e:
            await event.reply(f"❌ Failed to add mapping: {e}")
    
    async def remove_mapping(self, event, identifier: str):
        """Remove channel mapping"""
        mappings = self.config.get_all_mappings()
        
        if identifier.isdigit():
            idx = int(identifier) - 1
            if 0 <= idx < len(mappings):
                source = list(mappings.keys())[idx]
                if self.config.remove_mapping(source):
                    await event.reply(f"✅ Removed mapping for {source}")
                else:
                    await event.reply(f"❌ Failed to remove mapping")
            else:
                await event.reply(f"❌ Invalid index: {identifier}")
        else:
            source = int(identifier) if identifier.lstrip('-').isdigit() else None
            if source and self.config.remove_mapping(source):
                await event.reply(f"✅ Removed mapping for {source}")
            else:
                await event.reply(f"❌ Mapping not found: {identifier}")
    
    async def clear_mappings(self, event):
        """Clear all mappings"""
        self.config.clear_mappings()
        await event.reply("✅ All mappings cleared")
    
    async def handle_session(self, event, args):
        """Handle session commands"""
        if not args:
            await self.show_help(event, ['session'])
            return
        
        subcommand = args[0].lower()
        
        if subcommand == 'set':
            await event.reply("Please send the session string in the next message (in private):")
            self.session_input_mode = True
            
            @self.client.on(events.NewMessage(from_users=event.sender_id))
            async def session_handler(session_event):
                if self.session_input_mode:
                    self.session_input_mode = False
                    session_string = session_event.message.text.strip()
                    
                    from session_handler import SessionManager
                    session_mgr = SessionManager(self.config)
                    
                    if await session_mgr.validate_session(session_string):
                        await session_mgr.save_session(session_string)
                        await session_event.reply("✅ Session saved successfully")
                    else:
                        await session_event.reply("❌ Invalid session string")
                    
                    self.client.remove_event_handler(session_handler)
        
        elif subcommand == 'info':
            from .session_handler import SessionManager
            session_mgr = SessionManager(self.config)
            info = await session_mgr.get_session_info()
            
            if info:
                text = f"""**Session Information:**
```
User ID: {info['id']}
Username: @{info['username'] or 'N/A'}
Name: {info['first_name']} {info['last_name'] or ''}
Phone: {info['phone'] or 'Hidden'}
Premium: {'Yes' if info['premium'] else 'No'}
Verified: {'Yes' if info['verified'] else 'No'}
```"""
                await event.reply(text)
            else:
                await event.reply("❌ No valid session found")
        
        elif subcommand == 'test':
            from .session_handler import SessionManager
            session_mgr = SessionManager(self.config)
            session = await session_mgr.get_session()
            
            if session and await session_mgr.validate_session(session):
                await event.reply("✅ Session is valid")
            else:
                await event.reply("❌ Session is invalid or not set")
        
        elif subcommand == 'clear':
            from .session_handler import SessionManager
            session_mgr = SessionManager(self.config)
            session_mgr.clear_session()
            await event.reply("✅ Session cleared")
        
        else:
            await event.reply(f"Unknown session command: {subcommand}")
    
    async def handle_bot(self, event, args):
        """Handle bot control commands"""
        if not args:
            await self.show_help(event, ['bot'])
            return
        
        subcommand = args[0].lower()
        
        if subcommand == 'start':
            self.config.set_option('mirror_enabled', True)
            await event.reply("✅ Mirroring started")
        
        elif subcommand == 'stop':
            self.config.set_option('mirror_enabled', False)
            await event.reply("⏸️ Mirroring stopped")
        
        elif subcommand == 'restart':
            await event.reply("🔄 Restarting bot...")
            import sys
            import os
            os.execv(sys.executable, [sys.executable] + sys.argv)
        
        elif subcommand == 'status':
            status = self.mirror_engine.get_status()
            stats = status['stats']
            options = status['options']
            
            uptime = "N/A"
            if stats.get('start_time'):
                start = datetime.fromisoformat(stats['start_time'])
                uptime = str(datetime.now() - start).split('.')[0]
            
            text = f"""**Bot Status:**
```
State: {'RUNNING' if status['enabled'] else 'STOPPED'}
Mappings: {status['mappings_count']} active
Processing: {status['processing_count']} messages
Uptime: {uptime}

Statistics:
• Messages: {stats.get('messages_mirrored', 0)}
• Media: {stats.get('media_mirrored', 0)}
• Errors: {stats.get('errors', 0)}

Options:
• Text: {'✓' if options['text'] else '✗'}
• Media: {'✓' if options['media'] else '✗'}
• Edits: {'✓' if options['edits'] else '✗'}
• Deletes: {'✓' if options['deletes'] else '✗'}
• Bypass: {'✓' if options['bypass'] else '✗'}
```"""
            await event.reply(text)
        
        else:
            await event.reply(f"Unknown bot command: {subcommand}")
    
    async def handle_stats(self, event, args):
        """Handle statistics commands"""
        if args and args[0].lower() == 'reset':
            self.config.reset_stats()
            await event.reply("✅ Statistics reset")
        else:
            stats = self.config.get_stats()
            text = f"""**Mirror Statistics:**
```
Messages Mirrored: {stats.get('messages_mirrored', 0)}
Media Mirrored: {stats.get('media_mirrored', 0)}
Errors: {stats.get('errors', 0)}
```"""
            await event.reply(text)
    
    async def handle_config(self, event, args):
        """Handle configuration commands"""
        if not args:
            await self.show_help(event, ['config'])
            return
        
        subcommand = args[0].lower()
        
        if subcommand == 'show':
            options = self.config._config['options']
            text = "**Configuration:**\n```"
            for key, value in options.items():
                text += f"{key}: {value}\n"
            text += "```"
            await event.reply(text)
        
        elif subcommand == 'save':
            export = self.config.export_config()
            await event.reply(f"**Exported Config:**\n```json\n{export}\n```")
        
        elif subcommand == 'load':
            await event.reply("Send the JSON config in the next message:")
        
        elif subcommand == 'option':
            if len(args) < 3:
                await event.reply("Usage: .설정 config option [name] [on/off]")
                return
            
            option = args[1]
            value = args[2].lower() in ['on', 'true', '1', 'yes']
            self.config.set_option(option, value)
            await event.reply(f"✅ Set {option} = {value}")
        
        else:
            await event.reply(f"Unknown config command: {subcommand}")
    
    def get_entity_name(self, entity) -> str:
        """Get readable name for entity"""
        if isinstance(entity, User):
            return f"@{entity.username}" if entity.username else f"{entity.first_name}"
        elif isinstance(entity, (Chat, Channel)):
            username = getattr(entity, 'username', None)
            return f"@{username}" if username else entity.title
        return "Unknown"