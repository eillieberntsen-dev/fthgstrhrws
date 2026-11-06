import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1568277964762648657
TICKET_CATEGORY_ID = 1568291291480072313

STAFF_ROLES = [
    1568292371035193496,
    1568292367755116615,
    1568292377725247550,
    1568295300613939460,
]

MODERATOR_ROLES = [
    1568292371035193496,
    1568292367755116615,
]

SCAMMER_ROLE_ID = 1568292380862583045
RATTER_ROLE_ID  = 1568292391197085816

MAX_TICKETS = 2
PING_COOLDOWN_SECONDS = 86400  # 24 hours

DATA_FILE = "bot_data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"tickets": {}, "ping_cooldowns": {}}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def has_staff_role():
    async def predicate(interaction: discord.Interaction):
        return any(role.id in STAFF_ROLES for role in interaction.user.roles)
    return app_commands.check(predicate)


def has_mod_role():
    async def predicate(interaction: discord.Interaction):
        return any(role.id in MODERATOR_ROLES for role in interaction.user.roles)
    return app_commands.check(predicate)


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open a Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        guild = interaction.guild
        user = interaction.user

        user_tickets = [
            ch_id for ch_id, info in data["tickets"].items()
            if info.get("user_id") == user.id
        ]

        if len(user_tickets) >= MAX_TICKETS:
            await interaction.response.send_message(
                f"❌ You already have {MAX_TICKETS} open tickets. Please wait for one to be closed.",
                ephemeral=True
            )
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if category is None:
            await interaction.response.send_message("❌ Ticket category not found.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        for role_id in STAFF_ROLES:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites,
        )

        data["tickets"][str(channel.id)] = {"user_id": user.id, "channel_name": channel.name}
        save_data(data)

        embed = discord.Embed(
            title="🎫 Ticket Opened",
            description=f"Hey {user.mention}! Support will be with you shortly.\n\nDescribe your issue and a staff member will assist you.",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Paster Heaven Support")
        await channel.send(embed=embed)

        await interaction.response.send_message(
            f"✅ Your ticket has been created: {channel.mention}", ephemeral=True
        )


@tree.command(name="ticket-panel", description="Send the support ticket panel", guild=discord.Object(id=GUILD_ID))
@has_staff_role()
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(color=0x5865F2)
    embed.title = "Paster Heaven Support"
    embed.description = (
        "-# Top provider for multible Sources with undetected futures\n\n"
        "❓ **How can we help?**\n"
        "Pick the category that fits your request and the right team will pick it up.\n\n"
        "📌  **Before you open a ticket**\n"
        "<a:51047animatedarrowwhite:1568294336876257300> Read the terms in <#1568284830297358366> before you open a ticket.\n"
        "<a:51047animatedarrowwhite:1568294336876257300> Pick the category that matches your request."
    )
    view = TicketPanelView()
    await interaction.response.send_message(embed=embed, view=view)


@tree.command(name="channel-create", description="Create a channel for a user", guild=discord.Object(id=GUILD_ID))
@has_staff_role()
@app_commands.describe(user="The user to create a channel for", name="Channel name")
async def channel_create(interaction: discord.Interaction, user: discord.Member, name: str):
    guild = interaction.guild
    category = guild.get_channel(TICKET_CATEGORY_ID)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    for role_id in STAFF_ROLES:
        role = guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )

    channel = await guild.create_text_channel(
        name=f"🌐┃{name}",
        category=category,
        overwrites=overwrites,
    )

    await interaction.response.send_message(f"✅ Channel created: {channel.mention}", ephemeral=True)


@tree.command(name="channel-ping", description="Ping @here in your channel (once per 24 hours)", guild=discord.Object(id=GUILD_ID))
async def channel_ping(interaction: discord.Interaction):
    data = load_data()
    user_id = str(interaction.user.id)
    now = time.time()

    last_ping = data["ping_cooldowns"].get(user_id, 0)
    elapsed = now - last_ping
    remaining = PING_COOLDOWN_SECONDS - elapsed

    if elapsed < PING_COOLDOWN_SECONDS:
        reset_ts = int(last_ping + PING_COOLDOWN_SECONDS)
        await interaction.response.send_message(
            f"⏳ 24 Hours Haven't Gone — <t:{reset_ts}:R> left",
            ephemeral=True
        )
        return

    data["ping_cooldowns"][user_id] = now
    save_data(data)

    await interaction.response.send_message(f"@here — pinged by {interaction.user.mention}")


@tree.command(name="scammer-alert", description="Report a scammer or ratter", guild=discord.Object(id=GUILD_ID))
@has_mod_role()
@app_commands.describe(
    user="The user to report",
    reason="Reason: Scamming or Ratting"
)
@app_commands.choices(reason=[
    app_commands.Choice(name="Scamming", value="scamming"),
    app_commands.Choice(name="Ratting", value="ratting"),
])
async def scammer_alert(interaction: discord.Interaction, user: discord.Member, reason: app_commands.Choice[str]):
    guild = interaction.guild

    if reason.value == "scamming":
        role = guild.get_role(SCAMMER_ROLE_ID)
        label = "Scammer"
        color = discord.Color.red()
    else:
        role = guild.get_role(RATTER_ROLE_ID)
        label = "Ratter"
        color = discord.Color.orange()

    if role is None:
        await interaction.response.send_message("❌ Role not found.", ephemeral=True)
        return

    await user.add_roles(role, reason=f"Reported by {interaction.user} for {reason.value}")

    embed = discord.Embed(
        title=f"🚨 Scammer Alert — {label}",
        description=f"{user.mention} has been flagged as a **{label}**.\n**Reported by:** {interaction.user.mention}",
        color=color
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@tree.command(name="ticket-purge", description="Delete all active tickets", guild=discord.Object(id=GUILD_ID))
@has_staff_role()
async def ticket_purge(interaction: discord.Interaction):
    data = load_data()
    guild = interaction.guild
    deleted = 0

    await interaction.response.defer(ephemeral=True)

    for ch_id in list(data["tickets"].keys()):
        channel = guild.get_channel(int(ch_id))
        if channel:
            await channel.delete(reason="Ticket purge")
            deleted += 1
        del data["tickets"][ch_id]

    save_data(data)
    await interaction.followup.send(f"✅ Purged {deleted} ticket(s).", ephemeral=True)


@tree.command(name="ticket-rename", description="Rename the current ticket channel", guild=discord.Object(id=GUILD_ID))
@has_staff_role()
@app_commands.describe(name="New name for this ticket")
async def ticket_rename(interaction: discord.Interaction, name: str):
    data = load_data()
    channel = interaction.channel

    if str(channel.id) not in data["tickets"]:
        await interaction.response.send_message("❌ This command can only be used inside a ticket channel.", ephemeral=True)
        return

    safe_name = name.lower().replace(" ", "-")[:100]
    await channel.edit(name=safe_name)

    data["tickets"][str(channel.id)]["channel_name"] = safe_name
    save_data(data)

    await interaction.response.send_message(f"✅ Ticket renamed to `{safe_name}`.")


@bot.event
async def on_ready():
    bot.add_view(TicketPanelView())
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Logged in as {bot.user} — commands synced.")


bot.run(TOKEN)
