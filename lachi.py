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

# ==================== CONFIGURATION ====================

class Config:
    """Load token and master ID from environment variables"""

    def __init__(self):
        # Token from environment variable
        self.token = os.environ.get("DISCORD_TOKEN")

        # Master ID from environment variable
        master_id = os.environ.get("MASTER_ID")
        if master_id:
            try:
                self.master_id = int(master_id)
            except ValueError:
                raise ValueError("MASTER_ID must be a valid user ID number")
        else:
            raise ValueError("MASTER_ID environment variable not set")

        # Fallback to token.json if no env token
        if not self.token:
            try:
                with open("token.json", "r") as f:
                    config = json.load(f)
                    self.token = config.get("token")
            except:
                raise ValueError("No token found. Set DISCORD_TOKEN env var or create token.json")

# ==================== BANNER ====================

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Print Lachi Bot banner"""
    clear_screen()

    bold = "\033[1m"
    reset = "\033[0m"

    banner = bold + r"""
 ██╗ █████╗ ██████╗██╗ ██╗██╗ ██████╗ ██████╗ ████████╗
 ██║ ██╔══██╗██╔════╝██║ ██║██║ ██╔══██╗██╔═══██╗╚══██╔══╝
 ██║ ███████║██║ ███████║██║ ██████╔╝██║ ██║ ██║ 
 ██║ ██╔══██║██║ ██╔══██║██║ ██╔══██╗██║ ██║ ██║ 
 ███████╗██║ ██║╚██████╗██║ ██║██║ ██████╔╝╚██████╔╝ ██║ 
 ╚══════╝╚═╝ ╚═╝ ╚═════╝╚═╝ ╚═╝╚═╝ ╚═════╝ ╚═════╝ ╚═╝ 
 """ + reset

    print(banner)
    print(f"{bold} Auto-React System | DM Control Only{reset}")
    print(" " + "─" * 60)
    print()

# ==================== BOT SETUP ====================

config = Config()
bot = commands.Bot(command_prefix=",", self_bot=True)

targets = {}
admin_users = set()
STORAGE_FILE = "reactions.json"

# ==================== PERSISTENT STORAGE ====================

def save_data():
    """Save reactions and admins to JSON file"""
    data = {
        "targets": {str(k): v for k, v in targets.items()},
        "admins": list(admin_users)
    }
    try:
        with open(STORAGE_FILE, "w") as f:
            json.dump(data, f, indent=2)

        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}[SAVE]{reset} Data saved to {STORAGE_FILE}")
    except Exception as e:
        print(f"[SAVE] Error: {e}")

def load_data():
    """Load reactions and admins from JSON file"""
    global targets, admin_users

    try:
        with open(STORAGE_FILE, "r") as f:
            data = json.load(f)

        targets = {int(k): v for k, v in data.get("targets", {}).items()}
        admin_users = set(data.get("admins", []))

        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}[LOAD]{reset} Loaded {len(targets)} targets and {len(admin_users)} admins")

    except FileNotFoundError:
        print(f"[LOAD] No existing {STORAGE_FILE} - starting fresh")
    except Exception as e:
        print(f"[LOAD] Error: {e}")

# ==================== RUN ====================

if __name__ == "__main__":
    try:
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}Starting Lachi Bot...{reset}")
        bot.run(config.token)
    except discord.LoginFailure:
        print("Invalid token")
    except Exception as e:
        print(f"Error: {e}")
