import yt_dlp
import logging
import discord
import asyncio

logger = logging.getLogger("discord")
guild_playlist = {}


class Song:
    def __init__(self, title, file_path, length, text_channel):
        self.title = title
        self.file_path = file_path
        self.is_playing = 0
        self.length = length
        self.text_channel = text_channel
        self.playlist = None

    def __repr__(self):
        return self.title

    async def play(self, voice_client, start_time=0):
        if voice_client.is_connected():
            voice_client.play(
                discord.FFmpegPCMAudio(
                    executable="ffmpeg/bin/ffmpeg.exe",
                    source=self.file_path,
                    options="-ss " + str(start_time),
                )
            )
            self.is_playing = True
            if self.playlist.current_song_index != 0:
                await self.text_channel.send("Now playing: " + self.title)
            while voice_client.is_playing():
                await asyncio.sleep(1)
            self.is_playing = False


class Playlist:
    def __init__(self, guild, voice_client):
        self.guild = guild
        self.voice_client = voice_client
        self.songs = []
        self.current_song_index = 0
        self.current_song_time = 0

    async def play_at_index(self, song_index, start_time=0):
        self.current_song_index = song_index
        await self.songs[self.current_song_index].play(self.voice_client, start_time)

    async def start_playlist(self, song_index=0):
        self.current_song_index = song_index

        while self.current_song_index < len(self.songs):
            await self.songs[self.current_song_index].play(self.voice_client)
            self.current_song_index += 1

    def add_song(self, playlist_song):
        self.songs.append(playlist_song)
        playlist_song.playlist = self

    def clear(self):
        self.songs = []
        self.current_song_index = 0
        self.current_song_time = 0


def get_video_info(youtube_link):
    try:
        info = yt_dlp.YoutubeDL({"quiet": True}).extract_info(
            youtube_link, download=False
        )
        return info
    except yt_dlp.utils.DownloadError:
        logger.error("Video download failed: " + youtube_link)
        return


def download_audio(youtube_link, output_path):
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": output_path,
        "noplaylist": True,
        "ffmpeg_location": "ffmpeg/bin/",
    }

    yt_dlp.YoutubeDL(ydl_opts).download([youtube_link])
