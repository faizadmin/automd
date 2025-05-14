import discord
from discord.ext import commands, tasks
import asyncio
import re
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

# Dictionary to track kicked users and their end times
active_kicks = {}

def parse_duration(duration_str):
    match = re.match(r"(\d+)(min|hour)", duration_str)
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    if unit == "min":
        return timedelta(minutes=value)
    elif unit == "hour":
        return timedelta(hours=value)
    return None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    monitor_voice_kicks.start()

@bot.command()
async def kick(ctx, duration: str, user_id: int):
    time_delta = parse_duration(duration)
    if not time_delta:
        await ctx.send("Invalid duration! Use like `1min`, `10min`, or `1hour`.")
        return

    guild = ctx.guild
    member = guild.get_member(user_id)
    if not member:
        await ctx.send("User not found in this server.")
        return

    end_time = datetime.utcnow() + time_delta
    active_kicks[user_id] = end_time

    # If already in VC, disconnect immediately
    if member.voice and member.voice.channel:
        try:
            await member.move_to(None)
        except:
            await ctx.send("Failed to disconnect the user. Missing permissions?")
            return

    await ctx.send(f"{member.display_name} will be kicked from VC for {duration}.")

@tasks.loop(seconds=5)
async def monitor_voice_kicks():
    now = datetime.utcnow()
    expired = []

    for user_id, end_time in active_kicks.items():
        if now > end_time:
            expired.append(user_id)
            continue

        for guild in bot.guilds:
            member = guild.get_member(user_id)
            if member and member.voice and member.voice.channel:
                try:
                    await member.move_to(None)
                except:
                    pass  # Ignore errors silently

    for user_id in expired:
        del active_kicks[user_id]

bot.run("YOUR_BOT_TOKEN_HERE")  # 🔁 Yahan apna bot token paste karna
