import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
import threading
from utils import check_ban

app = Flask(__name__)

load_dotenv()
APPLICATION_ID = os.getenv("APPLICATION_ID")
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DEFAULT_LANG = "en"
user_languages = {}
allowed_check_channels = set()  # قنوات مسموحة
nomBot = "None"

@app.route('/')
def home():
    global nomBot
    return f"Bot {nomBot} is working"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_flask).start()

@bot.event
async def on_ready():
    global nomBot
    nomBot = f"{bot.user}"
    print(f"Le bot est connecté en tant que {bot.user}")

# -------------------------------
# أوامر الأدمن للتحكم بالقنوات
# -------------------------------
@bot.command(name="setcheckchannel")
@commands.has_permissions(administrator=True)
async def set_check_channel(ctx, channel: discord.TextChannel):
    allowed_check_channels.add(channel.id)
    await ctx.send(f"✅ الأمر check مسموح الآن في {channel.mention}")

@bot.command(name="removecheckchannel")
@commands.has_permissions(administrator=True)
async def remove_check_channel(ctx, channel: discord.TextChannel):
    if channel.id in allowed_check_channels:
        allowed_check_channels.remove(channel.id)
        await ctx.send(f"❌ الأمر check لم يعد مسموح في {channel.mention}")
    else:
        await ctx.send("⚠️ هذا الشات مو مضاف أصلاً.")

@bot.command(name="checkchannels")
@commands.has_permissions(administrator=True)
async def list_check_channels(ctx):
    if not allowed_check_channels:
        await ctx.send("⚠️ مافي قنوات مسموح فيها حالياً.")
    else:
        ch_list = [f"<#{cid}>" for cid in allowed_check_channels]
        await ctx.send("📌 القنوات المسموح بها:\n" + "\n".join(ch_list))

# -------------------------------
# الأمر check (Hybrid Command)
# -------------------------------
@bot.hybrid_command(name="check", description="Check Free Fire account ban status")
@commands.cooldown(1, 5, commands.BucketType.user)  # كوول داون 5 ثواني
async def check(ctx, user_id: str):
    lang = user_languages.get(ctx.author.id, "en")

    # تحقق من القناة
    if ctx.channel.id not in allowed_check_channels:
        await ctx.send("⚠️ هذا الأمر غير مسموح في هذا الشات.", ephemeral=True)
        return

    if not user_id.isdigit():
        message = {
            "en": f"{ctx.author.mention} ❌ **Invalid UID!**\n➡️ Please use: `!check 123456789`",
            "fr": f"{ctx.author.mention} ❌ **UID invalide !**\n➡️ Veuillez fournir un UID valide sous la forme : `!check 123456789`"
        }
        await ctx.send(message[lang])
        return

    # رسالة "Processing..."
    processing_msg = await ctx.send("⏳ Processing, please wait ...")

    try:
        ban_status = await check_ban(user_id)
    except Exception as e:
        await processing_msg.edit(content=f"{ctx.author.mention} ⚠️ Error:\n```{str(e)}```")
        return

    if ban_status is None:
        message = {
            "en": f"{ctx.author.mention} ❌ **Could not get information. Please try again later.**",
            "fr": f"{ctx.author.mention} ❌ **Impossible d'obtenir les informations.**\nVeuillez réessayer plus tard."
        }
        await processing_msg.edit(content=message[lang])
        return

    # -------------------------------
    # نفس الـ Embed القديم (ما غيرته)
    # -------------------------------
    is_banned = int(ban_status.get("is_banned", 0))
    period = ban_status.get("period", "N/A")
    nickname = ban_status.get("nickname", "NA")
    region = ban_status.get("region", "N/A")
    id_str = f"{user_id}"

    if isinstance(period, int):
        period_str = f"more than {period} months" if lang == "en" else f"plus de {period} mois"
    else:
        period_str = "unavailable" if lang == "en" else "indisponible"

    embed = discord.Embed(
        color=0xFF0000 if is_banned else 0x00FF00,
        timestamp=ctx.message.created_at
    )

    if is_banned:
        embed.title = "**▌ Banned Account 🛑 **" if lang == "en" else "**▌ Compte banni 🛑 **"
        embed.description = (
            f"**• {'Reason' if lang == 'en' else 'Raison'} :** "
            f"{'This account was confirmed for using cheats.' if lang == 'en' else 'Ce compte a été confirmé comme utilisant des hacks.'}\n"
            f"**• {'Suspension duration' if lang == 'en' else 'Durée de la suspension'} :** {period_str}\n"
            f"**• {'Nickname' if lang == 'en' else 'Pseudo'} :** {nickname}\n"
            f"**• {'Player ID' if lang == 'en' else 'ID du joueur'} :** {id_str}\n"
            f"**• {'Region' if lang == 'en' else 'Région'} :** {region}"
        )
        file = discord.File("assets/banned.gif", filename="banned.gif")
        embed.set_image(url="attachment://banned.gif")
    else:
        embed.title = "**▌ Clean Account ✅ **" if lang == "en" else "**▌ Compte non banni ✅ **"
        embed.description = (
            f"**• {'Status' if lang == 'en' else 'Statut'} :** "
            f"{'No sufficient evidence of cheat usage on this account.' if lang == 'en' else 'Aucune preuve suffisante pour confirmer l’utilisation de hacks sur ce compte.'}\n"
            f"**• {'Nickname' if lang == 'en' else 'Pseudo'} :** {nickname}\n"
            f"**• {'Player ID' if lang == 'en' else 'ID du joueur'} :** {id_str}\n"
            f"**• {'Region' if lang == 'en' else 'Région'} :** {region}"
        )
        file = discord.File("assets/notbanned.gif", filename="notbanned.gif")
        embed.set_image(url="attachment://notbanned.gif")

    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    embed.set_footer(text="DEVELOPED BY dArk•")

    # تعديل رسالة "Processing..." للـ Embed
    await processing_msg.edit(content=f"{ctx.author.mention}", embed=embed, attachments=[file])

# كول داون Error handler
@check.error
async def check_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⚠️ استنى {round(error.retry_after, 1)} ثانية قبل ما تستخدم الأمر مرة ثانية.", ephemeral=True)
    else:
        raise error

bot.run(TOKEN)
        f.write(str(channel_id))

ALLOWED_CHANNEL_ID = get_allowed_channel()

@app.route('/')
def home():
    global nomBot
    return f"Bot {nomBot} is working"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_flask).start()

@bot.event
async def on_ready():
    global nomBot
    nomBot = f"{bot.user}"
    print(f"Le bot est connecté en tant que {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

# ================== FUNCTION CORE ==================
async def run_check(interaction_or_ctx, uid: str, lang="en", is_slash=False):
    global ALLOWED_CHANNEL_ID

    # تحقق من القناة
    if ALLOWED_CHANNEL_ID and (
        (is_slash and interaction_or_ctx.channel.id != ALLOWED_CHANNEL_ID) or
        (not is_slash and interaction_or_ctx.channel.id != ALLOWED_CHANNEL_ID)
    ):
        msg = f"{interaction_or_ctx.user.mention if is_slash else interaction_or_ctx.author.mention} ❌ You cannot use this command in this channel."
        if is_slash:
            await interaction_or_ctx.response.send_message(msg, ephemeral=True)
        else:
            await interaction_or_ctx.send(msg, delete_after=10)
        return

    if not uid.isdigit():
        message = {
            "en": f"❌ Invalid UID!\n➡️ Use: `!check 123456789` or `/check 123456789`",
            "fr": f"❌ UID invalide !\n➡️ Utilisez : `!check 123456789` ou `/check 123456789`"
        }
        if is_slash:
            await interaction_or_ctx.response.send_message(message[lang], ephemeral=True)
        else:
            await interaction_or_ctx.send(message[lang])
        return

    if is_slash:
        await interaction_or_ctx.response.defer(thinking=True)
    else:
        wait_msg = await interaction_or_ctx.send("⏳ Processing, please wait ...")

    try:
        ban_status = await check_ban(uid)
    except Exception as e:
        msg = f"⚠️ Error:\n```{str(e)}```"
        if is_slash:
            await interaction_or_ctx.followup.send(msg)
        else:
            await wait_msg.edit(content=msg)
        return

    if ban_status is None:
        msg = {
            "en": "❌ Could not get information. Try again later.",
            "fr": "❌ Impossible d'obtenir les informations. Réessayez plus tard."
        }
        if is_slash:
            await interaction_or_ctx.followup.send(msg[lang])
        else:
            await wait_msg.edit(content=msg[lang])
        return

    is_banned = int(ban_status.get("is_banned", 0))
    period = ban_status.get("period", "N/A")
    nickname = ban_status.get("nickname", "NA")
    region = ban_status.get("region", "N/A")
    id_str = f"`{uid}`"

    if isinstance(period, int):
        period_str = f"more than {period} months" if lang == "en" else f"plus de {period} mois"
    else:
        period_str = "unavailable" if lang == "en" else "indisponible"

    embed = discord.Embed(
        color=0xFF0000 if is_banned else 0x00FF00
    )

    if is_banned:
        embed.title = "▌ Banned Account 🛑" if lang == "en" else "▌ Compte banni 🛑"
        embed.description = (
            f"**Reason:** {'Cheats detected.' if lang == 'en' else 'Hacks détectés.'}\n"
            f"**Duration:** {period_str}\n"
            f"**Nickname:** `{nickname}`\n"
            f"**Player ID:** {id_str}\n"
            f"**Region:** `{region}`"
        )
        file = discord.File("assets/banned.gif", filename="banned.gif")
        embed.set_image(url="attachment://banned.gif")
    else:
        embed.title = "▌ Clean Account ✅" if lang == "en" else "▌ Compte non banni ✅"
        embed.description = (
            f"**Status:** {'No evidence of cheats.' if lang == 'en' else 'Aucune preuve de hacks.'}\n"
            f"**Nickname:** `{nickname}`\n"
            f"**Player ID:** {id_str}\n"
            f"**Region:** `{region}`"
        )
        file = discord.File("assets/notbanned.gif", filename="notbanned.gif")
        embed.set_image(url="attachment://notbanned.gif")

    embed.set_thumbnail(url=interaction_or_ctx.user.avatar.url if is_slash else interaction_or_ctx.author.avatar.url)
    embed.set_footer(text="DEVELOPED BY dArk•")

    if is_slash:
        await interaction_or_ctx.followup.send(embed=embed, file=file)
    else:
        await wait_msg.delete()
        await interaction_or_ctx.send(embed=embed, file=file)

# ============== TEXT COMMAND ==============
@bot.command(name="check")
async def check_cmd(ctx, uid: str):
    lang = user_languages.get(ctx.author.id, "en")
    await run_check(ctx, uid, lang, is_slash=False)

# ============== SLASH COMMAND ==============
@bot.tree.command(name="check", description="Check if a UID is banned")
async def check_slash(interaction: discord.Interaction, uid: str):
    lang = user_languages.get(interaction.user.id, "en")
    await run_check(interaction, uid, lang, is_slash=True)

# ============== SET CHANNEL COMMANDS ==============
@bot.command(name="setchannel")
@commands.has_permissions(administrator=True)
async def set_channel_cmd(ctx):
    global ALLOWED_CHANNEL_ID
    ALLOWED_CHANNEL_ID = ctx.channel.id
    set_allowed_channel(ALLOWED_CHANNEL_ID)
    await ctx.send(f"✅ Commands restricted to this channel: {ctx.channel.mention}")

@bot.tree.command(name="setchannel", description="Restrict commands to this channel (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def set_channel_slash(interaction: discord.Interaction):
    global ALLOWED_CHANNEL_ID
    ALLOWED_CHANNEL_ID = interaction.channel.id
    set_allowed_channel(ALLOWED_CHANNEL_ID)
    await interaction.response.send_message(
        f"✅ Commands restricted to this channel: {interaction.channel.mention}"
    )
