import discord
from discord.ext import commands, tasks
from discord import app_commands, ButtonStyle
from discord.ui import View, Button, Modal, TextInput
import asyncio
import re
from datetime import datetime, timedelta
import os

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='.', intents=intents)
OWNER_ID = 1176678272579424258
MOD_LOG_CHANNEL_ID = 982222931893583892  # Replace with actual mod-only channel ID
VERIFY_CATEGORY_ID = 1373585291436232755  # Replace with category ID where ticket channels are made

active_kicks = {}

# Kick Timer System

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

@bot.command()
async def kick(ctx, duration: str, user_id: int):
    if ctx.author.id != OWNER_ID:
        await ctx.send("gadhe topa admi yeh sirf faiz bhai use kar sakte hai")
        return

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

    if member.voice and member.voice.channel:
        try:
            await member.move_to(None)
        except:
            await ctx.send("⚠️ Failed to disconnect the user. Missing permissions?")
            return

    await ctx.send(f"✅ {member.display_name} will be kicked from VC for {duration}.")

@bot.command()
async def unkick(ctx, user_id: int):
    if ctx.author.id != OWNER_ID:
        await ctx.send("gadhe topa admi yeh sirf faiz bhai use kar sakte hai")
        return

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
                    pass
    for user_id in expired:
        del active_kicks[user_id]

# FF Verification System

class SubmitModal(Modal, title="Submit Free Fire Nickname"):
    new_name = TextInput(label="Enter New Nickname")

    def __init__(self, user):
        super().__init__()
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.user.edit(nick=self.new_name.value)
            await interaction.response.send_message(f"✅ Nickname changed to `{self.new_name.value}`", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Failed to change nickname.", ephemeral=True)

class VerificationView(View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

        self.add_item(Button(label="Submit Screenshot", style=ButtonStyle.success, custom_id="submit_ss"))

    @discord.ui.button(label="Submit Screenshot", style=ButtonStyle.primary, custom_id="submit_ss")
    async def submit_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Only the applicant can upload.", ephemeral=True)
            return
        await interaction.response.send_message("📸 Please upload your Free Fire profile screenshot.", ephemeral=True)

class ModView(View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(label="Change Nickname", style=ButtonStyle.success, custom_id="mod_change_nick")
    async def change_nick(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_nicknames:
            await interaction.response.send_message("❌ You don't have permission to do this.", ephemeral=True)
            return
        await interaction.response.send_modal(SubmitModal(self.user))

@bot.command()
async def verifysetup(ctx):
    """Sends the verification button message."""
    view = discord.ui.View()
    
    class VerifyButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Click for Verification", style=discord.ButtonStyle.success)

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_message("🔧 Processing... Please wait.", ephemeral=True)
            # You can call the function to create ticket channel here, or it will be in another handler.

    view.add_item(VerifyButton())

    await ctx.send(
        "**🔐 Click below to verify your Free Fire account**",
        view=view
    )

@bot.event
async def on_message(message):
    try:
        if message.author.bot:
            return

        if isinstance(message.channel, discord.TextChannel):
            if message.channel.name.startswith("verify-") and message.attachments:
                # process uploaded screenshot
                await message.channel.send("Screenshot received. Click the button below to submit.")
                # send button etc.
        
        await bot.process_commands(message)

    except Exception as e:
        print(f"❌ Error in on_message: {e}")


bot.run(os.environ["TOKEN"])
