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

OWNER_ID = 1176678272579424258
MOD_CHANNEL_ID = 123456789012345678  # 🔁 Replace with your mod-only channel ID
active_kicks = {}

def parse_duration(duration_str):
    match = re.match(r"(\d+)(min|hour)", duration_str)
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    return timedelta(minutes=value) if unit == "min" else timedelta(hours=value)

def only_owner(ctx):
    if ctx.author.id != OWNER_ID:
        asyncio.create_task(ctx.send("gadhe topa admi yeh sirf faiz bhai use kar sakte hai"))
        return False
    return True

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name}')
    monitor_voice_kicks.start()

# ----------------- VC KICK SYSTEM ----------------- #
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
                    pass

    for user_id in expired:
        del active_kicks[user_id]

# ----------------- FF VERIFICATION SYSTEM ----------------- #
@bot.command(name="setup_verification")
async def setup_verification(ctx):
    view = discord.ui.View()
    view.add_item(VerifyButton())
    await ctx.send("Click below to verify your Free Fire profile:", view=view)

class VerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Click for Verification", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        modal = VerificationModal()
        await interaction.response.send_modal(modal)

class VerificationModal(discord.ui.Modal, title="Free Fire Verification"):
    image_url = discord.ui.TextInput(label="Upload Screenshot (Image URL)", placeholder="https://imgur.com/...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        mod_channel = interaction.client.get_channel(MOD_CHANNEL_ID)
        if not mod_channel:
            await interaction.response.send_message("❌ Mod channel not found!", ephemeral=True)
            return

        embed = discord.Embed(title="📥 New Verification Request", color=discord.Color.orange())
        embed.add_field(name="User", value=interaction.user.mention, inline=False)
        embed.add_field(name="Screenshot", value=self.image_url.value, inline=False)
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        view = discord.ui.View()
        view.add_item(ChangeNameButton(user_id=interaction.user.id))

        await mod_channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Your verification has been submitted!", ephemeral=True)

class ChangeNameButton(discord.ui.Button):
    def __init__(self, user_id: int):
        super().__init__(label="Change Name", style=discord.ButtonStyle.success)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(NicknameModal(user_id=self.user_id))

class NicknameModal(discord.ui.Modal, title="Change User Nickname"):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.new_name = discord.ui.TextInput(label="Enter new nickname", required=True)
        self.add_item(self.new_name)

    async def on_submit(self, interaction: discord.Interaction):
        for guild in bot.guilds:
            member = guild.get_member(self.user_id)
            if member:
                try:
                    await member.edit(nick=self.new_name.value)
                    await interaction.response.send_message(f"✅ Nickname changed to **{self.new_name.value}** for {member.mention}", ephemeral=True)
                    return
                except:
                    await interaction.response.send_message("❌ Failed to change nickname. Missing permissions?", ephemeral=True)
                    return
        await interaction.response.send_message("❌ User not found in any guild.", ephemeral=True)

# Run bot
bot.run(os.environ["TOKEN"])
