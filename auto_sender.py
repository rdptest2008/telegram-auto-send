"""
Automatic message sender for scheduled messages
"""
import asyncio
import logging
from typing import Dict
from pathlib import Path
from database import Database
from session_manager import SessionManager
import config

logger = logging.getLogger(__name__)


class AutoSender:
    """Handles automatic sending of scheduled messages"""
    
    def __init__(self, account_manager):
        self.account_manager = account_manager
        self.active_sessions: Dict[str, SessionManager] = {}
        self.running = False
    
    async def start(self):
        """Start the auto-send loop"""
        self.running = True
        logger.info("Auto-sender started")
        
        while self.running:
            try:
                await self.process_all_accounts()
                await asyncio.sleep(config.AUTO_SEND_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Error in auto-send loop: {e}")
                await asyncio.sleep(60)
    
    def stop(self):
        """Stop the auto-send loop"""
        self.running = False
        logger.info("Auto-sender stopped")
    
    async def process_all_accounts(self):
        """Process all accounts for pending messages"""
        accounts = self.account_manager.get_all_accounts()
        
        for account_id in accounts:
            try:
                await self.process_account(account_id)
            except Exception as e:
                logger.error(f"Error processing account {account_id}: {e}")
    
    async def process_account(self, account_id: str):
        """Process a single account"""
        account_path = self.account_manager.get_account_path(account_id)
        db = Database(account_path)
        
        # Check if auto-send is enabled
        auto_send = db.get_setting('auto_send', '1')
        if auto_send != '1':
            return
        
        # Get pending messages
        pending_messages = db.get_pending_messages()
        if not pending_messages:
            return
        
        # Get active groups
        groups = db.get_groups(active_only=True)
        if not groups:
            logger.warning(f"No active groups for account {account_id}")
            return
        
        # Initialize session if needed
        session_manager = await self.get_or_create_session(account_id, db)
        if not session_manager or not session_manager.is_connected():
            logger.warning(f"Session not available for account {account_id}")
            return
        
        # Send messages
        delay = int(db.get_setting('send_delay', str(config.MESSAGE_DELAY_BETWEEN_GROUPS)))
        
        for message in pending_messages:
            await self.send_message(account_id, message, groups, session_manager, db, delay)
    
    async def send_message(self, account_id: str, message: tuple, groups: list,
                          session_manager: SessionManager, db: Database, delay: int):
        """Send a single message to all groups"""
        message_id = message[0]
        message_text = message[1]
        
        try:
            logger.info(f"Sending message {message_id} from account {account_id}")
            
            successful, failed = await session_manager.send_to_multiple_groups(
                message_text, groups, delay
            )
            
            # Update message and statistics
            db.update_message_after_send(message_id)
            db.update_stats(successful + failed, successful, failed)
            
            logger.info(
                f"Message {message_id} sent: {successful} successful, {failed} failed"
            )
        except Exception as e:
            logger.error(f"Error sending message {message_id}: {e}")
    
    async def get_or_create_session(self, account_id: str, 
                                   db: Database) -> SessionManager:
        """Get or create a session manager for an account"""
        # Check if session already exists
        if account_id in self.active_sessions:
            session_manager = self.active_sessions[account_id]
            if session_manager.is_connected():
                return session_manager
        
        # Create new session
        user_data = db.get_user()
        if not user_data:
            return None
        
        session_file = user_data[2]  # session_file column
        account_path = self.account_manager.get_account_path(account_id)
        session_manager = SessionManager(account_path)
        
        if await session_manager.initialize_from_db(session_file):
            self.active_sessions[account_id] = session_manager
            return session_manager
        
        return None
    
    async def send_now(self, account_id: str) -> dict:
        """Send all messages immediately"""
        account_path = self.account_manager.get_account_path(account_id)
        db = Database(account_path)
        
        # Get all active messages
        messages = db.get_messages(active_only=True)
        if not messages:
            return {'success': False, 'message': 'No active messages'}
        
        # Get active groups
        groups = db.get_groups(active_only=True)
        if not groups:
            return {'success': False, 'message': 'No active groups'}
        
        # Initialize session
        session_manager = await self.get_or_create_session(account_id, db)
        if not session_manager:
            return {'success': False, 'message': 'Session not available'}
        
        # Send all messages
        delay = int(db.get_setting('send_delay', str(config.MESSAGE_DELAY_BETWEEN_GROUPS)))
        total_successful = 0
        total_failed = 0
        
        for message in messages:
            message_text = message[1]
            successful, failed = await session_manager.send_to_multiple_groups(
                message_text, groups, delay
            )
            total_successful += successful
            total_failed += failed
        
        # Update statistics
        db.update_stats(total_successful + total_failed, total_successful, total_failed)
        
        return {
            'success': True,
            'successful': total_successful,
            'failed': total_failed,
            'messages_count': len(messages),
            'groups_count': len(groups)
        }
    
    async def cleanup_session(self, account_id: str):
        """Clean up a session"""
        if account_id in self.active_sessions:
            session_manager = self.active_sessions[account_id]
            await session_manager.disconnect()
            del self.active_sessions[account_id]
            logger.info(f"Cleaned up session for {account_id}")
    
    async def cleanup_all_sessions(self):
        """Clean up all sessions"""
        for account_id in list(self.active_sessions.keys()):
            await self.cleanup_session(account_id)
        logger.info("All sessions cleaned up")
