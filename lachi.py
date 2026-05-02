"""
Minimal Discord Self-Bot - Auto React & Auto Delete
Core functions only: React to users and auto-delete all bot messages
"""
import os
import json
import asyncio
from pathlib import Path
import discord
from discord.ext import commands
from datetime import datetime

# ==================== CONFIGURATION ====================
class Config:
    """Load token from environment variable or token.json"""
    def __init__(self):
        self.token = os.environ.get("DISCORD_TOKEN")
        if not self.token:
            try:
                with open("token.json", "r") as f:
                    config = json.load(f)
                    self.token = config.get("token")
            except Exception:
                raise ValueError("No token found. Set DISCORD_TOKEN env var or create token.json")

# ==================== BANNER ====================
def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Print Cuck Bot banner with white background black text"""
    clear_screen()
    white_bg = "\033[47m"
    black_text = "\033[30m"
    bold = "\033[1m"
    reset = "\033[0m"
    banner = bold + r"""
██████╗██╗
██╗ ██████╗██╗
██╗
██████╗
██████╗ ████████╗
██╔════╝██║
██║██╔════╝██║ ██╔/
██╔══██╗██╔═══██╗╚══██╔══╝
██║
██║
██║██║
█████╔/
██████╔╝██║
██║
██║
██║
██║
██║██║
██╔═██╗
██╔══██╗██║
██║
██║
╚██████╗╚██████╔╝╚██████╗██║
██╗
██████╔╝╚██████╔╝
██║
╚═════╝ ╚═════╝
╚═╝
╚═════╝
╚═╝
╚═════╝╚═╝
╚═════╝
""" + reset
    print(banner)
    print(f"{bold}Commands delete automatically | Type ,cmds{reset}")
    print("─" * 60)
    print()

# ==================== BOT SETUP ====================
config = Config()
bot = commands.Bot(command_prefix=",", self_bot=True)

# Reaction targets: {user_id: [emoji1, emoji2, ...]}
targets = {}
# Admin user who can control the bot
ADMIN_USER_ID = 422023069586948098

# ==================== LOGGING ====================
def log_reaction(success: bool, user_name: str, emoji: str, reason: str = ""):
    """Log reaction attempts with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    bold = "\033[1m"
    dim = "\033[2m"
    reset = "\033[0m"
    if success:
        print(f"{dim}[{timestamp}]{reset} {bold}✓{reset} Reacted to {user_name} with {emoji}")
    else:
        print(f"{dim}[{timestamp}]{reset} {bold}✗{reset} Failed to react to {user_name} with {emoji} ({reason})")

# ==================== AUTO-DELETE HELPER ====================
async def delete_after_delay(message, delay=3):
    """Delete a message after delay"""
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception:
        pass

# ==================== EVENTS ====================
@bot.event
async def on_ready():
    """Display banner when bot is ready"""
    # Set terminal title
    if os.name == 'nt':
        os.system(f"title Cuck Bot @ {bot.user}")
    else:
        print(f"\033]0;Cuck Bot @ {bot.user}\007", end='', flush=True)
    print_banner()
    bold = "\033[1m"
    reset = "\033[0m"
    print(f"{bold}✓{reset} Logged in as {bot.user}")
    print(f"{bold}✓{reset} Auto-react enabled")
    print(f"{bold}✓{reset} Admin control: User ID {ADMIN_USER_ID}")
    print(f"{bold}✓{reset} Ready | Type ,cmds for commands")
    print()

@bot.event
async def on_message(message):
    # Ignore own messages except commands
    if message.author.id == bot.user.id and not message.content.startswith(","):
        return

    # Process commands first
    await bot.process_commands(message)

    # Auto-delete bot's own messages after short delay
    if message.author.id == bot.user.id:
        asyncio.create_task(delete_after_delay(message, 3))
        return

    # Admin commands via mention
    if message.author.id == ADMIN_USER_ID and bot.user in message.mentions:
        content = message.content.replace(f'<@{bot.user.id}>', '').strip()
        if content.startswith('react '):
            parts = content.split()
            if len(parts) >= 3:
                user_mention = parts[1]
                emojis = parts[2:]
                try:
                    user_id = int(user_mention.strip('<@!>'))
                    if user_id not in targets:
                        targets[user_id] = []
                    targets[user_id].extend(emojis)
                    await message.add_reaction('✅')
                    print(f"[ADMIN] Added reactions {', '.join(emojis)} for user {user_id}")
                except Exception as e:
                    await message.add_reaction('❌')
                    print(f"[ADMIN] Error: {e}")

        elif content.startswith('stop '):
            parts = content.split()
            if len(parts) >= 2:
                user_mention = parts[1]
                try:
                    user_id = int(user_mention.strip('<@!>'))
                    if user_id in targets:
                        targets.pop(user_id)
                        await message.add_reaction('✅')
                        print(f"[ADMIN] Stopped reacting to user {user_id}")
                    else:
                        await message.add_reaction('❌')
                except Exception as e:
                    await message.add_reaction('❌')
                    print(f"[ADMIN] Error: {e}")

        elif content == 'clear':
            targets.clear()
            await message.add_reaction('✅')
            print("[ADMIN] Cleared all targets")

        elif content == 'list':
            if targets:
                lines = ["**Active Targets:**"]
                for uid, emojis in targets.items():
                    try:
                        user = await bot.fetch_user(uid)
                        lines.append(f"• {user.name}: {', '.join(emojis)}")
                    except Exception:
                        lines.append(f"• User {uid}: {', '.join(emojis)}")
                await message.channel.send("\n".join(lines))
                await message.add_reaction('✅')
            else:
                await message.channel.send("No active targets")
                await message.add_reaction('❌')

    # Auto-react to targeted users
    if message.author.id in targets:
        for emoji in targets[message.author.id]:
            try:
                await message.add_reaction(emoji)
                log_reaction(True, message.author.name, emoji)
            except Exception as e:
                log_reaction(False, message.author.name, emoji, str(e))

# ==================== COMMANDS ====================
@bot.command()
async def react(ctx, user: discord.User, *emojis):
    """Auto-react to user's messages. Usage: ,react @user <emoji>..."""
    if not emojis:
        msg = await ctx.send("Provide at least one emoji")
        asyncio.create_task(delete_after_delay(msg, 3))
        return
    targets.setdefault(user.id, []).extend(emojis)
    msg = await ctx.send(f"✓ Reacting to {user.name} with {', '.join(emojis)}")
    asyncio.create_task(delete_after_delay(msg, 3))

@bot.command()
async def stop(ctx, user: discord.User):
    """Stop auto-reacting to user. Usage: ,stop @user"""
    if user.id in targets:
        targets.pop(user.id)
        msg = await ctx.send(f"✓ Stopped reacting to {user.name}")
    else:
        msg = await ctx.send(f"Not reacting to {user.name}")
    asyncio.create_task(delete_after_delay(msg, 3))

@bot.command()
async def clear(ctx):
    """Clear all reaction targets. Usage: ,clear"""
    targets.clear()
    msg = await ctx.send("✓ Cleared all targets")
    asyncio.create_task(delete_after_delay(msg, 3))

@bot.command()
async def list(ctx):
    """List all reaction targets. Usage: ,list"""
    if not targets:
        msg = await ctx.send("No active targets")
        asyncio.create_task(delete_after_delay(msg, 3))
        return
    lines = ["**Active Targets:**"]
    for uid, emojis in targets.items():
        user = bot.get_user(uid)
        name = user.name if user else f"User {uid}"
        lines.append(f"• {name}: {', '.join(emojis)}")
    msg = await ctx.send("\n".join(lines))
    asyncio.create_task(delete_after_delay(msg, 5))

@bot.command()
async def cmds(ctx):
    """Display all available commands"""
    help_text = """```
╔══════════════════════════════════════╗
║          CUCK BOT COMMANDS            ║
╚══════════════════════════════════════╝
Regular Commands:
,react @user <emoji>...   - Auto-react to user
,stop @user               - Stop reacting to user
,list                     - Show active targets
,clear                    - Clear all targets
,purge <x>                - Delete x of your messages
,cmds                     - Show this menu

Admin Commands (via mention):
@bot react @user <emoji>... - Add reactions instantly
@bot stop @user            - Stop reacting instantly
@bot clear                 - Clear all
@bot list                  - Show targets instantly

Admin User: 422023069586948098
All command responses auto-delete
Reactions are logged with timestamps
```"""
    msg = await ctx.send(help_text)
    asyncio.create_task(delete_after_delay(msg, 15))

@bot.command(aliases=['prune'])
async def purge(ctx, amount: int):
    """Delete your messages from current channel. Usage: ,purge <x>"""
    if amount <= 0:
        msg = await ctx.send("Amount must be positive")
        asyncio.create_task(delete_after_delay(msg, 3))
        return
    if amount > 100:
        msg = await ctx.send("Maximum is 100 messages")
        asyncio.create_task(delete_after_delay(msg, 3))
        return

    def is_me(m):
        return m.author.id == bot.user.id

    try:
        if isinstance(ctx.channel, discord.DMChannel):
            deleted_count = 0
            async for message in ctx.channel.history(limit=amount):
                if is_me(message):
                    try:
                        await message.delete()
                        deleted_count += 1
                        await asyncio.sleep(0.3)
                    except Exception:
                        pass
        else:
            deleted = await ctx.channel.purge(limit=amount, check=is_me)
            deleted_count = len(deleted)

        print(f"\033[1m[PURGE]\033[0m Deleted {deleted_count} messages in #{getattr(ctx.channel, 'name', 'DM')}")
        msg = await ctx.send(f"Deleted {deleted_count} messages")
        asyncio.create_task(delete_after_delay(msg, 3))
    except discord.Forbidden:
        msg = await ctx.send("Missing permissions to delete messages")
        asyncio.create_task(delete_after_delay(msg, 3))
    except Exception as e:
        msg = await ctx.send(f"Error: {str(e)[:50]}")
        asyncio.create_task(delete_after_delay(msg, 3))

# ==================== RUN ====================
if __name__ == "__main__":
    try:
        print("\033[1mStarting Cuck Bot...\033[0m")
        bot.run(config.token)
    except discord.LoginFailure:
        print("Invalid token")
    except Exception as e:
        print(f"Error: {e}")