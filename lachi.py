"""
Lachi Bot - Discord Self-Bot
Auto-react system with master/admin control
All communication via DM only
"""

import os
import json
import asyncio
from pathlib import Path
import discord
from discord.ext import commands

class Config:
    def __init__(self):
        self.token = os.environ.get("DISCORD_TOKEN")

        master_id = os.environ.get("MASTER_ID")
        if master_id:
            try:
                self.master_id = int(master_id)
            except ValueError:
                raise ValueError("MASTER_ID must be a valid user ID number")
        else:
            raise ValueError("MASTER_ID environment variable not set")

        if not self.token:
            try:
                with open("token.json", "r") as f:
                    config = json.load(f)
                    self.token = config.get("token")
            except:
                raise ValueError("No token found. Set DISCORD_TOKEN env var or create token.json")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    clear_screen()
    print("Lachi Bot Running")

config = Config()
bot = commands.Bot(command_prefix=",", self_bot=True)

targets = {}
admin_users = set()
STORAGE_FILE = "reactions.json"

def save_data():
    data = {
        "targets": {str(k): v for k, v in targets.items()},
        "admins": list(admin_users)
    }
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_data():
    global targets, admin_users
    try:
        with open(STORAGE_FILE, "r") as f:
            data = json.load(f)
        targets = {int(k): v for k, v in data.get("targets", {}).items()}
        admin_users = set(data.get("admins", []))
    except:
        pass

@bot.event
async def on_ready():
    print_banner()
    load_data()
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.id in targets:
        for emoji in targets[message.author.id]:
            try:
                await message.add_reaction(emoji)
            except:
                pass
    await bot.process_commands(message)

@bot.command()
async def purge(ctx, amount: int):
    def is_me(m):
        return m.author.id == bot.user.id
    deleted = await ctx.channel.purge(limit=amount, check=is_me)
    print(f"Deleted {len(deleted)} messages")

if __name__ == "__main__":
    bot.run(config.token)
