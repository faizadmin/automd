import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import os
from pymongo import MongoClient

# INTENTS
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="22", intents=intents)

# DISCORD CONSTANTS
GUILD_ID = 856739130850541618
UPLOAD_CHANNEL_ID = 982222931893583892
MOD_CHANNEL_ID = 1376090022788333670
MOD_ACTIVITY_CHANNEL_ID = 1376231467922755685
GIVE_ROLE_ID = 955703181738901534

# MONGO SETUP
MONGO_URI = "mongodb+srv://faizadmin:Pata%401244@cluster0.v16t0ei.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["discord_bot"]
config_col = db["config"]

# Helper: Load data from DB
def load_data():
    global mod_change_counts, mod_history, message_map
    data = config_col.find_one({"_id": "persistent_data"}) or {}
    mod_change_counts = data.get("mod_change_counts", {})
    mod_history = data.get("mod_history", {})
    message_map = data.get("message_map", {})

# Helper: Save data to DB
def save_data():
    config_col.update_one(
        {"_id": "persistent_data"},
        {
            "$set": {
                "mod_change_counts": mod_change_counts,
                "mod_history": mod_history,
                "message_map": message_map
            }
        },
        upsert=True
    )

# INITIAL LOAD
mod_change_counts = {}
mod_history = {}
message_map = {}
load_data()

# Modal for Nickname Change
class ChangeNameModal(Modal):
    def __init__(self, target_user, message_to_delete, mod_user):
        super().__init__(title="Change Nickname")
        self.target_user = target_user
        self.message_to_delete = message_to_delete
        self.mod_user = mod_user
        self.new_name = TextInput(label="Enter New Nickname")
        self.add_item(self.new_name)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            old_name = self.target_user.display_name
            new_name = self.new_name.value
            await self.target_user.edit(nick=new_name)
            await self.message_to_delete.delete()
            role = interaction.guild.get_role(GIVE_ROLE_ID)
            if role:
                await self.target_user.add_roles(role)

            mod_name = str(self.mod_user)
            mod_id = str(self.mod_user.id)
            mod_change_counts[mod_name] = mod_change_counts.get(mod_name, 0) + 1

            log_entry = {
                "user": str(self.target_user),
                "old": old_name,
                "new": new_name,
                "time": discord.utils.format_dt(discord.utils.utcnow(), style="R")
            }
            mod_history.setdefault(mod_id, []).append(log_entry)
            save_data()

            await interaction.response.send_message(
                f"✅ UserID: `{self.target_user.id}`\n"
                f"Old Name: `{old_name}`\n"
                f"New Name: `{new_name}`\n"
                f"Status: Verified\n"
                f"Verified by: {self.mod_user.mention} (`{self.mod_user.id}`)",
                ephemeral=False
            )

            upload_message_id = message_map.get(str(self.target_user.id))
            if upload_message_id:
                upload_channel = interaction.guild.get_channel(UPLOAD_CHANNEL_ID)
                try:
                    original_msg = await upload_channel.fetch_message(upload_message_id)
                    for ch in ["🇩", "🇴", "🇳", "🇪", "✅"]:
                        await original_msg.add_reaction(ch)
                except Exception:
                    pass

            embed = discord.Embed(
                title="✅ Verification Successful",
                color=discord.Color.green(),
                description=(
                    f"👤 User: {self.target_user.mention}\n"
                    f"🆔 ID: `{self.target_user.id}`\n\n"
                    f"📝 **Old Nickname:** `{old_name}`\n"
                    f"📝 **New Nickname:** `{new_name}`\n"
                    f"👮 Verified by: {self.mod_user.mention} (`{self.mod_user.id}`)\n"
                    f"⏰ Time: {discord.utils.format_dt(discord.utils.utcnow(), style='F')}"
                )
            )
            await interaction.guild.get_channel(MOD_ACTIVITY_CHANNEL_ID).send(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class CancelReasonModal(Modal):
    def __init__(self, target_user, message_to_delete, mod_user):
        super().__init__(title="Cancel Verification Request")
        self.target_user = target_user
        self.message_to_delete = message_to_delete
        self.mod_user = mod_user
        self.reason = TextInput(label="Reason for cancellation", style=discord.TextStyle.paragraph)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"⚠️ Are you sure you want to cancel verification for {self.target_user.mention}?\n"
            f"**Reason:** {self.reason.value}",
            view=CancelConfirmView(
                target_user=self.target_user,
                message_to_delete=self.message_to_delete,
                mod_user=self.mod_user,
                reason=self.reason.value
            ),
            ephemeral=True
        )

class CancelConfirmView(View):
    def __init__(self, target_user, message_to_delete, mod_user, reason):
        super().__init__(timeout=60)
        self.target_user = target_user
        self.message_to_delete = message_to_delete
        self.mod_user = mod_user
        self.reason = reason

    @discord.ui.button(label="✅ Yes, Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_confirm")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await self.message_to_delete.delete()
        await interaction.response.send_message("✅ Cancelled successfully.", ephemeral=True)

        upload_message_id = message_map.get(str(self.target_user.id))
        photo_url = None

        if upload_message_id:
            try:
                upload_channel = interaction.guild.get_channel(UPLOAD_CHANNEL_ID)
                original_msg = await upload_channel.fetch_message(upload_message_id)
                for emoji in ["🇩", "🇪", "🇳", "🇾", "❌"]:
                    await original_msg.add_reaction(emoji)
                if original_msg.attachments:
                    photo_url = original_msg.attachments[0].url
            except Exception:
                pass

        embed = discord.Embed(
            title="❌ Verification Request Cancelled",
            color=discord.Color.red(),
            description=(
                f"👤 User: {self.target_user.mention}\n"
                f"🆔 ID: `{self.target_user.id}`\n\n"
                f"📄 **Reason:** {self.reason}\n"
                f"👮 Cancelled by: {self.mod_user.mention} (`{self.mod_user.id}`)"
            )
        )
        if photo_url:
            embed.set_image(url=photo_url)

        await interaction.guild.get_channel(MOD_ACTIVITY_CHANNEL_ID).send(embed=embed)

    @discord.ui.button(label="❌ No", style=discord.ButtonStyle.secondary, custom_id="cancel_abort")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("❎ Cancel action aborted.", ephemeral=True)

class ChangeNameView(View):
    def __init__(self, target_user):
        super().__init__(timeout=None)
        self.target_user = target_user

    @discord.ui.button(label="Change Name", style=discord.ButtonStyle.primary, custom_id="change_name_btn")
    async def change_name(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_nicknames:
            return await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
        modal = ChangeNameModal(self.target_user, interaction.message, interaction.user)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel_verification_btn")
    async def cancel_verification(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_nicknames:
            return await interaction.response.send_message("🚫 You don't have permission.", ephemeral=True)
        modal = CancelReasonModal(self.target_user, interaction.message, interaction.user)
        await interaction.response.send_modal(modal)

@bot.event
async def on_ready():
    bot.add_view(ChangeNameView(None))
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def ver(ctx):
    await ctx.send("**This software version is 1.3**")

@bot.event
async def on_message(message):
    if message.channel.id == UPLOAD_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                embed = discord.Embed(title="📅 New Verification Request", color=discord.Color.blue())
                embed.set_image(url=attachment.url)
                embed.description = (
                    f"👤 User: {message.author.mention}\n"
                    f"🆔 ID: `{message.author.id}`\n\n"
                    f"Please review the verification request below."
                )
                view = ChangeNameView(message.author)
                mod_channel = bot.get_channel(MOD_CHANNEL_ID)
                if mod_channel:
                    msg = await mod_channel.send(embed=embed, view=view)
                    message_map[str(message.author.id)] = message.id
                    save_data()
    await bot.process_commands(message)

@bot.command()
async def top(ctx):
    if not ctx.author.guild_permissions.manage_nicknames:
        return await ctx.send("🚫 You don't have permission.")
    if not mod_change_counts:
        return await ctx.send("❌ No nickname changes.")
    sorted_mods = sorted(mod_change_counts.items(), key=lambda x: x[1], reverse=True)
    msg = "**🎖 Top Mods:**\n"
    for i, (mod, count) in enumerate(sorted_mods, 1):
        msg += f"{i}. **{mod}** — `{count}` names changed\n"
    await ctx.send(msg)

@bot.command()
async def his(ctx, user: discord.User = None):
    if not ctx.author.guild_permissions.manage_nicknames:
        return await ctx.send("🚫 You don't have permission.")
    if not user:
        return await ctx.send("❌ Please mention a user.")
    history = mod_history.get(str(user.id))
    if not history:
        return await ctx.send(f"ℹ️ No rename history for {user}.")
    text = f"📜 Name changes by **{user}**:\n"
    for i, entry in enumerate(history[-5:], 1):
        text += f"{i}. `{entry['old']}` → `{entry['new']}` for **{entry['user']}** ({entry['time']})\n"
    await ctx.send(text)

# Run your bot
TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
