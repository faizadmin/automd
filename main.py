import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="22", intents=intents)
TOKEN = os.getenv("TOKEN")  # Environment variable from Render

# Replace with your real IDs
GUILD_ID = 856739130850541618
UPLOAD_CHANNEL_ID = 982222931893583892
MOD_CHANNEL_ID = 1376090022788333670
GIVE_ROLE_ID = 955703181738901534

mod_change_counts = {}  # { "mod#1234": count }
user_history = {}       # { user_id: [ {old_name, new_name, by, time} ] }

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

            # Role assign
            role = interaction.guild.get_role(GIVE_ROLE_ID)
            if role:
                await self.target_user.add_roles(role)

            # Log mod count
            mod_name = str(self.mod_user)
            mod_change_counts[mod_name] = mod_change_counts.get(mod_name, 0) + 1
            count = mod_change_counts[mod_name]

            # Log user history
            entry = {
                "old": old_name,
                "new": new_name,
                "by": mod_name,
                "time": discord.utils.format_dt(discord.utils.utcnow(), style="R")
            }
            user_history.setdefault(self.target_user.id, []).append(entry)

            await interaction.response.send_message(
                f"✅ Name changed by **{self.mod_user.mention}**\nNew name: `{new_name}`", ephemeral=False
            )
            await interaction.channel.send(f"🧾 Total names changed by **{mod_name}**: `{count}`")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class ChangeNameView(View):
    def __init__(self, target_user):
        super().__init__(timeout=None)
        self.target_user = target_user

    @discord.ui.button(label="Change Name", style=discord.ButtonStyle.primary)
    async def change_name(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_nicknames:
            return await interaction.response.send_message("🚫 You don't have permission to change names.", ephemeral=True)
        modal = ChangeNameModal(target_user=self.target_user, message_to_delete=interaction.message, mod_user=interaction.user)
        await interaction.response.send_modal(modal)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}!")

@bot.event
async def on_message(message):
    if message.channel.id == UPLOAD_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                embed = discord.Embed(title="📥 New Verification Request", color=discord.Color.blue())
                embed.set_image(url=attachment.url)
                embed.set_footer(text=f"From: {message.author} ({message.author.id})")

                view = ChangeNameView(target_user=message.author)
                await bot.get_channel(MOD_CHANNEL_ID).send(embed=embed, view=view)

    await bot.process_commands(message)

# ✅ Command: 22top — show mods with most nickname changes
@bot.command()
async def top(ctx):
    if not mod_change_counts:
        return await ctx.send("❌ No nickname changes yet.")
    sorted_mods = sorted(mod_change_counts.items(), key=lambda x: x[1], reverse=True)
    text = "**🏆 Top Name Changers:**\n"
    for idx, (mod, count) in enumerate(sorted_mods, 1):
        text += f"{idx}. **{mod}** — `{count}` names changed\n"
    await ctx.send(text)

# ✅ Command: 22his @user or user_id — show nickname history
@bot.command()
async def his(ctx, user: discord.User = None):
    if not user:
        return await ctx.send("❌ Please mention a user or provide user ID.")
    history = user_history.get(user.id)
    if not history:
        return await ctx.send("ℹ️ No nickname change history found for this user.")

    text = f"📜 Nickname change history for **{user}**:\n"
    for i, entry in enumerate(history[-5:], 1):
        text += f"{i}. `{entry['old']}` → `{entry['new']}` by **{entry['by']}** ({entry['time']})\n"
    await ctx.send(text)

# 👇 Use your token setup here

bot.run(TOKEN)
