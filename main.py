import discord
from discord.ext import commands, tasks
import asyncio
import re
from datetime import datetime, timedelta
import os

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

# Only Faiz Bhai can use commands
OWNER_ID = 1176678272579424258

# Dict to track users on kick timer
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
    print(f'✅ Logged in as {bot.user.name}')
    monitor_voice_kicks.start()

def only_owner(ctx):
    if ctx.author.id != OWNER_ID:
        asyncio.create_task(ctx.send("gadhe topa admi yeh sirf faiz bhai use kar sakte hai"))
        return False
    return True

@bot.command()
async def kick(ctx, duration: str, user_id: int):
    if not only_owner(ctx): return

    time_delta = parse_duration(duration)
    if not time_delta:
        await ctx.send("❌ Invalid duration! Use like `1min`, `10min`, or `1hour`.")
        return

    guild = ctx.guild
    member = guild.get_member(user_id)
    if not member:
        await ctx.send("❌ User not found in this server.")
        return

    end_time = datetime.utcnow() + time_delta
    active_kicks[user_id] = end_time

    # If already in VC, disconnect immediately
    if member.voice and member.voice.channel:
        try:
            await member.move_to(None)
        except:
            await ctx.send("⚠️ Failed to disconnect the user. Missing permissions?")
            return

    await ctx.send(f"✅ {member.display_name} will be kicked from VC for {duration}.")

@bot.command()
async def unkick(ctx, user_id: int):
    if not only_owner(ctx): return

    if user_id in active_kicks:
        del active_kicks[user_id]
        await ctx.send(f"🟢 Kick timer removed for user <@{user_id}>.")
    else:
        await ctx.send("❌ User was not under kick timer.")

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
                    pass  # Ignore silently

    for user_id in expired:
        del active_kicks[user_id]

# Use token from Render environment variable
bot.run(os.environ["TOKEN"])
