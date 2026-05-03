"""
Cuck Bot - Discord Self-Bot
Auto-react system with master/admin control
All communication via DM only
PostgreSQL version - data persists across deployments
"""
import os
import asyncio
import discord
from discord.ext import commands
import asyncpg

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
        
        # PostgreSQL connection (Railway sets this automatically)
        self.database_url = os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not found. Add PostgreSQL to Railway project.")

# ==================== BANNER ====================
def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Print Cuck Bot banner"""
    clear_screen()
    
    bold = "\033[1m"
    reset = "\033[0m"
    
    banner = bold + r"""
  ██████╗██╗   ██╗ ██████╗██╗  ██╗    ██████╗  ██████╗ ████████╗
 ██╔════╝██║   ██║██╔════╝██║ ██╔╝    ██╔══██╗██╔═══██╗╚══██╔══╝
 ██║     ██║   ██║██║     █████╔╝     ██████╔╝██║   ██║   ██║   
 ██║     ██║   ██║██║     ██╔═██╗     ██╔══██╗██║   ██║   ██║   
 ╚██████╗╚██████╔╝╚██████╗██║  ██╗    ██████╔╝╚██████╔╝   ██║   
  ╚═════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝    ╚═════╝  ╚═════╝    ╚═╝   
    """ + reset
    
    print(banner)
    print(f"{bold}       Auto-React System | DM Control Only{reset}")
    print("        " + "─" * 60)
    print()

# ==================== BOT SETUP ====================
config = Config()
bot = commands.Bot(command_prefix=",", self_bot=True)

# Database connection pool
db_pool = None

# In-memory cache
targets = {}
admin_users = set()

# ==================== DATABASE FUNCTIONS ====================
async def init_database():
    """Initialize database connection and create tables"""
    global db_pool
    
    try:
        # Create connection pool
        db_pool = await asyncpg.create_pool(config.database_url)
        
        # Create tables if they don't exist
        async with db_pool.acquire() as conn:
            # Table for reaction targets
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS reaction_targets (
                    user_id BIGINT PRIMARY KEY,
                    emojis TEXT[] NOT NULL
                )
            ''')
            
            # Table for admin users
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY
                )
            ''')
        
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}[DATABASE]{reset} Connected to PostgreSQL")
        
    except Exception as e:
        print(f"[DATABASE] Error: {e}")
        raise

async def load_data_from_db():
    """Load all data from database into memory"""
    global targets, admin_users
    
    try:
        async with db_pool.acquire() as conn:
            # Load reaction targets
            rows = await conn.fetch('SELECT user_id, emojis FROM reaction_targets')
            targets = {row['user_id']: list(row['emojis']) for row in rows}
            
            # Load admins
            rows = await conn.fetch('SELECT user_id FROM admins')
            admin_users = {row['user_id'] for row in rows}
        
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}[DATABASE]{reset} Loaded {len(targets)} targets and {len(admin_users)} admins")
        
    except Exception as e:
        print(f"[DATABASE] Load error: {e}")

async def save_target(user_id: int, emojis: list):
    """Save or update a reaction target"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO reaction_targets (user_id, emojis)
                VALUES ($1, $2)
                ON CONFLICT (user_id) 
                DO UPDATE SET emojis = $2
            ''', user_id, emojis)
        
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}[DATABASE]{reset} Saved target {user_id}")
        
    except Exception as e:
        print(f"[DATABASE] Save error: {e}")

async def delete_target(user_id: int):
    """Delete a reaction target"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM reaction_targets WHERE user_id = $1', user_id)
        
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}[DATABASE]{reset} Deleted target {user_id}")
        
    except Exception as e:
        print(f"[DATABASE] Delete error: {e}")

async def clear_all_targets():
    """Clear all reaction targets"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM reaction_targets')
        
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}[DATABASE]{reset} Cleared all targets")
        
    except Exception as e:
        print(f"[DATABASE] Clear error: {e}")

async def add_admin(user_id: int):
    """Add an admin user"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO admins (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id)
        
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}[DATABASE]{reset} Added admin {user_id}")
        
    except Exception as e:
        print(f"[DATABASE] Add admin error: {e}")

async def remove_admin(user_id: int):
    """Remove an admin user"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('DELETE FROM admins WHERE user_id = $1', user_id)
        
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}[DATABASE]{reset} Removed admin {user_id}")
        
    except Exception as e:
        print(f"[DATABASE] Remove admin error: {e}")

# ==================== LOGGING ====================
def log_reaction(success: bool, user_name: str, emoji: str, reason: str = ""):
    """Log reaction attempts with timestamp"""
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    bold = "\033[1m"
    dim = "\033[2m"
    reset = "\033[0m"
    
    if success:
        print(f"{dim}[{timestamp}]{reset} {bold}✓{reset} Reacted to {user_name} with {emoji}")
    else:
        print(f"{dim}[{timestamp}]{reset} {bold}✗{reset} Failed to react to {user_name} with {emoji}: {reason}")

def is_admin(user_id: int) -> bool:
    """Check if user is master or admin"""
    return user_id == config.master_id or user_id in admin_users

async def parse_user(guild, user_str: str):
    """Parse user from mention, ID, or username"""
    # Try mention format: <@123456>
    if user_str.startswith('<@') and user_str.endswith('>'):
        try:
            user_id = int(user_str.strip('<@!>'))
            return await bot.fetch_user(user_id)
        except:
            pass
    
    # Try direct ID
    try:
        user_id = int(user_str)
        return await bot.fetch_user(user_id)
    except:
        pass
    
    # Try username (search in guild if available)
    if guild:
        for member in guild.members:
            if member.name.lower() == user_str.lower() or member.display_name.lower() == user_str.lower():
                return member
    
    # Try global search
    try:
        for guild in bot.guilds:
            for member in guild.members:
                if member.name.lower() == user_str.lower():
                    return member
    except:
        pass
    
    return None

# ==================== SAFE REACTION HELPER ====================
async def safe_add_reaction(message, emoji):
    """Safely add a reaction with error handling"""
    try:
        await message.add_reaction(emoji)
        return True
    except discord.errors.HTTPException as e:
        if e.code == 10014:  # Unknown Emoji
            print(f"[WARN] Unknown emoji: {emoji}")
            # Try alternative emoji
            try:
                await message.add_reaction("✅")
                return True
            except:
                pass
        return False
    except Exception as e:
        print(f"[WARN] Failed to add reaction: {e}")
        return False

# ==================== EVENTS ====================
@bot.event
async def on_ready():
    """Display banner and send startup DM to master"""
    if os.name == 'nt':
        os.system(f"title Cuck Bot @ {bot.user}")
    else:
        print(f"\033]0;Cuck Bot @ {bot.user}\007", end='', flush=True)
    
    print_banner()
    
    # Initialize database
    await init_database()
    await load_data_from_db()
    
    bold = "\033[1m"
    reset = "\033[0m"
    
    print(f"{bold}✓{reset} Logged in as {bot.user}")
    print(f"{bold}✓{reset} Master: User ID {config.master_id}")
    print(f"{bold}✓{reset} Admins: {len(admin_users)}")
    print(f"{bold}✓{reset} Targets: {len(targets)}")
    print(f"{bold}✓{reset} Ready | DM only mode")
    print()
    
    # Send startup DM to master
    try:
        master = await bot.fetch_user(config.master_id)
        
        admin_list = "None"
        if admin_users:
            admin_names = []
            for admin_id in admin_users:
                try:
                    admin = await bot.fetch_user(admin_id)
                    admin_names.append(f"{admin.name} (ID: {admin_id})")
                except:
                    admin_names.append(f"User {admin_id}")
            admin_list = "\n".join(f"• {name}" for name in admin_names)
        
        target_list = "None"
        if targets:
            target_names = []
            for user_id, emojis in list(targets.items())[:10]:  # Show first 10
                try:
                    user = await bot.fetch_user(user_id)
                    target_names.append(f"{user.name}: {', '.join(emojis)}")
                except:
                    target_names.append(f"User {user_id}: {', '.join(emojis)}")
            target_list = "\n".join(f"• {name}" for name in target_names)
            if len(targets) > 10:
                target_list += f"\n...and {len(targets) - 10} more"
        
        startup_msg = f"""**🟢 Cuck Bot Started**

**Admins ({len(admin_users)}):**
{admin_list}

**Active Reactions ({len(targets)}):**
{target_list}

Tag me (@{bot.user.name}) anywhere for commands
Type `help` for command list"""
        
        await master.send(startup_msg)
        print(f"{bold}[STARTUP]{reset} Sent status DM to master")
        
    except Exception as e:
        print(f"[STARTUP] Could not DM master: {e}")

@bot.event
async def on_message(message):
    # Delete own command messages
    if message.author.id == bot.user.id and message.content.startswith(","):
        await bot.process_commands(message)
        await asyncio.sleep(0.5)
        try:
            await message.delete()
        except:
            pass
        return
    
    # Admin/Master control via @mention
    if is_admin(message.author.id) and bot.user in message.mentions:
        content = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        bold = "\033[1m"
        reset = "\033[0m"
        
        # Get user's DM channel
        dm_channel = message.author.dm_channel
        if not dm_channel:
            dm_channel = await message.author.create_dm()
        
        # Master-only: add admin
        if message.author.id == config.master_id and content.startswith('addadmin '):
            parts = content.split(maxsplit=1)
            if len(parts) >= 2:
                user = await parse_user(message.guild if hasattr(message, 'guild') else None, parts[1])
                
                if user:
                    if user.id == config.master_id:
                        await safe_add_reaction(message, "⚠️")
                        await dm_channel.send("⚠️ Master already has full access")
                    elif user.id in admin_users:
                        await safe_add_reaction(message, "⚠️")
                        await dm_channel.send(f"⚠️ {user.name} is already an admin")
                    else:
                        admin_users.add(user.id)
                        await add_admin(user.id)
                        await safe_add_reaction(message, "✅")
                        await dm_channel.send(f"✅ {user.name} added as admin")
                        print(f"{bold}[MASTER]{reset} Added admin: {user.name} (ID: {user.id})")
                        
                        # DM the new admin
                        try:
                            admin_dm = user.dm_channel
                            if not admin_dm:
                                admin_dm = await user.create_dm()
                            
                            master_user = await bot.fetch_user(config.master_id)
                            await admin_dm.send(f"""**🟡 You've been promoted to Admin!**

You now have access to Cuck Bot commands.

**Available Commands:**
`@{bot.user.name} react @user 😊 👍` - Add reactions
`@{bot.user.name} stop @user` - Stop reacting
`@{bot.user.name} list` - Show targets
`@{bot.user.name} clear` - Clear all
`@{bot.user.name} help` - Show commands

**Promoted by:** {master_user.name}""")
                            print(f"{bold}[NOTIFY]{reset} Sent admin welcome DM to {user.name}")
                        except Exception as e:
                            print(f"[NOTIFY] Could not DM new admin: {e}")
                else:
                    await safe_add_reaction(message, "❌")
                    await dm_channel.send(f"❌ User not found: {parts[1]}")
            return
        
        # Master-only: remove admin
        if message.author.id == config.master_id and content.startswith('removeadmin '):
            parts = content.split(maxsplit=1)
            if len(parts) >= 2:
                user = await parse_user(message.guild if hasattr(message, 'guild') else None, parts[1])
                
                if user:
                    if user.id == config.master_id:
                        await safe_add_reaction(message, "⚠️")
                        await dm_channel.send("⚠️ Cannot remove master")
                    elif user.id in admin_users:
                        admin_users.remove(user.id)
                        await remove_admin(user.id)
                        await safe_add_reaction(message, "✅")
                        await dm_channel.send(f"✅ {user.name} removed as admin")
                        print(f"{bold}[MASTER]{reset} Removed admin: {user.name} (ID: {user.id})")
                        
                        # DM the removed admin
                        try:
                            admin_dm = user.dm_channel
                            if not admin_dm:
                                admin_dm = await user.create_dm()
                            
                            master_user = await bot.fetch_user(config.master_id)
                            await admin_dm.send(f"""**🔴 Your admin access has been revoked**

You no longer have access to Cuck Bot commands.

**Revoked by:** {master_user.name}""")
                            print(f"{bold}[NOTIFY]{reset} Sent removal notice to {user.name}")
                        except Exception as e:
                            print(f"[NOTIFY] Could not DM removed admin: {e}")
                    else:
                        await safe_add_reaction(message, "⚠️")
                        await dm_channel.send(f"⚠️ {user.name} is not an admin")
                else:
                    await safe_add_reaction(message, "❌")
                    await dm_channel.send(f"❌ User not found: {parts[1]}")
            return
        
        # Master-only: list admins
        if message.author.id == config.master_id and content == 'listadmins':
            if admin_users:
                msg_text = f"**Admins ({len(admin_users)}):**\n"
                for admin_id in admin_users:
                    try:
                        user = await bot.fetch_user(admin_id)
                        msg_text += f"• {user.name} (ID: {admin_id})\n"
                    except:
                        msg_text += f"• User {admin_id}\n"
                
                master_user = await bot.fetch_user(config.master_id)
                msg_text += f"\n**Master:** {master_user.name} (ID: {config.master_id})"
            else:
                master_user = await bot.fetch_user(config.master_id)
                msg_text = f"⚠️ No admins\n**Master:** {master_user.name} (ID: {config.master_id})"
            
            await safe_add_reaction(message, "✅")
            await dm_channel.send(msg_text)
            return
        
        # Admin: add reactions
        if content.startswith('react '):
            parts = content.split()
            if len(parts) >= 3:
                user = await parse_user(message.guild if hasattr(message, 'guild') else None, parts[1])
                emojis = parts[2:]
                
                if user:
                    # Prevent admins from adding reactions to master
                    if user.id == config.master_id and message.author.id != config.master_id:
                        await safe_add_reaction(message, "⚠️")
                        await dm_channel.send("⚠️ Admins cannot add reactions to Master")
                        return
                    
                    if user.id not in targets:
                        targets[user.id] = []
                    
                    targets[user.id].extend(emojis)
                    await save_target(user.id, targets[user.id])
                    await safe_add_reaction(message, "✅")
                    await dm_channel.send(f"✅ Added reactions {', '.join(emojis)} for {user.name}")
                    print(f"{bold}[ADMIN]{reset} Added reactions {', '.join(emojis)} for {user.name}")
                else:
                    await safe_add_reaction(message, "❌")
                    await dm_channel.send(f"❌ User not found: {parts[1]}")
            return
        
        # Admin: stop reactions
        if content.startswith('stop '):
            parts = content.split(maxsplit=1)
            if len(parts) >= 2:
                user = await parse_user(message.guild if hasattr(message, 'guild') else None, parts[1])
                
                if user:
                    if user.id in targets:
                        targets.pop(user.id)
                        await delete_target(user.id)
                        await safe_add_reaction(message, "✅")
                        await dm_channel.send(f"✅ Stopped reacting to {user.name}")
                        print(f"{bold}[ADMIN]{reset} Stopped reacting to {user.name}")
                    else:
                        await safe_add_reaction(message, "⚠️")
                        await dm_channel.send(f"⚠️ Not reacting to {user.name}")
                else:
                    await safe_add_reaction(message, "❌")
                    await dm_channel.send(f"❌ User not found: {parts[1]}")
            return
        
        # Admin: clear all
        if content == 'clear':
            targets.clear()
            await clear_all_targets()
            await safe_add_reaction(message, "✅")
            await dm_channel.send("✅ Cleared all reaction targets")
            print(f"{bold}[ADMIN]{reset} Cleared all targets")
            return
        
        # Admin: list targets
        if content == 'list':
            if targets:
                msg_text = f"**Active Targets ({len(targets)}):**\n"
                for user_id, emojis in list(targets.items())[:20]:
                    try:
                        user = await bot.fetch_user(user_id)
                        msg_text += f"• {user.name}: {', '.join(emojis)}\n"
                    except:
                        msg_text += f"• User {user_id}: {', '.join(emojis)}\n"
                
                if len(targets) > 20:
                    msg_text += f"\n...and {len(targets) - 20} more"
                
                await safe_add_reaction(message, "✅")
                await dm_channel.send(msg_text)
            else:
                await safe_add_reaction(message, "✅")
                await dm_channel.send("⚠️ No active targets")
            return
        
        # Help command
        if content.lower() in ['help', 'cmds', 'commands']:
            if message.author.id == config.master_id:
                help_text = f"""**Cuck Bot Commands**
**Your Role:** 🔴 Master

**Admin Commands:**
`react @user 😊 👍` - Add reactions
`stop @user` - Stop reacting
`list` - Show targets
`clear` - Clear all

**Master Only:**
`addadmin @user` - Add admin
`removeadmin @user` - Remove admin
`listadmins` - Show admins

Tag me anywhere: @bot <command>
Accepts: @mention, username, or ID"""
            else:
                help_text = f"""**Cuck Bot Commands**
**Your Role:** 🟡 Admin

**Available to you:**
`react @user 😊 👍` - Add reactions
`stop @user` - Stop reacting
`list` - Show targets
`clear` - Clear all

**Note:** You cannot add reactions to the Master
**Note:** You cannot add/remove other admins

Tag me anywhere: @bot <command>
Accepts: @mention, username, or ID"""
            
            await safe_add_reaction(message, "✅")
            await dm_channel.send(help_text)
            return
    
    # Auto-react to targeted users
    if message.author.id in targets:
        for emoji in targets[message.author.id]:
            try:
                await message.add_reaction(emoji)
                log_reaction(True, message.author.name, emoji)
            except Exception as e:
                log_reaction(False, message.author.name, emoji, str(e))
    
    await bot.process_commands(message)

# ==================== COMMANDS (purge only) ====================
@bot.command(aliases=['prune'])
async def purge(ctx, amount: int):
    """Delete your messages from current channel"""
    if amount <= 0:
        return
    
    if amount > 100:
        amount = 100
    
    def is_me(m):
        return m.author.id == bot.user.id
    
    try:
        deleted_count = 0
        
        if isinstance(ctx.channel, discord.DMChannel):
            async for message in ctx.channel.history(limit=amount):
                if is_me(message):
                    try:
                        await message.delete()
                        deleted_count += 1
                        await asyncio.sleep(0.3)
                    except:
                        pass
        else:
            deleted = await ctx.channel.purge(limit=amount, check=is_me)
            deleted_count = len(deleted)
        
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}[PURGE]{reset} Deleted {deleted_count} messages")
        
    except Exception as e:
        print(f"[PURGE] Error: {e}")

# ==================== RUN ====================
if __name__ == "__main__":
    try:
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"{bold}Starting Cuck Bot...{reset}")
        bot.run(config.token)
    except discord.LoginFailure:
        print("❌ Invalid token")
    except Exception as e:
        print(f"❌ Error: {e}")
