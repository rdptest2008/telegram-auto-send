# Telegram Auto-Sender Bot

A professional Telegram bot that automatically sends messages to multiple groups on a scheduled basis.

## Features

✅ **Multi-Account Support** - Manage multiple Telegram accounts  
✅ **Auto-Send** - Automatically send messages at scheduled intervals  
✅ **Group Management** - Add/remove groups easily  
✅ **Message Scheduling** - Configure custom send intervals  
✅ **Statistics** - Track sent messages and success rates  
✅ **Admin Panel** - Full control for administrators  
✅ **User Accounts** - Each user gets their own isolated account  
✅ **Clean Architecture** - Modular code for easy maintenance  

## Project Structure

```
telegram-bot/
├── config.py              # Configuration settings
├── database.py            # Database management
├── account_manager.py     # Account management
├── session_manager.py     # Telegram session handling
├── auto_sender.py         # Automatic message sender
├── handlers.py            # Bot command handlers
├── main.py               # Main entry point
├── requirements.txt       # Python dependencies
├── accounts/             # Account data (auto-created)
│   └── user_12345/
│       ├── bot.db        # Account database
│       └── sessions/     # Telegram sessions
└── logs/                 # Log files (auto-created)
    └── bot.log
```

## Installation

### 1. Clone or Download

Download all the files to a directory.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Settings

Edit `config.py` and set your credentials:

```python
API_ID = 'YOUR_API_ID'
API_HASH = 'YOUR_API_HASH'
BOT_TOKEN = 'YOUR_BOT_TOKEN'
ADMIN_USER_ID = YOUR_TELEGRAM_USER_ID
```

**Getting Credentials:**
- Get API_ID and API_HASH from: https://my.telegram.org/apps
- Create a bot and get BOT_TOKEN from: @BotFather
- Get your USER_ID from: @userinfobot

### 4. Run the Bot

```bash
python main.py
```

## Usage

### For Users

1. **Start the bot**: Send `/start` to your bot
2. **Create account**: Click "Create Account"
3. **Login**: Enter your phone number and verification code
4. **Add groups**: Add Telegram groups where you want to send messages
5. **Add messages**: Add messages to send automatically
6. **Configure**: Set send intervals in Settings

### For Admins

Admins can:
- Create multiple accounts
- Manage all user accounts
- View all statistics
- Override any settings

### Commands

- `/start` - Start the bot / Show main menu
- `/cancel` - Cancel current operation

### Auto-Send

Messages are automatically sent based on:
- **Min Interval**: Minimum time between sends (default: 60 minutes)
- **Max Interval**: Maximum time between sends (default: 90 minutes)
- **Delay**: Time between sending to each group (default: 2 seconds)

The bot randomly selects a time between min and max intervals for each message.

## Key Features Explained

### 1. Account Isolation

Each user gets their own:
- Database
- Telegram session
- Groups and messages
- Statistics

### 2. Automatic Sending

The auto-sender:
- Runs every 60 seconds
- Checks for pending messages
- Sends to all active groups
- Updates statistics
- Schedules next send

### 3. Error Handling

- Handles Telegram flood limits
- Reconnects on session loss
- Logs all errors
- Continues operation on failures

### 4. Security

- User accounts are isolated
- Session files are secure
- Admin-only features protected
- No password storage

## Troubleshooting

### Bot doesn't start
- Check your credentials in `config.py`
- Ensure bot token is valid
- Check internet connection

### Can't login to Telegram
- Verify phone number format (+1234567890)
- Check if you received the code
- Try again with correct code

### Messages not sending
- Check if auto-send is enabled in Settings
- Verify groups are active
- Check if Telegram session is valid
- Review logs in `logs/bot.log`

### Flood wait errors
- Increase delay between groups
- Increase time intervals
- Telegram has rate limits

## Database Schema

### Tables:
- **user_account**: Stores logged-in user data
- **groups**: Stores added groups
- **messages**: Stores messages to send
- **statistics**: Tracks send statistics
- **settings**: Stores configuration

## Logs

All activity is logged to:
- Console (stdout)
- File: `logs/bot.log`

Log levels:
- INFO: Normal operations
- WARNING: Potential issues
- ERROR: Errors that don't stop operation
- CRITICAL: Fatal errors

## Customization

### Change send intervals

Edit in Settings or directly in `config.py`:
```python
DEFAULT_MIN_INTERVAL = 60  # minutes
DEFAULT_MAX_INTERVAL = 90  # minutes
```

### Change delay between groups

Edit in `config.py`:
```python
MESSAGE_DELAY_BETWEEN_GROUPS = 2  # seconds
```

### Change check frequency

Edit in `config.py`:
```python
AUTO_SEND_CHECK_INTERVAL = 60  # seconds
```

## Advanced Features

### Multiple Messages

You can add multiple messages. Each will be sent according to its schedule.

### Group Management

- Enable/disable groups without deleting
- Track last message sent
- View member counts

### Statistics

Track:
- Total messages sent
- Success/failure rates
- Daily statistics
- Per-account statistics

## Safety Tips

1. **Don't spam**: Respect Telegram's limits
2. **Use delays**: Avoid flood bans
3. **Test first**: Start with one group
4. **Monitor logs**: Watch for errors
5. **Backup data**: Save your `accounts/` folder

## Limitations

- Telegram API rate limits apply
- Maximum 20 groups recommended per account
- Flood wait can delay sending
- Requires stable internet connection

## Support

For issues or questions:
1. Check the logs: `logs/bot.log`
2. Review this README
3. Check Telegram API documentation

## License

Free to use and modify.

## Disclaimer

Use responsibly. Don't spam or violate Telegram's Terms of Service.
