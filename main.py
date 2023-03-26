import re
import sys
import discord
import unicodedata
from discord import app_commands
import logging
import json
import youtube_module

# discord.utils.setup_logging()
logger = logging.getLogger("discord")
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

synced = False

with open("settings.json", "rb") as settings_file:
    try:
        settings = json.load(settings_file)
        token = settings["token"]
        download_path = settings["download path"]
    except json.JSONDecodeError:
        logger.error("Failed to load settings.json. Aborting...")
        sys.exit(1)


@tree.command(name="play", description="Plays a youtube video.")
async def play_youtube(context: discord.Interaction, link: str):
    # Try to get YouTube video info
    try:
        info = youtube_module.get_video_info(link)
        song_title = info["title"]
        song_title_formatted = slugify(song_title)
    except youtube_module.yt_dlp.utils.DownloadError or TypeError:
        await context.response.send_message(content="That link dont work", ephemeral=True)
        return

    # Try to get the user's voice channel
    voice_channel = context.user.voice.channel
    if voice_channel is None:
        await context.response.send_message("You need to be in a voice channel to play a video.")
        return

    # Download the audio from the YouTube video
    try:
        youtube_module.download_audio(link, download_path + song_title_formatted)
    except PermissionError:
        logger.info("Audio file already in use. Skipping download...")

    # Create song object
    song = youtube_module.Song(
        song_title, download_path + song_title_formatted + ".mp3", 0, context.channel
    )

    # If there is no playlist for this server, create one, add the song, and start the playlist
    # When playlist finishes, disconnect and destroy the playlist object
    if youtube_module.guild_playlist.get(context.guild) is None:
        voice_client = await voice_channel.connect()
        playlist = youtube_module.Playlist(context.guild, voice_client)
        playlist.add_song(song)
        youtube_module.guild_playlist[context.guild] = playlist
        await context.response.send_message("Now playing: " + song_title)
        await playlist.start_playlist()
        await voice_client.disconnect()
        youtube_module.guild_playlist.pop(context.guild)

    # Otherwise, add the song to the existing playlist for this server
    else:
        playlist = youtube_module.guild_playlist[context.guild]
        playlist.add_song(song)
        await context.response.send_message(
            song_title
            + " added to queue.\n"
            + str(len(playlist.songs) - 1)
            + " videos in queue."
        )


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
async def on_ready():
    logger.info("Carrot Bot Online")
    global synced
    if not synced:
        await tree.sync(guild=client.get_guild(403381473647919114))
        synced = True


client.run(token)
