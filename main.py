import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix=".", intents=intents)

GUILD_ID = 123456789012345678  # 🔁 Replace with your server ID
MOD_CHANNEL_ID = 123456789012345678  # 🔁 Replace with mod channel ID
TICKET_CATEGORY_ID = 123456789012345678  # 🔁 Replace with ticket category ID

# --------------- Views ------------------

class VerifyButton(discord.ui.View):
    @discord.ui.button(label="Click for Verification", style=discord.ButtonStyle.green, custom_id="verify_click")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        category = guild.get_channel(TICKET_CATEGORY_ID)
        ticket_name = f"verify-{user.name}".replace(" ", "-").lower()

        # Prevent duplicate ticket
        for channel in category.text_channels:
            if channel.topic == f"ticket-for-{user.id}":
                await interaction.response.send_message("🔒 You already have a ticket.", ephemeral=True)
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=ticket_name,
            overwrites=overwrites,
            category=category,
            topic=f"ticket-for-{user.id}"
        )

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

        await channel.send(
            f"👋 Hi {user.mention}, please upload your Free Fire profile screenshot below.",
            view=SubmitView(user.id)
        )


class SubmitView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Submit Verification", style=discord.ButtonStyle.primary, custom_id="submit_verification")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ You cannot submit for someone else!", ephemeral=True)
            return

        channel = interaction.channel
        messages = [m async for m in channel.history(limit=20)]
        attachments = [m.attachments[0] for m in messages if m.attachments]

        if not attachments:
            await interaction.response.send_message("⚠️ No screenshot found. Please upload before submitting.", ephemeral=True)
            return

        image = attachments[0]
        mod_channel = interaction.guild.get_channel(MOD_CHANNEL_ID)

        embed = discord.Embed(
            title="📝 New Free Fire Verification Request",
            description=f"From: {interaction.user.mention} (`{interaction.user.id}`)",
            color=discord.Color.green()
        )
        embed.set_image(url=image.url)

        await mod_channel.send(embed=embed, view=NicknameView(interaction.user.id))
        await interaction.response.send_message("✅ Submitted to moderators. Thank you!", ephemeral=True)

        await channel.send("🔒 Closing this ticket in 10 seconds...")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=10))
        await channel.delete()


class NicknameView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Change Nickname", style=discord.ButtonStyle.secondary, custom_id="change_nick")
    async def change_nick(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(self.user_id)
        if not member:
            await interaction.response.send_message("❌ Member not found.", ephemeral=True)
            return

        await interaction.response.send_modal(NickModal(self.user_id))


class NickModal(discord.ui.Modal, title="Change Nickname"):
    nickname = discord.ui.TextInput(label="Enter new nickname", placeholder="e.g., FF•PlayerYT", max_length=32)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(self.user_id)
        if not member:
            await interaction.response.send_message("❌ Member not found.", ephemeral=True)
            return

        try:
            await member.edit(nick=self.nickname.value)
            await interaction.response.send_message(f"✅ Nickname changed to `{self.nickname.value}`", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Failed to change nickname. Missing permissions?", ephemeral=True)

# --------------- Commands ------------------

@bot.tree.command(name="setupverify", description="Send verification button")
async def setupverify(interaction: discord.Interaction):
    await interaction.response.send_message("🛡️ Click the button below to start Free Fire verification:", view=VerifyButton())

# --------------- Events ------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is online as {bot.user}")


# --------------- Start Bot ------------------

bot.run(os.getenv("TOKEN"))  # Load from .env file (or replace with actual token)
