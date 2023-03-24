import discord
from discord import app_commands
import asyncio
import json
import yt_dlp

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

with open("settings.json", "rb") as settings_file:
    settings = json.load(settings_file)
    token = settings["token"]
    settings_file.close()


def get_video_info(youtube_link):
    info = yt_dlp.YoutubeDL({'quiet': True}).extract_info(youtube_link, download=False)

    return info


def download_audio(youtube_link, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path,
        'noplaylist': True,
        'ffmpeg_location': 'ffmpeg/bin/'
    }

    yt_dlp.YoutubeDL(ydl_opts).download([youtube_link])


@tree.command(name="play", description="Plays a youtube video.")
async def play_youtube(ctx: discord.Interaction, link: str):
    try:
        info = get_video_info(link)
    except yt_dlp.utils.DownloadError:
        await ctx.response.send_message(content="That link dont work", ephemeral=True)
        return

    file_name = "audio"
    file_path = "downloads/" + file_name
    download_audio(link, file_path)

    if ctx.user.voice.channel is not None:
        voice_client = await ctx.user.voice.channel.connect()
        voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg/bin/ffmpeg.exe", source=file_path + ".mp3"))

        channel = ctx.channel
        response = await channel.send("Now Playing: " + info["title"])
        while voice_client.is_playing():
            await asyncio.sleep(1)
        await voice_client.disconnect()
        await response.edit(content="Finished Playing: " + info["title"])
    else:
        await ctx.response.send_message(content="You gotta be in a voice channel to play videos.", ephemeral=True)


async def on_ready():
    print("Carrot Bot Online")


client.run(token)
