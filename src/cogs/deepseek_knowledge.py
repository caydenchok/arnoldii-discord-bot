import os
import logging
import discord
from discord.ext import commands
import asyncio
import time
import json
import requests
import re
from datetime import datetime
from collections import defaultdict, deque

logger = logging.getLogger('arnoldii.deepseek')

class DeepSeekKnowledge(commands.Cog):
    """Main cog for Arnoldii chatbot using DeepSeek API"""

    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"  # Default model

        # Store conversation history for each channel
        self.conversation_history = defaultdict(lambda: deque(maxlen=10))

        # System prompt for DeepSeek
        self.system_prompt = (
            "You are Arnoldii, an advanced AI assistant developed by Astragate. "
            "You are helpful, friendly, and extremely knowledgeable. "
            "Always introduce yourself as 'Arnoldii, developed by Astragate' when meeting someone new. "
            "You can answer questions on a wide range of topics with accurate, up-to-date information. "
            "When you don't know something, admit it rather than making up information. "
            "Keep your responses conversational but informative."
        )

        # Track usage to avoid exceeding rate limits or budget
        self.usage_tracking = {
            'total_tokens': 0,
            'requests_today': 0,
            'last_reset': datetime.now().date()
        }

    async def call_deepseek_api(self, messages):
        """Call the DeepSeek API with the given messages"""
        if not self.api_key:
            return "Error: DeepSeek API key not configured. Please set the DEEPSEEK_API_KEY environment variable."

        # Check if we need to reset the daily counter
        today = datetime.now().date()
        if today > self.usage_tracking['last_reset']:
            self.usage_tracking['requests_today'] = 0
            self.usage_tracking['last_reset'] = today

        # Increment request counter
        self.usage_tracking['requests_today'] += 1

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            async def _make_request():
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                return response.json()

            response_json = await asyncio.to_thread(_make_request)

            # Track token usage if available in the response
            if 'usage' in response_json and 'total_tokens' in response_json['usage']:
                self.usage_tracking['total_tokens'] += response_json['usage']['total_tokens']
                logger.info(f"Total tokens used: {self.usage_tracking['total_tokens']}")

            if 'choices' in response_json and len(response_json['choices']) > 0:
                return response_json['choices'][0]['message']['content']
            else:
                logger.error(f"Unexpected API response: {response_json}")
                return "I encountered an error while processing your request. Please try again later."

        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return f"I encountered an error: {str(e)}"

    def _format_conversation(self, channel_id, new_user_message=None):
        """Format the conversation history for the AI"""
        # Start with the system prompt
        formatted = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history
        for speaker, message in self.conversation_history[channel_id]:
            role = "assistant" if speaker == "Arnoldii" else "user"
            formatted.append({"role": role, "content": message})

        # Add the new message if provided
        if new_user_message:
            formatted.append({"role": "user", "content": new_user_message})

        return formatted

    async def send_response(self, ctx, response):
        """Send a response, splitting into chunks if necessary"""
        if len(response) > 1900:
            chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await ctx.send(chunk)
                else:
                    await ctx.send(f"(continued) {chunk}")
        else:
            await ctx.send(response)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages that might be directed at Arnoldii"""
        # Don't respond to our own messages
        if message.author == self.bot.user:
            return

        # Don't respond to commands (they start with !)
        if message.content.startswith('!'):
            return

        # Check if the bot is mentioned or called by name
        is_mentioned = self.bot.user.mentioned_in(message) and not message.mention_everyone
        is_called = any(name.lower() in message.content.lower() for name in ['arnoldii', 'arnold'])

        if is_mentioned or is_called:
            async with message.channel.typing():
                # Get the content of the message
                content = message.content

                # If the bot is mentioned, remove the mention from the content
                if is_mentioned:
                    content = re.sub(f'<@!?{self.bot.user.id}>', '', content).strip()

                # If the content is empty after removing the mention, treat it as a greeting
                if not content:
                    content = "Hello"

                # Add the user message to history
                channel_id = message.channel.id
                self.conversation_history[channel_id].append(("User", content))

                # Format the conversation with history
                messages = self._format_conversation(channel_id)

                # Call the API
                start_time = time.time()
                response = await self.call_deepseek_api(messages)
                response_time = time.time() - start_time
                logger.info(f"DeepSeek API response time: {response_time:.2f} seconds")

                # Add the bot's response to history
                self.conversation_history[channel_id].append(("Arnoldii", response))

                # Send the response
                await self.send_response(message.channel, response)

    @commands.command(name='chat')
    async def chat(self, ctx, *, message: str):
        """Chat with Arnoldii"""
        async with ctx.typing():
            # Add the user message to history
            channel_id = ctx.channel.id
            self.conversation_history[channel_id].append(("User", message))

            # Format the conversation with history
            messages = self._format_conversation(channel_id)

            # Call the API
            start_time = time.time()
            response = await self.call_deepseek_api(messages)
            response_time = time.time() - start_time
            logger.info(f"DeepSeek API response time: {response_time:.2f} seconds")

            # Add the bot's response to history
            self.conversation_history[channel_id].append(("Arnoldii", response))

            # Send the response
            await self.send_response(ctx, response)

    @commands.command(name='clear')
    async def clear_chat(self, ctx):
        """Clear the conversation history for this channel"""
        channel_id = ctx.channel.id
        self.conversation_history[channel_id].clear()
        await ctx.send("✅ Conversation history cleared!")

    @commands.command(name='usage')
    async def check_usage(self, ctx):
        """Check the current DeepSeek API usage"""
        if ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="DeepSeek API Usage",
                description="Current usage statistics for the DeepSeek API",
                color=discord.Color.blue()
            )

            embed.add_field(name="Total Tokens Used", value=str(self.usage_tracking['total_tokens']), inline=True)
            embed.add_field(name="Requests Today", value=str(self.usage_tracking['requests_today']), inline=True)
            embed.add_field(name="Last Reset", value=str(self.usage_tracking['last_reset']), inline=True)

            await ctx.send(embed=embed)
        else:
            await ctx.send("You need administrator permissions to check API usage.")

def setup(bot):
    bot.add_cog(DeepSeekKnowledge(bot))
