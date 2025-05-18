import os
import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)
TOKEN = os.getenv("TOKEN")  # Environment variable from Render

# Replace with your actual IDs
GUILD_ID = 856739130850541618
MOD_CHANNEL_ID = 982222931893583892
CATEGORY_ID = 1373585291436232755

change_counts = {}

# Modal to change nickname
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
            await self.user.edit(nick=new_name)

            # Update and store count
            count = change_counts.get(self.user.id, 0) + 1
            change_counts[self.user.id] = count

            # Delete only application message
            try:
                await self.app_message.delete()
            except Exception as e:
                print("Error deleting app message:", e)

            # Log in mod channel
            mod_channel = interaction.guild.get_channel(MOD_CHANNEL_ID)
            embed = discord.Embed(
                title="✅ Nickname Changed",
                color=discord.Color.green(),
                description=(
                    f"**User:** {self.user.mention}\n"
                    f"**New Nickname:** `{new_name}`\n"
                    f"**Total Changes:** `{count}`"
                )
            )
            await mod_channel.send(embed=embed)

            # Notify and delete ticket channel
            await interaction.response.send_message(
                f"✅ Nickname changed to `{new_name}`. Closing ticket...",
                ephemeral=True
            )
            await self.ticket_channel.delete()

        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)


# Button view shown on mod panel with "Change Name"
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


# Button shown to users for starting verification
class VerificationButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Click for Verification", style=discord.ButtonStyle.success)
    async def verify(self, interaction: discord.Interaction, button: Button):
        guild = bot.get_guild(GUILD_ID)
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True)
        }

        channel = await guild.create_text_channel(
            name=f"verify-{interaction.user.name}",
            overwrites=overwrites,
            category=category
        )

       await channel.send(f"{interaction.user.mention}, please upload your Free Fire profile screenshot.")

# Let the user know the ticket was created
await interaction.response.send_message(
    f"✅ Ticket created: {channel.mention}. Please upload your Free Fire profile screenshot there.",
    ephemeral=True
)



# Command to send setup panel with button
@bot.command()
async def setup(ctx):
    embed = discord.Embed(
        title="Verification",
        description="Click the button below to start Free Fire verification.",
        color=discord.Color.blurple()
    )
    view = VerificationButton()
    await ctx.send(embed=embed, view=view)


# Detect image upload inside ticket channel
@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author.bot or not message.guild:
        return

    if message.channel.category and message.channel.category.id == CATEGORY_ID:
        if message.attachments:
            image = message.attachments[0]
            if image.content_type and image.content_type.startswith("image"):
                user = message.author

                embed = discord.Embed(
                    title="New Verification Application",
                    color=discord.Color.blue(),
                    description=f"**User:** {user.mention}\nUploaded a Free Fire profile."
                )
                embed.set_image(url=image.url)

                mod_channel = bot.get_channel(MOD_CHANNEL_ID)
                view = ApplicationView(user, image.url, message.channel, None)
                app_msg = await mod_channel.send(embed=embed, view=view)
                view.app_message = app_msg


# Start bot using TOKEN from environment
bot.run(TOKEN)
