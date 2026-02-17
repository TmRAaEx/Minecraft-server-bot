import discord
from discord.ext import tasks
from os import getenv
from dotenv import load_dotenv
from mcstatus import JavaServer
import json
from datetime import datetime
import os

class DiscordBot:
    def __init__(self):
        load_dotenv()
        self.token = getenv("BOT_TOKEN")
        self.server_ip = getenv("SERVER_IP")
        self.alert_channel_id = getenv("ALERT_CHANNEL_ID")  # Optional: channel to send alerts
        self.ping_user_id = getenv("PING_USER_ID")  # Optional: user ID to ping on alerts
        intents = discord.Intents.all()
        self.client = discord.Client(intents=intents)
        # Use a direct GIF URL (this one works with Discord embeds)
        self.server_down_gif = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExMzkwbnJobDF6MnE5M2F6ZzdxNTN5dXl3Znh5dzN2b2c0czI1c3dwYyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/bC8EUWeuy5OIx6o7ul/giphy.gif"
        self.server_up_gif = "https://media.giphy.com/media/3o7abGQa0aRJUurpII/giphy.gif"
        # Initialize mcstatus
        self.mc_server = JavaServer.lookup(self.server_ip)
        # Player tracking file
        self.player_data_file = "player_data.json"
        self.player_data = self._load_player_data()
        # Server status tracking
        self.last_server_status = None  # None = unknown, True = up, False = down
        self.auto_check_enabled = False
        
        # Register event handlers
        self.client.event(self.on_ready)
        self.client.event(self.on_message)
        
        # Setup background task
        self.check_server_task = tasks.loop(minutes=10)(self._check_server_status)

    async def on_ready(self):
        server_count = 0
        
        for server in self.client.guilds:
            print(f"-{server.id} (name: {server.name})")
            server_count += 1
        
        print(f"Bot is in {server_count} servers")
        
        # Start auto-checking if alert channel is configured
        if self.alert_channel_id and not self.check_server_task.is_running():
            self.check_server_task.start()
            print(f"Auto-check started for alerts in channel {self.alert_channel_id}")
    
    async def on_message(self, message: discord.Message):
        # Don't respond to own messages
        if message.author == self.client.user:
            return
        
        # Check for prefix
        prefix = "mc-info:"
        if not message.content.lower().startswith(prefix):
            return
        
        # Extract command after prefix
        command = message.content[len(prefix):].strip().lower()
        channel = message.channel
        
        if command == "help":
            help_message = (
                "**Available Commands:**\n"
                "`mc-info:hello` - Get a greeting\n"
                "`mc-info:status` - Check Minecraft server status\n"
                "`mc-info:players` - Show current players online\n"
                "`mc-info:playtime` - Show player playtime stats\n"
                "`mc-info:autocheck on/off` - Enable/disable auto-alerts (requires ALERT_CHANNEL_ID in .env)\n"
                "`mc-info:help` - Show this message"
            )
            await channel.send(help_message)
        
        elif command == "hello":
            await channel.send("Hey dirtbag")
        
        elif command == "status":
            await self.__server_status(channel)   

        elif command == "players":
            await self.__show_players(channel)
            
        elif command == "playtime":
            await self.__show_playtime(channel)
            
        elif command.startswith("autocheck"):
            args = command.split()
            if len(args) > 1:
                if args[1] == "on":
                    await self.__enable_autocheck(channel)
                elif args[1] == "off":
                    await self.__disable_autocheck(channel)
            else:
                status = "enabled" if self.check_server_task.is_running() else "disabled"
                await channel.send(f"Auto-check is currently **{status}**")         
        
    async def __server_status(self, channel):
        status_msg = await channel.send("Checking server status...")
        try:
            status = self.mc_server.status()
            await status_msg.edit(content=f"Server status ok: \nserver responded in {status.latency}ms")
        except TimeoutError:
            await self.__server_down__(status_msg)

    async def __show_players(self, channel):
        player_msg = await channel.send("Checking online players...")
        try:
            status = self.mc_server.status()
            player_count = status.players.online
            max_players = status.players.max
            
            # Update player tracking
            self._update_player_tracking(status)
            
            embed = discord.Embed(
                title="🎮 Players Online",
                description=f"**{player_count}/{max_players}** players online",
                color=discord.Color.green()
            )
            
            if status.players.sample:
                player_list = "\n".join([f"• {player.name}" for player in status.players.sample])
                embed.add_field(name="Currently Playing:", value=player_list, inline=False)
            elif player_count > 0:
                embed.add_field(name="Note:", value="Player list hidden by server settings", inline=False)
            else:
                embed.add_field(name="Status:", value="No players online", inline=False)
            
            await player_msg.edit(content=None, embed=embed)
        except TimeoutError: 
            await self.__server_down__(player_msg)
    
    async def __show_playtime(self, channel):
        playtime_msg = await channel.send("Fetching playtime data...")
        
        if not self.player_data:
            await playtime_msg.edit(content="No playtime data available yet. The bot tracks players as it sees them online.")
            return
        
        embed = discord.Embed(
            title="⏱️ Player Playtime Stats",
            description="Tracked time players have been online",
            color=discord.Color.blue()
        )
        
        # Sort by total time
        sorted_players = sorted(
            self.player_data.items(),
            key=lambda x: x[1].get("total_time", 0),
            reverse=True
        )[:10]  # Top 10 players
        
        if sorted_players:
            playtime_list = []
            for player_name, data in sorted_players:
                total_seconds = data.get("total_time", 0)
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                
                if hours > 0:
                    time_str = f"{hours}h {minutes}m"
                else:
                    time_str = f"{minutes}m"
                
                playtime_list.append(f"• **{player_name}**: {time_str}")
            
            embed.add_field(name="Top Players:", value="\n".join(playtime_list), inline=False)
        else:
            embed.add_field(name="Status:", value="No playtime data available", inline=False)
        
        await playtime_msg.edit(content=None, embed=embed)
    
    def _load_player_data(self):
        """Load player tracking data from file"""
        if os.path.exists(self.player_data_file):
            with open(self.player_data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_player_data(self):
        """Save player tracking data to file"""
        with open(self.player_data_file, 'w') as f:
            json.dump(self.player_data, f, indent=2)
    
    def _update_player_tracking(self, status):
        """Update player session times"""
        current_time = datetime.now().timestamp()
        current_players = set()
        
        if status.players.sample:
            current_players = {player.name for player in status.players.sample}
        
        # Update currently online players
        for player_name in current_players:
            if player_name not in self.player_data:
                self.player_data[player_name] = {
                    "total_time": 0,
                    "session_start": current_time,
                    "last_seen": current_time
                }
            else:
                # If they were offline, start new session
                if "session_start" not in self.player_data[player_name]:
                    self.player_data[player_name]["session_start"] = current_time
                else:
                    # Add time since last check
                    last_seen = self.player_data[player_name].get("last_seen", current_time)
                    time_diff = current_time - last_seen
                    # Only add time if check was recent (within 5 minutes)
                    if time_diff < 300:
                        self.player_data[player_name]["total_time"] += time_diff
                
                self.player_data[player_name]["last_seen"] = current_time
        
        # Mark offline players
        for player_name in self.player_data:
            if player_name not in current_players and "session_start" in self.player_data[player_name]:
                # End session
                del self.player_data[player_name]["session_start"]
        
        self._save_player_data()
    
    async def _check_server_status(self):
        """Background task to check server status and send alerts"""
        if not self.alert_channel_id:
            return
        
        try:
            channel = self.client.get_channel(int(self.alert_channel_id))
            if not channel:
                print(f"Alert channel {self.alert_channel_id} not found")
                return
            
            try:
                # Try to ping the server
                latency = self.mc_server.ping()
                server_is_up = True
            except (TimeoutError, Exception):
                server_is_up = False
            
            # Check if status changed
            if self.last_server_status is not None and self.last_server_status != server_is_up:
                if server_is_up:
                    # Server came back online
                    embed = discord.Embed(
                        title="✅ Server is Back Online!",
                        description=f"The Minecraft server at  is now online.",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    embed.set_image(url=self.server_up_gif)
                    
                    await channel.send("", embed=embed)
                else:
                    # Server went down
                    embed = discord.Embed(
                        title="❌ Server Went Offline",
                        description=f"The Minecraft server  is no longer responding.",
                        color=discord.Color.red(),
                        timestamp=datetime.now()
                    )
                    embed.set_image(url=self.server_down_gif)
                    ping_msg = f"<@{self.ping_user_id}>" if self.ping_user_id else ""
                    await channel.send(ping_msg, embed=embed)
            
            self.last_server_status = server_is_up
            
        except Exception as e:
            print(f"Error in auto-check: {e}")
    
    async def __enable_autocheck(self, channel):
        """Enable auto-checking"""
        if not self.alert_channel_id:
            await channel.send("⚠️ Auto-check requires `ALERT_CHANNEL_ID` to be set in your `.env` file.")
            return
        
        if not self.check_server_task.is_running():
            self.check_server_task.start()
            await channel.send(f"✅ Auto-check enabled! Alerts will be sent to <#{self.alert_channel_id}>")
        else:
            await channel.send("Auto-check is already running.")
    
    async def __disable_autocheck(self, channel):
        """Disable auto-checking"""
        if self.check_server_task.is_running():
            self.check_server_task.cancel()
            await channel.send("❌ Auto-check disabled.")
        else:
            await channel.send("Auto-check is not running.")

    async def __server_down__(self, og_message):
        embed = discord.Embed(
                title="MC Server Not Responding",
                description="The server is currently offline or unreachable.",
                color=discord.Color.red()
            )
        embed.set_image(url=self.server_down_gif)
        await og_message.edit(content=None, embed=embed)


    def run(self):
        self.client.run(self.token)