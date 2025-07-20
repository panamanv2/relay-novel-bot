import os
import discord
from discord.ext import commands
import time
import logging

# トークン取得（.envを使わずRenderの環境変数から直接取得）
TOKEN = os.environ["DISCORD_BOT_TOKEN"]
print("DEBUG: TOKEN =", TOKEN[:10])  # ← 確認用（先頭10文字だけ）

# ログ設定
logging.basicConfig(level=logging.INFO)

# コマンド実行許可チャンネルID
ALLOWED_CHANNEL_ID = 1393506261294911639  # 実際の投稿用チャンネルIDに変更してください

# 投稿まとめ用チャンネルID
ANONYMOUS_CHANNEL_ID = ALLOWED_CHANNEL_ID

# インテント設定
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

# Botインスタンス作成
bot = commands.Bot(command_prefix='/', intents=intents)

# リレー小説データなど管理用
relay_story_by_thread = {}
last_post_time_by_user_and_thread = {}

POST_INTERVAL = 300  # 5分制限
MAX_LENGTH = 100     # 最大文字数

# 起動者ユーザーID（start_botした人を記録）
relay_owner_id = None

# Bot起動完了ログ
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'✅ Botログイン完了: {bot.user}')

# ステータス表示（スレッドの物語）
@bot.tree.command(name="status", description="このスレッドのリレー小説の進行状況を表示します")
async def status(interaction: discord.Interaction):
    thread_id = interaction.channel.id
    story_list = relay_story_by_thread.get(thread_id, [])
    story = "\n".join([f"#{i+1}: {line}" for i, line in enumerate(story_list)]) or "まだ物語は始まっていません。"
    if len(story) > 1800:
        story = story[-1800:]
    await interaction.response.send_message(f"📚 このスレッドの物語:\n```\n{story}\n```", ephemeral=True)

# コマンド一覧表示
@bot.tree.command(name="commands", description="Botの利用可能なコマンド一覧を表示します")
async def commands_list(interaction: discord.Interaction):
    cmds = bot.tree.get_commands()
    description = "\n".join([f"/{cmd.name} : {cmd.description}" for cmd in cmds])
    await interaction.response.send_message(f"📜 利用可能なコマンド一覧:\n{description}", ephemeral=True)

# BOT起動コマンド（start_bot）
@bot.tree.command(name="start", description="Botを起動します")
async def start(interaction: discord.Interaction):
    global relay_owner_id

    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return await ctx.send("⚠️ このチャンネルではBOTを起動できません。")

    if relay_owner_id is not None:
        return await ctx.send(f"⚠️ BOTは既に <@{relay_owner_id}> さんによって起動されています。")

    relay_owner_id = ctx.author.id
    await ctx.send(f"🚀 {ctx.author.mention} さんがBOTを起動しました！")

# BOT停止コマンド（end_bot）
@bot.tree.command(name="end", description="Botを終了します")
async def end(interaction: discord.Interaction):
    global relay_owner_id

    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return await ctx.send("⚠️ このチャンネルではBOTを停止できません。")

    user_id = ctx.author.id

    if relay_owner_id is None:
        return await ctx.send("⚠️ BOTは現在起動していません。")

    if user_id == relay_owner_id:
        await ctx.send(f"🛑 {ctx.author.mention} さんがBOTを停止しました。")
        relay_owner_id = None
    else:
        await ctx.send(f"🚫 {ctx.author.mention} さん、あなたにはBOTを停止する権限がありません。起動者は <@{relay_owner_id}> さんです。")
        await ctx.channel.send(f"⚠️ ユーザー {ctx.author.mention} が停止権限なしに停止コマンドを実行しようとしました。")

# メッセージ監視
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if relay_owner_id is None:
        return

    if not (message.channel.id == ALLOWED_CHANNEL_ID or isinstance(message.channel, discord.Thread)):
        return

    content = message.content.strip()
    user_id = message.author.id
    now = time.time()

    if len(content) > MAX_LENGTH:
        try:
            await message.delete()
            await message.channel.send(f"⚠️ 投稿は{MAX_LENGTH}文字以内でお願いします。（現在：{len(content)}文字）", delete_after=5)
        except:
            pass
        return

    thread_id = message.channel.id if not isinstance(message.channel, discord.DMChannel) else None
    key = (user_id, thread_id)
    last_time = last_post_time_by_user_and_thread.get(key, 0)
    if now - last_time < POST_INTERVAL:
        try:
            await message.delete()
            remaining = int(POST_INTERVAL - (now - last_time))
            await message.channel.send(f"⏳ あと {remaining} 秒待ってから投稿してください。", delete_after=5)
        except:
            pass
        return

    last_post_time_by_user_and_thread[key] = now
    if thread_id:
        relay_story_by_thread.setdefault(thread_id, []).append(content)
        post_number = len(relay_story_by_thread[thread_id])
    else:
        thread_id = ANONYMOUS_CHANNEL_ID
        relay_story_by_thread.setdefault(thread_id, []).append(content)
        post_number = len(relay_story_by_thread[thread_id])

    formatted_message = f"🖋 **名も無き作家より（#{post_number}）**：\n{content}"

    if isinstance(message.channel, discord.Thread) or message.channel.id == ANONYMOUS_CHANNEL_ID:
        try:
            await message.delete()
            await message.channel.send(formatted_message)
        except discord.Forbidden:
            print("⚠️ メッセージ削除権限がありません。")
        except Exception as e:
            print(f"❌ エラー: {e}")
    else:
        target_channel = bot.get_channel(ANONYMOUS_CHANNEL_ID)
        if target_channel:
            await target_channel.send(formatted_message)
            await message.channel.send("✅ 投稿を受け付けました。ありがとうございました。")
        else:
            await message.channel.send("⚠️ 投稿チャンネルが見つかりません。管理者に連絡してください。")

# Bot起動
bot.run(TOKEN)
