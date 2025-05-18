import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)
TOKEN = os.getenv("TOKEN")  # Environment variable from Render

GUILD_ID = 856739130850541618         # Replace with your server ID
MOD_CHANNEL_ID = 982222931893583892  # Replace with your mod-only channel ID
CATEGORY_ID = 1373585291436232755        # For ticket channels

change_counts = {}

class NicknameModal(Modal, title="Change Nickname"):
    new_name = TextInput(label="Enter new nickname", required=True)

    def __init__(self, user, ticket_channel, app_message):
        super().__init__()
        self.user = user
        self.ticket_channel = ticket_channel
        self.app_message = app_message

    async def on_submit(self, interaction: discord.Interaction):
        old_name = self.user.display_name
        new_name = self.new_name.value

        try:
            # Change nickname
            await self.user.edit(nick=new_name)

            # Update count
            count = change_counts.get(self.user.id, 0) + 1
            change_counts[self.user.id] = count

            # Delete application message
            try:
                await self.app_message.delete()
            except Exception as e:
                print("Failed to delete application message:", e)

            # Log in mod channel
            mod_channel = interaction.guild.get_channel(MOD_CHANNEL_ID)
            log_embed = discord.Embed(
                title="✅ Nickname Changed",
                color=discord.Color.green(),
                description=(
                    f"**User:** {self.user.mention}\n"
                    f"**New Nickname:** `{new_name}`\n"
                    f"**Total Changes:** `{count}`"
                )
            )
            await mod_channel.send(embed=log_embed)

            # Respond to mod privately
            await interaction.response.send_message(
                f"✅ Nickname changed to `{new_name}` and ticket will be closed.",
                ephemeral=True
            )

            # Delete ticket channel
            await self.ticket_channel.delete()

        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)



class ApplicationView(View):
    def __init__(self, user, image_url, ticket_channel, app_message):
        super().__init__(timeout=None)
        self.user = user
        self.image_url = image_url
        self.ticket_channel = ticket_channel
        self.app_message = app_message

    @discord.ui.button(label="Change Name", style=discord.ButtonStyle.primary)
    async def change_name(self, interaction: discord.Interaction, button: Button):
        if interaction.user.guild_permissions.manage_nicknames:
            modal = NicknameModal(self.user, self.ticket_channel, self.app_message)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)



@bot.event
async def on_ready():
    print(f"Bot ready as {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"Failed to sync: {e}")


@bot.command()
async def setup(ctx):
    if not ctx.guild:
        return

    embed = discord.Embed(
        title="Free Fire Verification",
        description="Click the button below to start verification.",
        color=discord.Color.blue()
    )

    class SetupView(View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="Click for Verification", style=discord.ButtonStyle.success)
        async def verify_button(self, interaction: discord.Interaction, button: Button):
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            category = ctx.guild.get_channel(CATEGORY_ID)
            ticket_channel = await ctx.guild.create_text_channel(
                name=f"verify-{interaction.user.name}",
                overwrites=overwrites,
                category=category
            )
            await interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)
            await ticket_channel.send(
                f"{interaction.user.mention}, please upload your Free Fire profile screenshot for verification."
            )

    await ctx.send(embed=embed, view=SetupView())



@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name.startswith("verify-") and message.attachments:
        user = message.author
        image = message.attachments[0]

        mod_channel = bot.get_channel(MOD_CHANNEL_ID)
        embed = discord.Embed(title="New Verification Request", color=discord.Color.green())
        embed.set_author(name=f"{user.name}#{user.discriminator}", icon_url=user.avatar.url if user.avatar else None)
        embed.set_image(url=image.url)
        embed.set_footer(text=f"User ID: {user.id}")

      view = ApplicationView(user, image.url, message.channel, None)
app_msg = await mod_channel.send(embed=embed, view=view)
view.app_message = app_msg


    await bot.process_commands(message)

bot.run(TOKEN)
