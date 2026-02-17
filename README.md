# Minecraft Server Bot

A Discord bot for monitoring Minecraft servers.

## Features

- ✅ Check server status and latency
- 👥 View online players
- ⏱️ Track player playtime
- 🔔 Auto-alerts when server goes up/down
- 🎨 Rich embeds with server status
- 🎯 Prefix-based commands (`mc-info:`)

## Setup

1. Clone the repository
2. Create a `.env` file with your bot token and server IP:
   ```
   BOT_TOKEN=your_bot_token_here
   SERVER_IP=your.minecraft.server:25565
   ALERT_CHANNEL_ID=123456789012345678
   PING_USER_ID=123456789012345678
   ```
   - `ALERT_CHANNEL_ID` is optional - the Discord channel ID where auto-alerts will be sent
   - `PING_USER_ID` is optional - the Discord user ID to ping when server status changes
   - To get IDs: Enable Developer Mode in Discord → Right-click channel/user → Copy ID
   
3. Run the setup script:
   ```powershell
   .\setup.ps1
   ```

## Commands

- `mc-info:help` - Show all available commands
- `mc-info:status` - Check Minecraft server status and latency
- `mc-info:players` - Show currently online players
- `mc-info:playtime` - Display player playtime statistics
- `mc-info:autocheck on/off` - Enable or disable automatic server monitoring
- `mc-info:hello` - Get a greeting

## Running the Bot

Simply run:
```powershell
.\run.ps1
```

Or manually:
```powershell
.\.venv\Scripts\python.exe main.py
```

## Discord Developer Portal Setup

Enable these privileged intents for your bot:
1. Go to https://discord.com/developers/applications/
2. Select your bot
3. Go to "Bot" section
4. Enable:
   - Server Members Intent
   - Presence Intent
   - Message Content Intent
5. Save changes

## Dependencies

- discord.py
- python-dotenv
- mcstatus

## Notes

- Playtime tracking starts when the bot is running and players are checked
- Player data is stored in `player_data.json` (auto-created)
- Some servers hide player lists - in that case only player count is shown
- Auto-alerts check the server every 2 minutes and notify when status changes
- If `ALERT_CHANNEL_ID` is set in `.env`, auto-alerts start automatically when the bot starts
- You can toggle auto-alerts on/off with `mc-info:autocheck on/off`
