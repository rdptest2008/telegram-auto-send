"""
Command and callback handlers for the bot
"""
import logging
import re
from telethon import Button
from database import Database
from session_manager import SessionManager
import config

logger = logging.getLogger(__name__)


class BotHandlers:
    """Handles bot commands and callbacks"""
    
    def __init__(self, account_manager, auto_sender):
        self.account_manager = account_manager
        self.auto_sender = auto_sender
        self.user_states = {}
    
    # ==================== Start Command ====================
    async def handle_start(self, event):
        """Handle /start command"""
        user_id = event.sender_id
        
        if user_id == config.ADMIN_USER_ID:
            await self.show_admin_menu(event)
        else:
            await self.show_user_menu(event, user_id)
    
    async def show_admin_menu(self, event):
        """Show admin menu"""
        accounts = self.account_manager.get_all_accounts()
        
        text = "👑 **Admin Panel**\n\nSelect an account to manage:"
        
        buttons = []
        for account_id in accounts:
            buttons.append([Button.inline(f"📱 {account_id}", f"select:{account_id}")])
        buttons.append([Button.inline("➕ Create Account", "create_account")])
        
        await event.reply(text, buttons=buttons)
    
    async def show_user_menu(self, event, user_id):
        """Show user menu"""
        account_id = self.account_manager.get_user_account_id(user_id)
        
        if self.account_manager.account_exists(account_id):
            await self.show_account_menu(event, account_id)
        else:
            text = "🔐 **Welcome!**\n\nCreate your account to get started:"
            buttons = [[Button.inline("➕ Create Account", "create_user_account")]]
            await event.reply(text, buttons=buttons)
    
    # ==================== Account Management ====================
    async def handle_create_account(self, event):
        """Handle account creation"""
        user_id = event.sender_id
        
        if user_id == config.ADMIN_USER_ID:
            from datetime import datetime
            account_id = f"admin_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            account_id = self.account_manager.get_user_account_id(user_id)
        
        self.account_manager.create_account(account_id)
        
        await event.edit(
            f"✅ **Account Created: {account_id}**\n\n"
            "Click below to login:",
            buttons=[Button.inline("🔐 Login", f"login:{account_id}")]
        )
    
    async def show_account_menu(self, event, account_id):
        """Show account management menu"""
        account_path = self.account_manager.get_account_path(account_id)
        db = Database(account_path)
        user_data = db.get_user()
        
        if user_data:
            phone = user_data[1]
            stats = db.get_total_stats()
            
            text = (
                f"📱 **Account: {account_id}**\n"
                f"📞 **Phone: {phone}**\n\n"
                f"📊 **Statistics:**\n"
                f"• Total Sent: {stats['total_sent']}\n"
                f"• Groups: {stats['total_groups']}\n"
                f"• Messages: {stats['total_messages']}\n"
                f"• Today: {stats['today_sent']}\n\n"
                "Select an action:"
            )
            
            buttons = [
                [Button.inline("➕ Add Group", f"add_group:{account_id}")],
                [Button.inline("📝 Add Message", f"add_msg:{account_id}")],
                [Button.inline("📋 View Groups", f"view_groups:{account_id}"),
                 Button.inline("📄 View Messages", f"view_msgs:{account_id}")],
                [Button.inline("🚀 Send Now", f"send_now:{account_id}"),
                 Button.inline("⚙️ Settings", f"settings:{account_id}")],
                [Button.inline("📊 Full Stats", f"stats:{account_id}")],
                [Button.inline("🔙 Back", "back_main")]
            ]
        else:
            text = f"📱 **Account: {account_id}**\n\n❌ Not logged in yet"
            buttons = [
                [Button.inline("🔐 Login", f"login:{account_id}")],
                [Button.inline("🔙 Back", "back_main")]
            ]
        
        await event.edit(text, buttons=buttons)
    
    # ==================== Login ====================
    async def start_login(self, event, account_id):
        """Start login process"""
        user_id = event.sender_id
        
        self.user_states[user_id] = {
            'state': 'awaiting_phone',
            'account_id': account_id
        }
        
        await event.edit(
            "🔐 **Login**\n\n"
            "Send your phone number with country code:\n"
            "Example: +1234567890\n\n"
            "Or send /cancel to cancel",
            buttons=[Button.inline("🔙 Back", f"select:{account_id}")]
        )
    
    async def process_phone(self, event, user_id, account_id, phone):
        """Process phone number input"""
        if not re.match(r'^\+\d{10,15}$', phone):
            await event.reply("❌ Invalid phone number. Example: +1234567890")
            return
        
        try:
            account_path = self.account_manager.get_account_path(account_id)
            session_manager = SessionManager(account_path)
            
            success, result = await session_manager.send_code_request(phone)
            
            if success:
                client, code_info = result
                self.user_states[user_id].update({
                    'state': 'awaiting_code',
                    'client': client,
                    'phone': phone,
                    'phone_code_hash': code_info.phone_code_hash
                })
                await event.reply("✅ **Code sent!**\n\nSend the code you received:")
            else:
                await event.reply(f"❌ Error: {result}")
        except Exception as e:
            logger.error(f"Error in process_phone: {e}")
            await event.reply(f"❌ Error: {str(e)}")
    
    async def process_code(self, event, user_id, account_id, code):
        """Process verification code"""
        state_data = self.user_states[user_id]
        client = state_data['client']
        phone = state_data['phone']
        phone_code_hash = state_data['phone_code_hash']
        
        account_path = self.account_manager.get_account_path(account_id)
        session_manager = SessionManager(account_path)
        
        success, message = await session_manager.sign_in_with_code(
            client, phone, code, phone_code_hash
        )
        
        if success:
            # Save to database
            session_file = str(client.session.filename)
            db = Database(account_path)
            db.save_user(phone, session_file)
            
            del self.user_states[user_id]
            
            await event.reply(
                "✅ **Login Successful!**\n\n"
                "You can now:\n"
                "• Add groups\n"
                "• Send messages\n"
                "• Configure settings",
                buttons=[Button.inline("🏠 Main Menu", f"select:{account_id}")]
            )
        elif message == "PASSWORD_REQUIRED":
            self.user_states[user_id]['state'] = 'awaiting_password'
            self.user_states[user_id]['client'] = client
            await event.reply("🔐 **2FA Password Required**\n\nSend your password:")
        else:
            await event.reply(f"❌ {message}")
    
    async def process_password(self, event, user_id, account_id, password):
        """Process 2FA password"""
        state_data = self.user_states[user_id]
        client = state_data['client']
        phone = state_data['phone']
        
        account_path = self.account_manager.get_account_path(account_id)
        session_manager = SessionManager(account_path)
        
        success, message = await session_manager.sign_in_with_password(client, password)
        
        if success:
            session_file = str(client.session.filename)
            db = Database(account_path)
            db.save_user(phone, session_file)
            
            del self.user_states[user_id]
            
            await event.reply("✅ **Login Successful!**")
        else:
            await event.reply(f"❌ {message}")
    
    # ==================== Add Group ====================
    async def start_add_group(self, event, account_id):
        """Start add group process"""
        user_id = event.sender_id
        
        account_path = self.account_manager.get_account_path(account_id)
        db = Database(account_path)
        
        if not db.user_exists():
            await event.answer("❌ Please login first", alert=True)
            return
        
        self.user_states[user_id] = {
            'state': 'awaiting_group',
            'account_id': account_id
        }
        
        await event.edit(
            "📥 **Add Group**\n\n"
            "Send group link:\n"
            "• @username\n"
            "• t.me/username\n"
            "• Invite link\n\n"
            "Or send /cancel to cancel",
            buttons=[Button.inline("🔙 Back", f"select:{account_id}")]
        )
    
    async def process_group(self, event, user_id, account_id, group_link):
        """Process group addition"""
        account_path = self.account_manager.get_account_path(account_id)
        db = Database(account_path)
        session_manager = await self.auto_sender.get_or_create_session(account_id, db)
        
        if not session_manager:
            await event.reply("❌ Session not available. Please login again.")
            del self.user_states[user_id]
            return
        
        success, result = await session_manager.join_group(group_link)
        
        if success:
            group_info = result
            db.add_group(
                group_link,
                group_info['title'],
                group_info['id'],
                group_info['members_count']
            )
            
            await event.reply(
                f"✅ **Group Added**\n\n"
                f"🏷️ **Name:** {group_info['title']}\n"
                f"👥 **Members:** {group_info['members_count']:,}",
                buttons=[Button.inline("🔙 Back", f"select:{account_id}")]
            )
        else:
            await event.reply(f"❌ Error: {result}")
        
        del self.user_states[user_id]
    
    # ==================== Add Message ====================
    async def start_add_message(self, event, account_id):
        """Start add message process"""
        user_id = event.sender_id
        
        account_path = self.account_manager.get_account_path(account_id)
        db = Database(account_path)
        
        if not db.user_exists():
            await event.answer("❌ Please login first", alert=True)
            return
        
        groups = db.get_groups()
        if not groups:
            await event.answer("❌ No groups added yet", alert=True)
            return
        
        min_interval = db.get_setting('min_interval', '60')
        max_interval = db.get_setting('max_interval', '90')
        
        self.user_states[user_id] = {
            'state': 'awaiting_message',
            'account_id': account_id
        }
        
        await event.edit(
            f"📝 **Add Message**\n\n"
            f"⏰ Current interval: {min_interval}-{max_interval} minutes\n"
            f"📊 Target groups: {len(groups)}\n\n"
            "Send your message text:",
            buttons=[Button.inline("🔙 Back", f"select:{account_id}")]
        )
    
    async def process_message(self, event, user_id, account_id, message_text):
        """Process message addition"""
        account_path = self.account_manager.get_account_path(account_id)
        db = Database(account_path)
        
        min_interval = int(db.get_setting('min_interval', '60'))
        max_interval = int(db.get_setting('max_interval', '90'))
        
        if db.add_message(message_text, min_interval, max_interval):
            await event.reply(
                f"✅ **Message Added**\n\n"
                f"⏰ Interval: {min_interval}-{max_interval} minutes\n"
                f"📝 Will be sent automatically",
                buttons=[Button.inline("🔙 Back", f"select:{account_id}")]
            )
        else:
            await event.reply("❌ Error adding message")
        
        del self.user_states[user_id]
    
    # ==================== Send Now ====================
    async def handle_send_now(self, event, account_id):
        """Handle immediate send"""
        await event.edit("🔄 **Sending...**")
        
        result = await self.auto_sender.send_now(account_id)
        
        if result['success']:
            text = (
                f"✅ **Sent Successfully**\n\n"
                f"📤 **Results:**\n"
                f"• ✅ Successful: {result['successful']}\n"
                f"• ❌ Failed: {result['failed']}\n"
                f"• 📝 Messages: {result['messages_count']}\n"
                f"• 👥 Groups: {result['groups_count']}"
            )
        else:
            text = f"❌ **Error:** {result['message']}"
        
        await event.edit(text, buttons=[Button.inline("🔙 Back", f"select:{account_id}")])
    
    # ==================== Settings ====================
    async def show_settings(self, event, account_id):
        """Show settings menu"""
        account_path = self.account_manager.get_account_path(account_id)
        db = Database(account_path)
        settings = db.get_all_settings()
        
        text = "⚙️ **Settings**\n\n"
        for key, value, description in settings:
            text += f"• **{description}:** `{value}`\n"
        
        buttons = [
            [Button.inline("🕒 Change Timing", f"change_time:{account_id}")],
            [Button.inline("🔄 Toggle Auto-Send", f"toggle_auto:{account_id}")],
            [Button.inline("🔙 Back", f"select:{account_id}")]
        ]
        
        await event.edit(text, buttons=buttons)
    
    # ==================== Statistics ====================
    async def show_stats(self, event, account_id):
        """Show full statistics"""
        account_path = self.account_manager.get_account_path(account_id)
        db = Database(account_path)
        stats = db.get_total_stats()
        
        text = (
            f"📊 **Full Statistics - {account_id}**\n\n"
            f"📈 **Total:**\n"
            f"• Messages Sent: {stats['total_sent']}\n"
            f"• Active Groups: {stats['total_groups']}\n"
            f"• Active Messages: {stats['total_messages']}\n\n"
            f"📅 **Today:**\n"
            f"• Sent: {stats['today_sent']}\n"
            f"• Successful: {stats['today_successful']}\n"
            f"• Failed: {stats['today_failed']}"
        )
        
        buttons = [
            [Button.inline("🔄 Refresh", f"stats:{account_id}")],
            [Button.inline("🔙 Back", f"select:{account_id}")]
        ]
        
        await event.edit(text, buttons=buttons)
    
    # ==================== Message Router ====================
    async def handle_message(self, event):
        """Handle text messages"""
        user_id = event.sender_id
        text = event.text
        
        if text == '/cancel':
            if user_id in self.user_states:
                del self.user_states[user_id]
                await event.reply("✅ Cancelled")
            return
        
        if user_id not in self.user_states:
            return
        
        state_data = self.user_states[user_id]
        account_id = state_data['account_id']
        state = state_data['state']
        
        if state == 'awaiting_phone':
            await self.process_phone(event, user_id, account_id, text)
        elif state == 'awaiting_code':
            await self.process_code(event, user_id, account_id, text)
        elif state == 'awaiting_password':
            await self.process_password(event, user_id, account_id, text)
        elif state == 'awaiting_group':
            await self.process_group(event, user_id, account_id, text)
        elif state == 'awaiting_message':
            await self.process_message(event, user_id, account_id, text)
