"""
Telegram session management
"""
import logging
import hashlib
import asyncio
from pathlib import Path
from typing import Optional, Tuple
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError, 
    FloodWaitError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError
)
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
import config

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages Telegram sessions for an account"""
    
    def __init__(self, account_path: Path):
        self.account_path = account_path
        self.sessions_dir = account_path / config.SESSION_DIR_NAME
        self.sessions_dir.mkdir(exist_ok=True)
        self.client: Optional[TelegramClient] = None
    
    def get_session_path(self, phone: str) -> Path:
        """Get session file path for a phone number"""
        session_hash = hashlib.md5(phone.encode()).hexdigest()
        return self.sessions_dir / f"{session_hash}.session"
    
    async def create_client(self, phone: str) -> TelegramClient:
        """Create a new Telegram client"""
        session_path = str(self.get_session_path(phone))
        client = TelegramClient(session_path, config.API_ID, config.API_HASH)
        await client.connect()
        return client
    
    async def initialize_from_db(self, session_file: str) -> bool:
        """Initialize client from saved session"""
        try:
            if not Path(session_file).exists():
                logger.error(f"Session file not found: {session_file}")
                return False
            
            self.client = TelegramClient(session_file, config.API_ID, config.API_HASH)
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.warning("Session is not authorized")
                await self.client.disconnect()
                self.client = None
                return False
            
            logger.info("Client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing client: {e}")
            if self.client:
                await self.client.disconnect()
                self.client = None
            return False
    
    async def send_code_request(self, phone: str) -> Tuple[bool, any]:
        """Send verification code"""
        try:
            client = await self.create_client(phone)
            code_info = await client.send_code_request(phone)
            return True, (client, code_info)
        except FloodWaitError as e:
            logger.error(f"Flood wait: {e.seconds} seconds")
            return False, f"Please wait {e.seconds} seconds before trying again"
        except Exception as e:
            logger.error(f"Error sending code: {e}")
            return False, str(e)
    
    async def sign_in_with_code(self, client: TelegramClient, phone: str, 
                                code: str, phone_code_hash: str) -> Tuple[bool, str]:
        """Sign in with verification code"""
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            self.client = client
            return True, "Success"
        except SessionPasswordNeededError:
            return False, "PASSWORD_REQUIRED"
        except PhoneCodeInvalidError:
            return False, "Invalid code"
        except PhoneCodeExpiredError:
            return False, "Code expired"
        except Exception as e:
            logger.error(f"Error signing in: {e}")
            return False, str(e)
    
    async def sign_in_with_password(self, client: TelegramClient, 
                                    password: str) -> Tuple[bool, str]:
        """Sign in with 2FA password"""
        try:
            await client.sign_in(password=password)
            self.client = client
            return True, "Success"
        except Exception as e:
            logger.error(f"Error with password: {e}")
            return False, str(e)
    
    async def join_group(self, group_link: str) -> Tuple[bool, any]:
        """Join a Telegram group"""
        if not self.client:
            return False, "Client not initialized"
        
        try:
            # Clean the link
            link = group_link.replace('https://t.me/', '').replace('t.me/', '')
            if link.startswith('@'):
                link = link[1:]
            
            # Try to join
            try:
                result = await self.client(JoinChannelRequest(link))
                entity = result.chats[0]
            except Exception:
                # Try with invite link
                if '+' in link or 'joinchat' in link:
                    invite_hash = link.split('/')[-1].replace('+', '')
                    result = await self.client(ImportChatInviteRequest(invite_hash))
                    entity = result.chats[0]
                else:
                    raise
            
            # Get full entity info
            full_entity = await self.client.get_entity(entity.id)
            
            return True, {
                'title': full_entity.title,
                'id': full_entity.id,
                'members_count': getattr(full_entity, 'participants_count', 0)
            }
        except Exception as e:
            error_msg = str(e)
            if "USER_ALREADY_PARTICIPANT" in error_msg:
                try:
                    entity = await self.client.get_entity(link)
                    return True, {
                        'title': entity.title,
                        'id': entity.id,
                        'members_count': getattr(entity, 'participants_count', 0)
                    }
                except:
                    pass
            logger.error(f"Error joining group: {e}")
            return False, error_msg
    
    async def send_message(self, entity_id: int, message: str) -> bool:
        """Send a message to an entity"""
        if not self.client:
            return False
        
        try:
            await self.client.send_message(entity_id, message)
            return True
        except FloodWaitError as e:
            logger.warning(f"Flood wait: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def send_to_multiple_groups(self, message: str, groups: list, 
                                     delay: int = 2) -> Tuple[int, int]:
        """Send message to multiple groups"""
        if not self.client:
            return 0, len(groups)
        
        successful = 0
        failed = 0
        
        for group in groups:
            try:
                group_id = group[3]  # group_id_telegram column
                if await self.send_message(group_id, message):
                    successful += 1
                else:
                    failed += 1
                
                # Delay between sends to avoid flood
                if delay > 0:
                    await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Error sending to group {group[2]}: {e}")
                failed += 1
        
        return successful, failed
    
    async def disconnect(self):
        """Disconnect the client"""
        if self.client:
            try:
                await self.client.disconnect()
                logger.info("Client disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            finally:
                self.client = None
    
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.client is not None and self.client.is_connected()
