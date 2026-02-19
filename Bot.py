import discord
from discord.ext import commands, tasks
from datetime import datetime
from services.minecraft import MinecraftService
from config import *

from services.player_tracker import PlayerTracker  # your new tracker class

class DiscordBot:
    def __init__(self):
        intents = discord.Intents.all()

        self.bot = commands.Bot(
            command_prefix="mc-info:",
            intents=intents,
            help_command=None
        )

        # Services
        self.minecraft = MinecraftService(SERVER_IP)
        self.tracker = PlayerTracker("player_data.json")

        # Monitoring
        self.last_server_status = None
        self.last_online_players = set()
        self.server_down_gif = "https://media.giphy.com/media/bC8EUWeuy5OIx6o7ul/giphy.gif"
        self.server_up_gif = "https://media.giphy.com/media/3o7abGQa0aRJUurpII/giphy.gif"

        # Register events & commands
        self._register_events()
        self._register_commands()

    # ---------------- EVENTS ---------------- #
    def _register_events(self):
        @self.bot.event
        async def on_ready():
            print(f"Logged in as {self.bot.user}")
            print(f"Bot is in {len(self.bot.guilds)} servers")
            if not self.monitor_task.is_running():
                self.monitor_task.start()

    # ---------------- COMMANDS ---------------- #
    def _register_commands(self):
        @self.bot.command()
        async def hello(ctx):
            await ctx.send("Hey dirtbag")

        @self.bot.command()
        async def help(ctx):
            help_message = (
                "**Available Commands:**\n"
                "`mc-info:hello` - Get a greeting\n"
                "`mc-info:status` - Check Minecraft server status\n"
                "`mc-info:players` - Show current players\n"
                "`mc-info:playtime` - Show players' playtime\n"
                "`mc-info:autocheck on/off` - Enable/disable auto-alert"
            )
            await ctx.send(help_message)

        @self.bot.command()
        async def status(ctx):
            msg = await ctx.send("Checking server status...")
            status = await self.safe_minecraft_call(ctx, self.minecraft.get_status, message=msg)
            if not status:
                return  # safe_minecraft_call already handled errors

            latency = round(status.latency)
            motd = status.description
            if isinstance(motd, dict):
                motd = motd.get("text", "Unknown")
            online = status.players.online
            max_players = status.players.max

            embed = discord.Embed(
                title="✅ Server Online",
                description=f"Responded in {latency}ms",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="📜 MOTD", value=motd, inline=False)
            embed.add_field(name="👥 Players", value=f"{online}/{max_players}", inline=True)
            await msg.edit(content=None, embed=embed)

        @self.bot.command()
        async def players(ctx):
            msg = await ctx.send("Fetching players...")
            status = await self.safe_minecraft_call(ctx, self.minecraft.get_status, message=msg)
            if not status:
                return

            self.tracker.update(status)
            online = status.players.online
            max_players = status.players.max

            embed = discord.Embed(
                title="🎮 Players Online",
                description=f"{online}/{max_players} players",
                color=discord.Color.green()
            )

            if status.players.sample:
                embed.add_field(
                    name="Currently Playing",
                    value="\n".join(f"• {p.name}" for p in status.players.sample),
                    inline=False
                )
            else:
                embed.add_field(name="Status", value="No visible players")

            await msg.edit(content=None, embed=embed)

        @self.bot.command()
        async def playtime(ctx):
            top = self.tracker.top_players()
            if not top:
                await ctx.send("No playtime data yet.")
                return

            embed = discord.Embed(
                title="⏱ Player Playtime",
                color=discord.Color.blue()
            )

            lines = []
            for name, data in top:
                total = data.get("total_time", 0)
                hours = total // 3600
                minutes = (total % 3600) // 60

                # Show current session if present
                current_session = data.get("current_session", None)
                if current_session:
                    c_hours = current_session // 3600
                    c_minutes = (current_session % 3600) // 60
                    session_str = f" (Current: {c_hours}h {c_minutes}m)"
                else:
                    session_str = ""

                lines.append(f"• **{name}**: {hours}h {minutes}m{session_str}")

            embed.add_field(name="Top Players", value="\n".join(lines), inline=False)
            await ctx.send(embed=embed)

    # ---------------- MONITOR ---------------- #
    @tasks.loop(minutes=10)
    async def monitor_task(self):
        if not ALERT_CHANNEL_ID:
            return

        channel = self.bot.get_channel(int(ALERT_CHANNEL_ID))
        if not channel:
            return

        try:
            status = self.minecraft.get_status()
            server_is_up = True

            # Collect current players
            current_players = set()
            if status.players.sample:
                current_players = {p.name for p in status.players.sample}

        except Exception:
            server_is_up = False
            current_players = set()

        # ---------------- SERVER STATUS ALERT ---------------- #
        if self.last_server_status is not None and self.last_server_status != server_is_up:
            if server_is_up:
                embed = discord.Embed(
                    title="Server Back Online!",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.set_image(url=self.server_up_gif)
                await channel.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Server Went Offline",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                embed.set_image(url=self.server_down_gif)
                ping_msg = f"<@{PING_USER_ID}>" if PING_USER_ID else ""
                await channel.send(ping_msg, embed=embed)

        # ---------------- NEW PLAYER ALERT ---------------- #
        if server_is_up:
            new_players = current_players - self.last_online_players

            if new_players:
                embed = discord.Embed(
                    title="🎉 Player Joined!",
                    description="\n".join(f"• {name}" for name in new_players),
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                await channel.send(embed=embed)

            # Update tracker for playtime
            self.tracker.update(status)

            # Save current set for next comparison
            self.last_online_players = current_players

        else:
            # If server is down, reset player list
            self.last_online_players = set()

        self.last_server_status = server_is_up

    # ---------------- HELPERS ---------------- #
    async def _server_down(self, message):
        embed = discord.Embed(
            title="Server Not Responding",
            color=discord.Color.red()
        )
        embed.set_image(url=self.server_down_gif)
        await message.edit(content=None, embed=embed)

    async def safe_minecraft_call(self, ctx, func, *args, message=None, **kwargs):
        """
        Calls a MinecraftService method safely.
        
        Parameters:
        - ctx: the command context
        - func: function to call
        - message: optional discord.Message to edit on failure
        - args/kwargs: passed to func
        """
        try:
            return func(*args, **kwargs)
        except TimeoutError:
            if message:
                await self._server_down(message)
            else:
                # fallback if no message to edit
                await ctx.send("❌ Server not responding.")
            return None
        except Exception as e:
            # catch-all for unexpected errors
            await ctx.send(f"❌ An error occurred: {e}")
            return None


    # ---------------- RUN ---------------- #
    def run(self):
        self.bot.run(BOT_TOKEN)
