"""
Main entry point for the Telegram bot
"""
import asyncio
import logging
import signal
import sys
from telethon import TelegramClient, events
from account_manager import AccountManager
from auto_sender import AutoSender
from handlers import BotHandlers
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Main bot class"""
    
    def __init__(self):
        self.bot = None
        self.account_manager = AccountManager()
        self.auto_sender = AutoSender(self.account_manager)
        self.handlers = BotHandlers(self.account_manager, self.auto_sender)
        self.running = False
    
    async def start(self):
        """Start the bot"""
        try:
            # Create bot client
            self.bot = TelegramClient('bot_session', config.API_ID, config.API_HASH)
            
            # Register event handlers
            self.register_handlers()
            
            # Start bot
            await self.bot.start(bot_token=config.BOT_TOKEN)
            logger.info("✅ Bot started successfully")
            
            # Get bot info
            me = await self.bot.get_me()
            logger.info(f"Bot username: @{me.username}")
            
            # Start auto-sender
            self.running = True
            asyncio.create_task(self.auto_sender.start())
            
            # Keep running
            await self.bot.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
    
    def register_handlers(self):
        """Register all event handlers"""
        
        # Start command
        @self.bot.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            try:
                await self.handlers.handle_start(event)
            except Exception as e:
                logger.error(f"Error in start handler: {e}")
                await event.reply("❌ An error occurred")
        
        # Callback query handler
        @self.bot.on(events.CallbackQuery)
        async def callback_handler(event):
            try:
                await self.handle_callback(event)
            except Exception as e:
                logger.error(f"Error in callback handler: {e}")
                await event.answer("❌ An error occurred", alert=True)
        
        # Message handler
        @self.bot.on(events.NewMessage)
        async def message_handler(event):
            try:
                # Skip commands
                if event.text and event.text.startswith('/'):
                    return
                await self.handlers.handle_message(event)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
    
    async def handle_callback(self, event):
        """Handle callback queries"""
        user_id = event.sender_id
        data = event.data.decode('utf-8')
        
        # Check access permissions
        if ':' in data:
            action, account_id = data.split(':', 1)
            if not self.account_manager.can_access_account(user_id, account_id):
                await event.answer("❌ Access denied", alert=True)
                return
        
        # Route callbacks
        if data == "create_account":
            await self.handlers.handle_create_account(event)
        
        elif data == "create_user_account":
            await self.handlers.handle_create_account(event)
        
        elif data.startswith("select:"):
            account_id = data.split(":", 1)[1]
            await self.handlers.show_account_menu(event, account_id)
        
        elif data.startswith("login:"):
            account_id = data.split(":", 1)[1]
            await self.handlers.start_login(event, account_id)
        
        elif data.startswith("add_group:"):
            account_id = data.split(":", 1)[1]
            await self.handlers.start_add_group(event, account_id)
        
        elif data.startswith("add_msg:"):
            account_id = data.split(":", 1)[1]
            await self.handlers.start_add_message(event, account_id)
        
        elif data.startswith("send_now:"):
            account_id = data.split(":", 1)[1]
            await self.handlers.handle_send_now(event, account_id)
        
        elif data.startswith("settings:"):
            account_id = data.split(":", 1)[1]
            await self.handlers.show_settings(event, account_id)
        
        elif data.startswith("stats:"):
            account_id = data.split(":", 1)[1]
            await self.handlers.show_stats(event, account_id)
        
        elif data == "back_main":
            await self.handlers.handle_start(event)
        
        else:
            await event.answer("Unknown action", alert=True)
    
    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot...")
        self.running = False
        
        # Stop auto-sender
        self.auto_sender.stop()
        await self.auto_sender.cleanup_all_sessions()
        
        # Disconnect bot
        if self.bot:
            await self.bot.disconnect()
        
        logger.info("Bot stopped")


# Global bot instance
bot_instance = None


async def main():
    """Main function"""
    global bot_instance
    
    bot_instance = TelegramBot()
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        if bot_instance:
            asyncio.create_task(bot_instance.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start bot
    await bot_instance.start()


if __name__ == '__main__':
    print("🚀 Starting Telegram Bot...")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
    finally:
        print("=" * 50)
        print("Bot shutdown complete")
