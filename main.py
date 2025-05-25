import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="22", intents=intents)

# Replace with your actual values
GUILD_ID = 856739130850541618
UPLOAD_CHANNEL_ID = 982222931893583892
MOD_CHANNEL_ID = 1376090022788333670  # old mod channel (used only for new requests)
MOD_ACTIVITY_CHANNEL_ID = 1376231467922755685  # NEW mod activity channel for success/fail messages
GIVE_ROLE_ID = 955703181738901534

mod_change_counts = {}
mod_history = {}
message_map = {}  # user_id : uploaded_message_id

# Modal for Name Change
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
            mod_id = self.mod_user.id
            mod_change_counts[mod_name] = mod_change_counts.get(mod_name, 0) + 1

            log_entry = {
                "user": self.target_user,
                "old": old_name,
                "new": new_name,
                "time": discord.utils.format_dt(discord.utils.utcnow(), style="R")
            }
            mod_history.setdefault(mod_id, []).append(log_entry)

            # Send confirmation message to interaction
            await interaction.response.send_message(
                f"✅ UserID: `{self.target_user.id}`\n"
                f"Old Name: `{old_name}`\n"
                f"New Name: `{new_name}`\n"
                f"Status: Verified\n"
                f"Verified by: {self.mod_user.mention} (`{self.mod_user.id}`)",
                ephemeral=False
            )

            # Add reactions to original upload message
            upload_message_id = message_map.get(self.target_user.id)
            if upload_message_id:
                upload_channel = interaction.guild.get_channel(UPLOAD_CHANNEL_ID)
                if upload_channel.permissions_for(interaction.guild.me).add_reactions:
                    try:
                        original_msg = await upload_channel.fetch_message(upload_message_id)
                        for ch in ["🇩", "🇴", "🇳", "🇪", "✅"]:
                            await original_msg.add_reaction(ch)
                    except Exception as e:
                        print(f"Failed to add reactions: {e}")
                else:
                    print("Bot missing Add Reactions permission in upload channel")

            # Send embed message to MOD_ACTIVITY_CHANNEL_ID (new channel)
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
            mod_activity_channel = interaction.guild.get_channel(MOD_ACTIVITY_CHANNEL_ID)
            if mod_activity_channel:
                await mod_activity_channel.send(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

# Modal to Get Cancellation Reason
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

# View to Confirm Cancellation (UPDATED as requested)
class CancelConfirmView(View):
    def __init__(self, target_user, message_to_delete, mod_user, reason):
        super().__init__(timeout=60)
        self.target_user = target_user
        self.message_to_delete = message_to_delete
        self.mod_user = mod_user
        self.reason = reason

    @discord.ui.button(label="✅ Yes, Cancel", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await self.message_to_delete.delete()
        await interaction.response.send_message("✅ Cancelled successfully.", ephemeral=True)

        upload_message_id = message_map.get(self.target_user.id)
        photo_url = None

        if upload_message_id:
            try:
                upload_channel = interaction.guild.get_channel(UPLOAD_CHANNEL_ID)
                original_msg = await upload_channel.fetch_message(upload_message_id)

                # Add reactions: D E N Y ❌
                deny_reacts = ["🇩", "🇪", "🇳", "🇾", "❌"]


                for emoji in deny_reacts:
                    await original_msg.add_reaction(emoji)

                if original_msg.attachments:
                    photo_url = original_msg.attachments[0].url
            except Exception as e:
                print(f"Failed to react to original message: {e}")

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

        mod_activity_channel = interaction.guild.get_channel(MOD_ACTIVITY_CHANNEL_ID)
        if mod_activity_channel:
            await mod_activity_channel.send(embed=embed)

    @discord.ui.button(label="❌ No", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("❎ Cancel action aborted.", ephemeral=True)

# View with Change Name and Cancel Buttons
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

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_verification(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_nicknames:
            return await interaction.response.send_message("🚫 You don't have permission to cancel.", ephemeral=True)
        modal = CancelReasonModal(target_user=self.target_user, message_to_delete=interaction.message, mod_user=interaction.user)
        await interaction.response.send_modal(modal)

# Event: Bot Ready
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}!")

# Event: On Message with Image Upload
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
                embed.set_footer(text=f"From: {message.author} ({message.author.id})")

                view = ChangeNameView(target_user=message.author)
                sent_msg = await bot.get_channel(MOD_CHANNEL_ID).send(embed=embed, view=view)

                message_map[message.author.id] = message.id
    await bot.process_commands(message)


# Command: 22top
@bot.command()
async def top(ctx):
    if not mod_change_counts:
        return await ctx.send("❌ No nickname changes yet.")
    sorted_mods = sorted(mod_change_counts.items(), key=lambda x: x[1], reverse=True)
    text = "**🎖 Top Name Changers:**\n"
    for idx, (mod, count) in enumerate(sorted_mods, 1):
        text += f"{idx}. **{mod}** — `{count}` names changed\n"
    await ctx.send(text)

# Command: 22his @mod
@bot.command()
async def his(ctx, user: discord.User = None):
    if not user:
        return await ctx.send("❌ Please mention a moderator or provide user ID.")
    mod_id = user.id
    history = mod_history.get(mod_id)
    if not history:
        return await ctx.send(f"ℹ️ No rename history found for **{user}**.")
    text = f"📜 Name changes by **{user}**:\n"
    for i, entry in enumerate(history[-5:], 1):
        target = entry['user']
        text += f"{i}. `{entry['old']}` → `{entry['new']}` for **{target}** ({entry['time']})\n"
    await ctx.send(text)

# Run the bot
TOKEN = os.getenv("TOKEN")
bot.run(TOKEN)
