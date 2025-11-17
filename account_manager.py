"""
Account management for the Telegram bot
"""
import logging
from pathlib import Path
from typing import List, Optional
import config

logger = logging.getLogger(__name__)


class AccountManager:
    """Manages user accounts"""
    
    def __init__(self):
        self.accounts_dir = config.ACCOUNTS_DIR
        self.accounts_dir.mkdir(exist_ok=True)
    
    def get_account_path(self, account_id: str) -> Path:
        """Get account directory path"""
        return self.accounts_dir / account_id
    
    def create_account(self, account_id: str) -> Path:
        """Create a new account directory"""
        account_path = self.get_account_path(account_id)
        account_path.mkdir(exist_ok=True)
        
        # Create sessions subdirectory
        sessions_path = account_path / config.SESSION_DIR_NAME
        sessions_path.mkdir(exist_ok=True)
        
        logger.info(f"Created account: {account_id}")
        return account_path
    
    def account_exists(self, account_id: str) -> bool:
        """Check if account exists"""
        return self.get_account_path(account_id).exists()
    
    def get_all_accounts(self) -> List[str]:
        """Get list of all account IDs"""
        try:
            return [
                d.name for d in self.accounts_dir.iterdir() 
                if d.is_dir() and not d.name.startswith('.')
            ]
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return []
    
    def delete_account(self, account_id: str) -> bool:
        """Delete an account"""
        try:
            import shutil
            account_path = self.get_account_path(account_id)
            if account_path.exists():
                shutil.rmtree(account_path)
                logger.info(f"Deleted account: {account_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            return False
    
    def get_user_account_id(self, user_id: int) -> str:
        """Get account ID for a user"""
        return f"user_{user_id}"
    
    def is_user_account(self, account_id: str, user_id: int) -> bool:
        """Check if account belongs to user"""
        return account_id == self.get_user_account_id(user_id)
    
    def can_access_account(self, user_id: int, account_id: str) -> bool:
        """Check if user can access account"""
        # Admin can access all accounts
        if user_id == config.ADMIN_USER_ID:
            return True
        
        # Users can only access their own account
        return self.is_user_account(account_id, user_id)
