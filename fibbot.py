import os
from datetime import datetime

import aiohttp
import discord
from discord import app_commands
from discord import guild
from discord.ext import commands
from discord.flags import Intents

from discord.message import Attachment

from dotenv import load_dotenv
from pathlib import Path


dotenv_path = Path('.env')
load_dotenv(dotenv_path=dotenv_path)

token = os.getenv('TOKEN')

# Ensure that the folder "Images" exists
if not os.path.exists("Images"):
    os.makedirs("Images")

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)


@bot.tree.command(name="setup", description="Erstellt die katergorien Akten und Berichte und deren channel Archiv")
async def setup(ctx):
    guild = ctx.guild  # Get the guild (server)

    # Check if the "Akten" category already exists
    akten = discord.utils.get(guild.categories, name="Akten")
    if akten is None:
        akten = await guild.create_category_channel("Akten")

    # Check if the "Berichte" category already exists
    berichte = discord.utils.get(guild.categories, name="Berichte")
    if berichte is None:
        berichte = await guild.create_category_channel("Berichte")

    # Check if the "Archiv" channel under "Akten" exists
    akten_archiv = discord.utils.get(guild.text_channels, name="Archiv", category=akten)
    if akten_archiv is None:
        akten_archiv = await guild.create_text_channel("Archiv", category=akten)

    # Check if the "Archiv" channel under "Berichte" exists
    berichte_archiv = discord.utils.get(guild.text_channels, name="Archiv", category=berichte)
    if berichte_archiv is None:
        berichte_archiv = await guild.create_text_channel("Archiv", category=berichte)

    await ctx.response.send_message(
        f"Category '{akten.name}' and '{berichte.name}' with their channels have been created or already exist.")


@bot.tree.command(name="akte", description="erstellt einen neuen channel mit dem namen der Akte")
@app_commands.describe(akten_name="waehle einen akten namen")
async def akte(ctx, akten_name: str):
    # Get the category of the channel where the command was sent
    category = ctx.channel.category
    channel = ctx.channel

    # Check if the command is being used in "Archiv" channel of "Akten" or "Berichte" category
    valid_categories = ["Akten", "Berichte"]
    if category is None or category.name not in valid_categories or channel.name != "archiv":
        await ctx.response.send_message(
            "This command can only be used in the 'Archiv' channel under 'Akten' or 'Berichte' categories.")
        return

    # Replace spaces with hyphens for a valid channel name (if needed)
    formatted_akten_name = akten_name.replace(" ", "-").lower()

    # Check if the channel with the formatted name under the category exists
    akte = discord.utils.get(ctx.guild.text_channels, name=formatted_akten_name, category=category)

    if akte is None:
        # If no channel exists, create a new one with the formatted name
        akte = await ctx.guild.create_text_channel(formatted_akten_name, category=category)
        embed = discord.Embed(title=f"{ctx.user.display_name} [+] {akten_name}", color=discord.Color.green())
        await ctx.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title=f"Akte {akten_name} existiert", color=discord.Color.red())
        await ctx.response.send_message(embed=embed)


@bot.tree.command(name="suche", description="sucht nach einer Akte")
@app_commands.describe(search_string="Suche nach dieser akte")
async def suche(ctx, search_string: str):
    # Get the category of the channel where the command was sent
    category = ctx.channel.category
    channel = ctx.channel

    # Check if the command is being used in "Archiv" channel of "Akten" or "Berichte" category
    valid_categories = ["Akten", "Berichte"]
    if category is None or category.name not in valid_categories or channel.name != "archiv":
        await ctx.response.send_message(
            "This command can only be used in the 'Archiv' channel under 'Akten' or 'Berichte' categories.")
        return

    # Find channels in the same category that contain the search_string
    matching_channels = [channel for channel in category.text_channels if search_string.lower() in channel.name.lower()]
    user_display_name = ctx.user.display_name

    # Check if any matching channels were found
    if matching_channels:
        embed = discord.Embed(title=f"{user_display_name} -> {search_string}", color=discord.Color.green())
        for channel in matching_channels:
            embed.add_field(name=channel.name, value=f"<#{channel.id}>", inline=False)
        embed.set_footer(text="FIB-Net")
        await ctx.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title=f"{user_display_name} -> {search_string}", color=discord.Color.red())
        embed.add_field(name="", value="Keine Ergebnisse", inline=False)
        embed.set_footer(text="FIB-Net")
        await ctx.response.send_message(embed=embed)


# Modal for the /eintrag command (text input)
class EintragModal(discord.ui.Modal, title="Neuen Eintrag erstellen"):
    eintrag_text = discord.ui.TextInput(
        label="Inhalt des Eintrags",
        style=discord.TextStyle.paragraph,  # Allows multiline input
        placeholder="Geben Sie den Inhalt des Eintrags ein",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        now = datetime.now()
        formatted_date_time = now.strftime("%d.%m.%Y %H:%M")
        user_display_name = interaction.user.display_name
        category = interaction.channel.category
        channel = interaction.channel

        # Validate channel and category
        valid_categories = ["Akten", "Berichte"]
        if category is None or category.name not in valid_categories or channel.name == "archiv":
            await interaction.response.send_message(
                "This command cannot be used in the 'Archiv' channel or outside the 'Akten' or 'Berichte' categories.",
                ephemeral=True
            )
            return

        # Create embed for text content
        base = discord.Embed(
            title=f"{formatted_date_time} | {user_display_name}",
            description=self.eintrag_text.value
        )
        base.set_footer(text="FIB-Net")
        await interaction.response.send_message(embed=base)


# Slash command to trigger the /eintrag modal (text only)
@bot.tree.command(name="eintrag", description="Erstellt einen neuen Text-Eintrag")
async def eintrag(interaction: discord.Interaction):
    modal = EintragModal()
    await interaction.response.send_modal(modal)


# Command for /beweis to handle file attachments (images/videos)
@bot.tree.command(name="beweis", description="Fügt ein Bild oder Video als Beweis hinzu")
@app_commands.describe(attachment="Anhang/Beweis (Bild/Video)")
async def beweis(interaction: discord.Interaction, attachment: discord.Attachment):
    now = datetime.now()
    formatted_date_time = now.strftime("%d.%m.%Y %H:%M")
    user_display_name = interaction.user.display_name
    category = interaction.channel.category
    channel = interaction.channel

    # Validate channel and category
    valid_categories = ["Akten", "Berichte"]
    if category is None or category.name not in valid_categories or channel.name == "archiv":
        await interaction.response.send_message(
            "This command cannot be used in the 'Archiv' channel or outside the 'Akten' or 'Berichte' categories.",
            ephemeral=True
        )
        return

    # Defer response to give more time for processing
    await interaction.response.defer()

    # Ensure the "Images" directory exists
    os.makedirs("Images", exist_ok=True)

    # Handle image attachments
    if attachment.content_type.startswith('image/'):
        image_path = os.path.join("Images", f"{attachment.filename}")
        await attachment.save(image_path)

        # Send the locally saved image
        with open(image_path, 'rb') as f:
            image_file = discord.File(f, filename=attachment.filename)
            image_embed = discord.Embed()
            image_embed.set_image(url=f"attachment://{attachment.filename}")
            image_embed.set_footer(text=f"Beweis {formatted_date_time} | {user_display_name}")
            await interaction.followup.send(embed=image_embed, file=image_file)

    # Handle video attachments
    elif attachment.content_type.startswith('video/'):
        video_path = os.path.join("Images", f"{attachment.filename}")
        await attachment.save(video_path)

        # Check file size and avoid sending oversized files
        if attachment.size > 64000000:
            await interaction.followup.send("The file is too large. Please upload a smaller video.")
            return

        # Send the locally saved video
        with open(video_path, 'rb') as f:
            video_file = discord.File(f, filename=attachment.filename)
            message = await interaction.followup.send(file=video_file)

            # Create a link to the video
            video_link = message.attachments[0].url
            video_embed = discord.Embed()
            video_embed.add_field(name="", value=f"Video Link: {video_link}")
            video_embed.set_footer(text=f"Beweis {formatted_date_time} | {user_display_name}")
            await interaction.channel.send(embed=video_embed)

    else:
        await interaction.followup.send("Unsupported file type. Only images and videos are allowed.")


bot.run(token)
