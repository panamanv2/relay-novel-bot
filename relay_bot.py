import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import time

load_dotenv()

TOKEN = os.getenv("TOKEN")
ALLOWED_THREAD_IDS = list(map(int, os.getenv("ANONYMOUS_CHANNEL_IDS", "").split(",")))

MAX_LENGTH = 100
COOLDOWN_SECONDS = 300

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
relay_owner_id = None
last_post_time = {}
message_counter = 0

@bot.event
async def on_ready():
    print(f"✅ Bot is ready: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print("❌ Slash command sync failed:", e)

# スラッシュコマンド：起動
@bot.tree.command(name="start", description="Botを起動します")
async def start(interaction: discord.Interaction):
    global relay_owner_id
    if interaction.channel_id not in ALLOWED_THREAD_IDS:
        await interaction.response.send_message("⚠️ このスレッドではBotを起動できません。", ephemeral=True)
        return

    if relay_owner_id is not None:
        await interaction.response.send_message(f"⚠️ すでに <@{relay_owner_id}> さんが起動しています。", ephemeral=True)
        return

    relay_owner_id = interaction.user.id
    await interaction.response.send_message(f"🚀 {interaction.user.mention} さんがBotを起動しました！")

# スラッシュコマンド：停止
@bot.tree.command(name="end", description="Botを停止します")
async def end(interaction: discord.Interaction):
    global relay_owner_id
    if interaction.channel_id not in ALLOWED_THREAD_IDS:
        await interaction.response.send_message("⚠️ このスレッドではBotを停止できません。", ephemeral=True)
        return

    if relay_owner_id != interaction.user.id:
        await interaction.response.send_message(f"🚫 あなたは起動者ではありません。起動者：<@{relay_owner_id}>", ephemeral=True)
        return

    relay_owner_id = None
    await interaction.response.send_message(f"🛑 {interaction.user.mention} さんがBotを停止しました。")

# 匿名投稿メッセージ受信
@bot.event
async def on_message(message):
    global message_counter

    if message.author == bot.user or message.guild is None:
        return

    if message.channel.id not in ALLOWED_THREAD_IDS:
        return

    if relay_owner_id is None:
        await message.channel.send("⚠️ Botが起動していません。")
        return

    user_id = message.author.id
    now = time.time()

    if user_id in last_post_time and now - last_post_time[user_id] < COOLDOWN_SECONDS:
        remaining = int(COOLDOWN_SECONDS - (now - last_post_time[user_id]))
        await message.channel.send(f"⏳ あと {remaining} 秒後に投稿できます。")
        return

    if len(message.content) > MAX_LENGTH:
        await message.channel.send(f"⚠️ 文字数は最大{MAX_LENGTH}文字です。")
        return

    try:
        await message.delete()
    except Exception:
        pass

    message_counter += 1
    await message.channel.send(f"📝【No.{message_counter}】\n{message.content}")
    last_post_time[user_id] = now

bot.run(TOKEN)
