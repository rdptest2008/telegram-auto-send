"""
Database management for the Telegram bot
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
import random

logger = logging.getLogger(__name__)


class Database:
    """Database handler for account data"""
    
    def __init__(self, account_path: Path):
        self.account_path = account_path
        self.db_path = account_path / 'bot.db'
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # User account table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_account (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                session_file TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Groups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_link TEXT UNIQUE NOT NULL,
                group_title TEXT,
                group_id_telegram INTEGER,
                members_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_message_sent TIMESTAMP
            )
        ''')
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT NOT NULL,
                min_minutes INTEGER DEFAULT 60,
                max_minutes INTEGER DEFAULT 90,
                is_active BOOLEAN DEFAULT 1,
                total_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_sent TIMESTAMP,
                next_send TIMESTAMP
            )
        ''')
        
        # Statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE DEFAULT (date('now')),
                messages_sent INTEGER DEFAULT 0,
                successful_sends INTEGER DEFAULT 0,
                failed_sends INTEGER DEFAULT 0,
                UNIQUE(date)
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT
            )
        ''')
        
        # Default settings
        default_settings = [
            ('min_interval', '60', 'Minimum interval between messages (minutes)'),
            ('max_interval', '90', 'Maximum interval between messages (minutes)'),
            ('auto_send', '1', 'Auto-send enabled (1/0)'),
            ('send_delay', '2', 'Delay between sending to groups (seconds)')
        ]
        
        for key, value, desc in default_settings:
            cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value, description)
                VALUES (?, ?, ?)
            ''', (key, value, desc))
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    # User methods
    def save_user(self, phone: str, session_file: str) -> bool:
        """Save user account"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_account (phone, session_file, last_login)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (phone, session_file))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            return False
    
    def get_user(self) -> Optional[Tuple]:
        """Get user account"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user_account WHERE is_active = 1 LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def user_exists(self) -> bool:
        """Check if user exists"""
        return self.get_user() is not None
    
    # Group methods
    def add_group(self, group_link: str, group_title: str, 
                  group_id_telegram: Optional[int] = None, 
                  members_count: int = 0) -> bool:
        """Add a group"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO groups (group_link, group_title, group_id_telegram, members_count)
                VALUES (?, ?, ?, ?)
            ''', (group_link, group_title, group_id_telegram, members_count))
            conn.commit()
            conn.close()
            logger.info(f"Added group: {group_title}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Group already exists: {group_link}")
            return False
        except Exception as e:
            logger.error(f"Error adding group: {e}")
            return False
    
    def get_groups(self, active_only: bool = True) -> List[Tuple]:
        """Get all groups"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if active_only:
                cursor.execute('SELECT * FROM groups WHERE is_active = 1')
            else:
                cursor.execute('SELECT * FROM groups')
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            return []
    
    def update_group_status(self, group_id: int, is_active: bool) -> bool:
        """Update group status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE groups SET is_active = ? WHERE id = ?
            ''', (int(is_active), group_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating group status: {e}")
            return False
    
    def delete_group(self, group_id: int) -> bool:
        """Delete a group"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM groups WHERE id = ?', (group_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting group: {e}")
            return False
    
    # Message methods
    def add_message(self, message_text: str, min_minutes: int = 60, 
                   max_minutes: int = 90) -> bool:
        """Add a message"""
        try:
            next_send = datetime.now() + timedelta(
                minutes=random.randint(min_minutes, max_minutes)
            )
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (message_text, min_minutes, max_minutes, next_send)
                VALUES (?, ?, ?, ?)
            ''', (message_text, min_minutes, max_minutes, next_send))
            conn.commit()
            conn.close()
            logger.info(f"Added message, next send at {next_send}")
            return True
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False
    
    def get_messages(self, active_only: bool = True) -> List[Tuple]:
        """Get all messages"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if active_only:
                cursor.execute('SELECT * FROM messages WHERE is_active = 1')
            else:
                cursor.execute('SELECT * FROM messages')
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []
    
    def get_pending_messages(self) -> List[Tuple]:
        """Get messages ready to send"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM messages 
                WHERE is_active = 1 AND next_send <= datetime('now')
            ''')
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Error getting pending messages: {e}")
            return []
    
    def update_message_after_send(self, message_id: int) -> bool:
        """Update message after sending"""
        try:
            min_minutes = int(self.get_setting('min_interval', '60'))
            max_minutes = int(self.get_setting('max_interval', '90'))
            next_send = datetime.now() + timedelta(
                minutes=random.randint(min_minutes, max_minutes)
            )
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE messages 
                SET total_sent = total_sent + 1,
                    last_sent = datetime('now'),
                    next_send = ?
                WHERE id = ?
            ''', (next_send, message_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            return False
    
    def delete_message(self, message_id: int) -> bool:
        """Delete a message"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False
    
    # Settings methods
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else default
        except Exception as e:
            logger.error(f"Error getting setting: {e}")
            return default
    
    def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error setting value: {e}")
            return False
    
    def get_all_settings(self) -> List[Tuple]:
        """Get all settings"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT key, value, description FROM settings')
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return []
    
    # Statistics methods
    def update_stats(self, messages_sent: int, successful: int, failed: int) -> bool:
        """Update statistics"""
        try:
            today = datetime.now().date().isoformat()
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO statistics (date, messages_sent, successful_sends, failed_sends)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    messages_sent = messages_sent + excluded.messages_sent,
                    successful_sends = successful_sends + excluded.successful_sends,
                    failed_sends = failed_sends + excluded.failed_sends
            ''', (today, messages_sent, successful, failed))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
            return False
    
    def get_today_stats(self) -> dict:
        """Get today's statistics"""
        try:
            today = datetime.now().date().isoformat()
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT messages_sent, successful_sends, failed_sends 
                FROM statistics WHERE date = ?
            ''', (today,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'messages_sent': result[0],
                    'successful': result[1],
                    'failed': result[2]
                }
            return {'messages_sent': 0, 'successful': 0, 'failed': 0}
        except Exception as e:
            logger.error(f"Error getting today stats: {e}")
            return {'messages_sent': 0, 'successful': 0, 'failed': 0}
    
    def get_total_stats(self) -> dict:
        """Get total statistics"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Total messages sent
            cursor.execute('SELECT SUM(total_sent) FROM messages')
            total_sent = cursor.fetchone()[0] or 0
            
            # Total groups
            cursor.execute('SELECT COUNT(*) FROM groups WHERE is_active = 1')
            total_groups = cursor.fetchone()[0] or 0
            
            # Total messages
            cursor.execute('SELECT COUNT(*) FROM messages WHERE is_active = 1')
            total_messages = cursor.fetchone()[0] or 0
            
            conn.close()
            
            today_stats = self.get_today_stats()
            
            return {
                'total_sent': total_sent,
                'total_groups': total_groups,
                'total_messages': total_messages,
                'today_sent': today_stats['messages_sent'],
                'today_successful': today_stats['successful'],
                'today_failed': today_stats['failed']
            }
        except Exception as e:
            logger.error(f"Error getting total stats: {e}")
            return {
                'total_sent': 0,
                'total_groups': 0,
                'total_messages': 0,
                'today_sent': 0,
                'today_successful': 0,
                'today_failed': 0
          }
