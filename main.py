import random
import re
import os
import unicodedata
import logging

import discord
from discord import app_commands

import youtube_module
import chatbot_module
import settings_manager

logger = logging.getLogger("discord")
settings = settings_manager.load_settings()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
command_tree = app_commands.CommandTree(client)
synced = False


@command_tree.command(name="play", description="Plays a youtube video.")
async def play_youtube(context: discord.Interaction, link: str):
    async with context.channel.typing():
        await context.response.send_message(content="Loading video info...")

    # Try to get YouTube video info
    try:
        info = youtube_module.get_video_info(link)
        song_title = info["title"]
        song_title_formatted = slugify(song_title)
    except youtube_module.yt_dlp.utils.DownloadError or TypeError:
        await context.edit_original_response(
            content="That link dont work", ephemeral=True
        )
        return

    # Try to get the user's voice channel
    voice_channel = context.user.voice.channel
    if voice_channel is None:
        await context.edit_original_response(
            content="You need to be in a voice channel to play a video."
        )
        return

    # Download the audio from the YouTube video
    try:
        async with context.channel.typing():
            await context.edit_original_response(content="Downloading video...")
            youtube_module.download_audio(
                link, settings["download_path"] / song_title_formatted
            )
    except PermissionError:
        logger.info("Audio file already in use. Skipping download...")

    # Create song object
    song = youtube_module.Song(
        song_title,
        settings["download_path"] / f"{song_title_formatted}.mp3",
        0,
        context.channel,
    )

    # If there is no playlist for this server, create one, add the song, and start the playlist
    # When playlist finishes, disconnect and destroy the playlist object
    if youtube_module.guild_playlist.get(context.guild) is None:
        voice_client = await voice_channel.connect()
        playlist = youtube_module.Playlist(context.guild, voice_client)
        playlist.add_song(song)
        youtube_module.guild_playlist[context.guild] = playlist
        await context.edit_original_response(content=f"Now playing: {song_title}")
        await playlist.start_playlist()
        await voice_client.disconnect()
        youtube_module.guild_playlist.pop(context.guild)

    # Otherwise, add the song to the existing playlist for this server
    else:
        playlist = youtube_module.guild_playlist[context.guild]
        playlist.add_song(song)
        await context.edit_original_response(
            content=f"{song_title} added to queue.\n{len(playlist.songs) - 1} videos in queue."
        )


@command_tree.command(
    name="skip", description="Skips to the next video in the playlist"
)
async def skip_youtube(context: discord.Interaction):
    await context.response.send_message(content="Skipping...")
    # If server does not have an active playlist, skip skipping
    if youtube_module.guild_playlist[context.guild] is None:
        await context.edit_original_response(content="Can't skip; no videos playing.")
        return
    playlist = youtube_module.guild_playlist[context.guild]
    await playlist.next_song()


def slugify(value, allow_unicode=False):
    """
    Taken from https://docs.djangoproject.com/en/4.1/_modules/django/utils/text/#slugify
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


@client.event
async def on_message(message):
    channel_id = message.channel.id
    if channel_id in chatbot_module.channel_bots:
        chat_bot = chatbot_module.channel_bots[channel_id]

    async def chatbot_respond():
        chat_bot = chatbot_module.channel_bots[channel_id]
        response = await chat_bot.get_response()
        await message.channel.send(content=response)

    if client.user in message.mentions and channel_id in chatbot_module.channel_bots:
        await chatbot_respond()
    elif (
            channel_id in settings["chatbot_unrestricted_channels"]
            and random.uniform(0, 1) < settings["chatbot_response_chance"]
            and client.user is not message.author
    ):
        await chatbot_respond()


@client.event
async def on_ready():
    logger.info("Carrot Bot Online")

    # Synchronize commands
    global synced
    if not synced:
        await command_tree.sync()
        logger.info("Synchronized commands")
        synced = True

    # Initialize chatbots
    for channel_id in settings["chatbot_channels"]:
        channel = client.get_channel(channel_id)
        chatbot_module.channel_bots[channel_id] = chatbot_module.ChatBot(
            channel, client
        )


if "CARROT_BOT_TOKEN" in os.environ.keys():
    client.run(os.environ["CARROT_BOT_TOKEN"])
else:
    raise KeyError("You must set the CARROT_BOT_TOKEN system environment variable.")
    exit(1)
