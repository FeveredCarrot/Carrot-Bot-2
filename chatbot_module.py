import logging
import os
import sys

import discord
import openai

import settings_manager

logger = logging.getLogger("discord")
settings = settings_manager.load_settings()
if os.environ["OPENAI_API_KEY"] is None:
    logger.error("You must set the OPENAI_API_KEY system environment variable.")
    sys.exit(1)
else:
    openai.api_key = os.environ["OPENAI_API_KEY"]

channel_bots = {}


class ChatBot:
    def __init__(self, channel, client):
        self.channel = channel
        self.client = client
        self.messages = []

    async def generate_messages_list(self):
        self.messages = []
        async for message in self.channel.history(
            limit=settings["chatbot_history_limit"]
        ):
            self.messages.append(self.format_message(message))
        self.messages.append(settings["chatbot_prompt"])
        self.messages.reverse()

    def format_message(self, message):
        if message.author.id == self.client.user.id:
            return {
                "role": "assistant",
                "content": f"{message.author.name}: {message.content}",
            }
        else:
            return {
                "role": "user",
                "content": f"{message.author.name}: {message.content}",
            }

    async def get_response(self):
        await self.generate_messages_list()
        logger.info(self.messages)
        async with self.channel.typing():
            response = openai.ChatCompletion.create(
                model=settings["openai_model"], messages=self.messages
            )
        response = response["choices"][0]["message"]["content"]
        if "Carrot Bot:" in response[:12]:
            response = response[12:]
        return response
