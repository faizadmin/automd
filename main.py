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

verified_users = {}

class NicknameModal(Modal, title="Change Nickname"):
    new_name = TextInput(label="Enter new nickname", required=True)

    def __init__(self, user, ticket_channel):
        super().__init__()
        self.user = user
        self.ticket_channel = ticket_channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.user.edit(nick=self.new_name.value)
            await interaction.response.send_message(f"Nickname changed to: **{self.new_name.value}**", ephemeral=True)
            await self.ticket_channel.delete()
        except Exception as e:
            await interaction.response.send_message(f"Failed to change nickname: {e}", ephemeral=True)


class ApplicationView(View):
    def __init__(self, user, image_url, ticket_channel):
        super().__init__(timeout=None)
        self.user = user
        self.image_url = image_url
        self.ticket_channel = ticket_channel

    @discord.ui.button(label="Change Name", style=discord.ButtonStyle.primary)
    async def change_name(self, interaction: discord.Interaction, button: Button):
        if interaction.user.guild_permissions.manage_nicknames:
            modal = NicknameModal(self.user, self.ticket_channel)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("You don't have permission.", ephemeral=True)


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
    view = View()
    
    @discord.ui.button(label="Click for Verification", style=discord.ButtonStyle.success)
    async def verify_button(interaction: discord.Interaction, button: Button):
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

    view.add_item(verify_button)
    await ctx.send(embed=embed, view=view)


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

        view = ApplicationView(user, image.url, message.channel)
        await mod_channel.send(embed=embed, view=view)
        await message.channel.send("Your application has been submitted. Please wait for review.")

    await bot.process_commands(message)

bot.run(TOKEN)
