import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="22", intents=intents)

# Replace with your real IDs
GUILD_ID = 856739130850541618
UPLOAD_CHANNEL_ID = 982222931893583892
MOD_CHANNEL_ID = 1376090022788333670
GIVE_ROLE_ID = 955703181738901534

mod_change_counts = {}  # { "mod#1234": count }
mod_history = {}        # { mod_id: [ {user, old, new, time} ] }
message_map = {}        # { user_id: uploaded_message_id }

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

            mod_name = str(self.mod_user)
            mod_id = self.mod_user.id
            mod_change_counts[mod_name] = mod_change_counts.get(mod_name, 0) + 1
            count = mod_change_counts[mod_name]

            # Log mod change history
            log_entry = {
                "user": self.target_user,
                "old": old_name,
                "new": new_name,
                "time": discord.utils.format_dt(discord.utils.utcnow(), style="R")
            }
            mod_history.setdefault(mod_id, []).append(log_entry)

            # React to original image message with "✅" and send "✅ Done"
            uploaded_msg_id = message_map.get(self.target_user.id)
            if uploaded_msg_id:
                try:
                    uploaded_msg = await interaction.guild.get_channel(UPLOAD_CHANNEL_ID).fetch_message(uploaded_msg_id)
                    await uploaded_msg.add_reaction("🇩")
                    await uploaded_msg.add_reaction("🇴")
                    await uploaded_msg.add_reaction("🇳")
                    await uploaded_msg.add_reaction("🇪")
                    await uploaded_msg.add_reaction("✅")
                except:
                    pass

            await interaction.response.send_message(
                f"\u2705 Name changed by **{self.mod_user.mention}**\nNew name: `{new_name}`", ephemeral=False
            )
            await interaction.channel.send(f"\U0001f9be Total names changed by **{mod_name}**: `{count}`")
        except Exception as e:
            await interaction.response.send_message(f"\u274C Error: {e}", ephemeral=True)

class ChangeNameView(View):
    def __init__(self, target_user):
        super().__init__(timeout=None)
        self.target_user = target_user

    @discord.ui.button(label="Change Name", style=discord.ButtonStyle.primary)
    async def change_name(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_nicknames:
            return await interaction.response.send_message("\ud83d\udeab You don't have permission to change names.", ephemeral=True)
        modal = ChangeNameModal(target_user=self.target_user, message_to_delete=interaction.message, mod_user=interaction.user)
        await interaction.response.send_modal(modal)

@bot.event
async def on_ready():
    print(f"\u2705 Logged in as {bot.user}!")

@bot.event
async def on_message(message):
    if message.channel.id == UPLOAD_CHANNEL_ID and message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                embed = discord.Embed(title="\ud83d\udcc5 New Verification Request", color=discord.Color.blue())
                embed.set_image(url=attachment.url)
                embed.set_footer(text=f"From: {message.author} ({message.author.id})")

                view = ChangeNameView(target_user=message.author)
                sent_msg = await bot.get_channel(MOD_CHANNEL_ID).send(embed=embed, view=view)
                message_map[message.author.id] = message.id

    await bot.process_commands(message)

# \u2705 Command: 22top — show top nickname changers
@bot.command()
async def top(ctx):
    if not mod_change_counts:
        return await ctx.send("\u274C No nickname changes yet.")
    sorted_mods = sorted(mod_change_counts.items(), key=lambda x: x[1], reverse=True)
    text = "**\ud83c\udfc6 Top Name Changers:**\n"
    for idx, (mod, count) in enumerate(sorted_mods, 1):
        text += f"{idx}. **{mod}** — `{count}` names changed\n"
    await ctx.send(text)

# \u2705 Command: 22his @mod — show who that mod has renamed
@bot.command()
async def his(ctx, user: discord.User = None):
    if not user:
        return await ctx.send("\u274C Please mention a moderator or give user ID.")

    mod_id = user.id
    history = mod_history.get(mod_id)

    if not history:
        return await ctx.send(f"\u2139\ufe0f No rename history found for **{user}**.")

    text = f"\ud83d\udcdc Name changes by **{user}**:\n"
    for i, entry in enumerate(history[-5:], 1):  # last 5
        target = entry['user']
        text += f"{i}. `{entry['old']}` → `{entry['new']}` for **{target}** ({entry['time']})\n"
    await ctx.send(text)

# 🔻 Run the bot
TOKEN = os.getenv("TOKEN")  # Environment variable from Render
bot.run(TOKEN)
