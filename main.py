import os
import time
import requests
import discord
from discord.ext import commands, tasks
from discord import app_commands

# ================== SECRETS ==================
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
ERLC_API_KEY = os.environ["ERLC_API_KEY"]

# ================== ER:LC API ==================
ERLC_BASE_URL = "https://api.policeroleplay.community/v1"
HEADERS = {"Server-Key": ERLC_API_KEY}

def get_server_data():
    try:
        server = requests.get(f"{ERLC_BASE_URL}/server", headers=HEADERS)
        players = requests.get(f"{ERLC_BASE_URL}/server/players", headers=HEADERS)

        if server.status_code != 200 or players.status_code != 200:
            print(f"ER:LC API error: server={server.status_code}, players={players.status_code}")
            return None

        return {"server": server.json(), "players": players.json()}
    except Exception as e:
        print("Error fetching ER:LC data:", e)
        return None

# ================== BOT SETUP ==================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================== UTILS ==================
def get_staff_details(players):
    staff_list = []
    for p in players:
        perm = p.get("PermissionLevel", "Civilian")
        if perm != "Civilian":
            role = perm if perm in ["Moderator", "Admin", "Co-Owner"] else "Staff"
            staff_list.append(f"• **{p.get('Player', 'Unknown')}** ({role})")
    return "\n".join(staff_list) if staff_list else "No staff online."

# ================== EMBED FUNCTION ==================
def create_session_embed(data):
    server = data["server"]
    players = data["players"]
    current_players = server.get("CurrentPlayers", 0)
    max_players = server.get("MaxPlayers", 0)
    queue = server.get("QueuePlayers", 0)
    active_staff = sum(1 for p in players if p.get("PermissionLevel", "Civilian") != "Civilian")
    timestamp = int(time.time())

    embed = discord.Embed(
        title="<:image_20260115_172643193:1461471690092449905> Session Status",
        description=(
            "> Welcome to our Sessions Channel! Here will show the status of\n"
            "> the In-game Playercount, Active Staff and Queue.\n\n"
            f"• Server Name: {server.get('Name', 'Tennessee State Roleplay | Realistic | Strict')}\n"
            f"• Server Code: {server.get('JoinKey', 'TNMETRO')}\n"
            "• Server Owner: Vyncemanden"
        ),
        color=0x2b2d31
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1461066463438831830/1461466290605789459/SESSION.png")
    embed.add_field(name="<:image_20260115_172829941:1461472139109470461> In-Game Status", value=f"**Last Updated:** <t:{timestamp}:R>", inline=False)
    embed.add_field(name="Player Count", value=f"```\n{current_players}/{max_players}\n```", inline=True)
    embed.add_field(name="Active Staff", value=f"```\n{active_staff}\n```", inline=True)
    embed.add_field(name="In Queue", value=f"```\n{queue}\n```", inline=True)
    return embed

# ================== AUTO-UPDATE TASK ==================
active_session_messages = {}

@tasks.loop(minutes=1)
async def update_sessions():
    for msg_id, channel_id in list(active_session_messages.items()):
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        try:
            message = await channel.fetch_message(msg_id)
            data = get_server_data()
            if data:
                embed = create_session_embed(data)
                await message.edit(embed=embed)
        except Exception as e:
            print(f"Error updating message {msg_id}: {e}")
            del active_session_messages[msg_id]

# ================== SESSION MANAGEMENT ==================
ALLOWED_ROLE_ID = 1461009685149782102
session_start_time = None
session_msg_id = None

class SessionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.start_button = discord.ui.Button(label="Start", style=discord.ButtonStyle.green, custom_id="session_start")
        self.start_button.callback = self.start_callback
        self.add_item(self.start_button)

    async def start_callback(self, interaction: discord.Interaction):
        global session_start_time, session_msg_id
        member = interaction.user
        if not hasattr(member, "roles") or not any(role.id == ALLOWED_ROLE_ID for role in member.roles):
            await interaction.response.send_message("❌ You do not have permission to start a session.", ephemeral=True)
            return

        session_start_time = time.time()
        
        embed = discord.Embed(
            title="<:image_20260115_172643193:1461471690092449905> Session has started!",
            description=(
                "> Session has started you are free you join.\n"
                "> Please ensure you follow all rules and have fun roleplaying!"
            ),
            color=0x2b2d31
        )
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1461066463438831830/1461466290605789459/SESSION.png")
        
        embed.add_field(name="Status", value="```\nSTARTED\n```", inline=True)
        embed.add_field(name="Staff on Site", value=f"```\n{member.display_name}\n```", inline=True)

        self.clear_items()
        end_button = discord.ui.Button(label="End", style=discord.ButtonStyle.red, custom_id="session_end")
        end_button.callback = self.end_callback
        self.add_item(end_button)

        if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            msg = await interaction.channel.send(embed=embed, view=self)
            session_msg_id = msg.id
        await interaction.response.edit_message(view=None)

    async def end_callback(self, interaction: discord.Interaction):
        global session_start_time, session_msg_id
        member = interaction.user
        if not hasattr(member, "roles") or not any(role.id == ALLOWED_ROLE_ID for role in member.roles):
            await interaction.response.send_message("❌ You do not have permission to end a session.", ephemeral=True)
            return

        duration = "Unknown"
        if session_start_time:
            elapsed = int(time.time() - session_start_time)
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration = f"{hours}h {minutes}m {seconds}s"
            session_start_time = None

        embed = discord.Embed(
            title="Session Shutdown!",
            description=(
                "> The Server Has now been shutdown, Please wait for for we\n"
                "> host another session very soon aswell please don't be In-game\n"
                "> while the session is down."
            ),
            color=0x2b2d31
        )
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1461066463438831830/1461466290605789459/SESSION.png")
        if duration != "Unknown":
            embed.add_field(name="Session Duration", value=f"```\n{duration}\n```", inline=False)

        if session_msg_id and isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            try:
                msg = await interaction.channel.fetch_message(session_msg_id)
                await msg.edit(embed=embed, view=None)
                await interaction.response.send_message("✅ Session ended successfully.", ephemeral=True)
            except:
                await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.edit_message(embed=embed, view=None)
        
        session_msg_id = None

# ================== READY ==================
@bot.event
async def on_ready():
    await bot.tree.sync()
    bot.add_view(SessionView())
    if not update_sessions.is_running():
        update_sessions.start()
    print(f"Logged in as {bot.user}")

# ================== SLASH COMMANDS ==================
@bot.tree.command(name="session", description="Post ER:LC session status embed")
async def session(interaction: discord.Interaction):
    if not hasattr(interaction.user, "roles") or not any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    data = get_server_data()
    if not data:
        await interaction.followup.send("❌ Failed to fetch ER:LC data.", ephemeral=True)
        return
        
    embed = create_session_embed(data)
    if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
        msg = await interaction.channel.send(embed=embed, view=SessionView())
        active_session_messages[msg.id] = interaction.channel.id
        await interaction.followup.send("✅ Session embed posted!", ephemeral=True)

@bot.tree.command(name="command", description="Execute a command with input")
@app_commands.describe(command="The command name", input="The input for the command")
async def command(interaction: discord.Interaction, command: str, input: str):
    await interaction.response.send_message(f"✅ Command `{command}` executed with input: `{input}`", ephemeral=True)

@bot.tree.command(name="erlcheck", description="Show detailed server and staff status")
async def erlcheck(interaction: discord.Interaction):
    await interaction.response.defer()
    data = get_server_data()
    if not data:
        await interaction.followup.send("❌ Failed to fetch ER:LC data.")
        return
    
    server = data["server"]
    players = data["players"]
    timestamp = int(time.time())
    staff_info = get_staff_details(players)
    
    embed = discord.Embed(
        title="<:image_20260115_172829941:1461472139109470461> Server Status Check",
        description=(
            "> Current live look at the server status and active staff members.\n"
            "> High quality roleplay is our top priority!"
        ),
        color=0x2b2d31
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1461066463438831830/1461466290605789459/SESSION.png")
    embed.add_field(name="Players", value=f"```\n{server.get('CurrentPlayers', 0)}/{server.get('MaxPlayers', 0)}\n```", inline=True)
    embed.add_field(name="In Queue", value=f"```\n{server.get('QueuePlayers', 0)}\n```", inline=True)
    embed.add_field(name="Staff Online", value=staff_info, inline=False)
    embed.add_field(name="Last Updated", value=f"<t:{timestamp}:R>", inline=False)
    await interaction.followup.send(embed=embed)

# ================== RUN ==================
bot.run(DISCORD_TOKEN)
