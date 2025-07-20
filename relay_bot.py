import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", 0))
ANONYMOUS_CHANNEL_IDS = list(map(int, os.getenv("ANONYMOUS_CHANNEL_IDS", "").split(",")))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

relay_owner_id = None
last_post_time = {}
POST_INTERVAL = 300
MAX_LENGTH = 100

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}")

@bot.command(name="start")
async def start(ctx):
    global relay_owner_id

    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return await ctx.send("⚠️ このチャンネルではBOTを起動できません。")

    if relay_owner_id is not None:
        return await ctx.send(f"⚠️ BOTは既に <@{relay_owner_id}> さんによって起動されています。")

    relay_owner_id = ctx.author.id
    await ctx.send(f"🚀 {ctx.author.mention} さんがBOTを起動しました！")

@bot.command(name="end")
async def end(ctx):
    global relay_owner_id

    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return await ctx.send("⚠️ このチャンネルではBOTを停止できません。")

    if relay_owner_id is None:
        return await ctx.send("⚠️ BOTは現在起動していません。")

    if ctx.author.id == relay_owner_id:
        relay_owner_id = None
        await ctx.send(f"🛑 {ctx.author.mention} さんがBOTを停止させました。")
    else:
        await ctx.send(f"🚫 {ctx.author.mention} さんには停止権限がありません。起動者は <@{relay_owner_id}> さんです。")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id not in ANONYMOUS_CHANNEL_IDS:
        return

    now = message.created_at.timestamp()
    user_id = message.author.id
    if user_id in last_post_time and now - last_post_time[user_id] < POST_INTERVAL:
        return await message.channel.send(f"⚠️ 5分間隔での投稿が必要です。")

    if len(message.content) > MAX_LENGTH:
        return await message.channel.send(f"⚠️ 投稿は{MAX_LENGTH}文字以内にしてください。")

    try:
        await message.delete()
        await message.channel.send(f"📩 **名も無き作家**より：\n> {message.content}")
        last_post_time[user_id] = now
    except Exception as e:
        print(f"❌ 投稿エラー: {e}")

bot.run(TOKEN)
