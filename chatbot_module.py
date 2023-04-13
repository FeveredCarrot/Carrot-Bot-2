import json
import logging
import os
import ssl
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
        self.messages.reverse()
        self.messages = ChatBot.load_prompts() + self.messages

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

    @staticmethod
    def load_prompts():
        with open(settings["chatbot_prompts"], "r") as prompts_file:
            prompts = json.load(prompts_file)
        return prompts

    @staticmethod
    def sanitize_output(message_content):
        message_content = message_content.replace("@everyone", "@​everyone")
        return message_content

    async def get_response(self):
        await self.generate_messages_list()
        logger.info("Responding to message...")
        async with self.channel.typing():
            try:
                response = openai.ChatCompletion.create(
                    model=settings["openai_model"],
                    messages=self.messages,
                    temperature=settings["chatbot_temperature"],
                )
            except openai.error.RateLimitError:
                logger.error("Response failed. Bot is being rate limited by OpenAI.")
                await self.channel.send("Guh, I am being rate limited by OpenAI. Try again later.")
            except ssl.SSLError:
                logger.error("Response failed. OpenAI API request timed out.")
                await self.channel.send("Guh, the API request timed out. Try again later.")

        response = response["choices"][0]["message"]["content"]
        if "Carrot Bot:" in response[:12]:
            response = response[12:]
        logger.info(f"Response: {response}")
        return response
