import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="&", intents=intents)
TOKEN = os.getenv("TOKEN")  # Environment variable from Render

# Replace with your real IDs
GUILD_ID = 856739130850541618
UPLOAD_CHANNEL_ID = 982222931893583892
MOD_CHANNEL_ID = 1376090022788333670
GIVE_ROLE_ID = 955703181738901534

# Dictionary to track total name changes per mod
mod_change_counts = {}

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
            await self.target_user.edit(nick=self.new_name.value)
            await self.message_to_delete.delete()

            # Assign role to target user
            role = interaction.guild.get_role(GIVE_ROLE_ID)
            if role:
                await self.target_user.add_roles(role)

            # Count update
            mod_name = str(self.mod_user)
            mod_change_counts[mod_name] = mod_change_counts.get(mod_name, 0) + 1
            count = mod_change_counts[mod_name]

            # Response messages
            await interaction.response.send_message(
                f"✅ Name changed successfully by **{self.mod_user.mention}**\nNew name: `{self.new_name.value}`",
                ephemeral=False
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

bot.run(TOKEN)

