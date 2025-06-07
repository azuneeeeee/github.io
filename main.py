# main.py の修正箇所

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import random
import unicodedata
import re

# FlaskはRenderの無料Web Serviceで24時間稼働を試みる場合にのみ必要です。
# from flask import Flask
# import threading

# admin_commands.py から必要な関数と変数をインポート
from admin_commands import not_in_maintenance, setup as setup_admin_commands_cog, OWNER_ID, is_maintenance_mode

# .env ファイルから環境変数を読み込む
load_dotenv()

# songs.py から楽曲データと有効な難易度リストをインポート
from songs import proseka_songs, VALID_DIFFICULTIES

# Discordのインテントを有効にする
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # 製作者のユーザー情報を取得するために必要かもしれません

# コマンドプレフィックスを設定
bot = commands.Bot(command_prefix='!', intents=intents)

# Flaskアプリのインスタンスを作成 (24時間稼働を試みる場合のみ有効化)
# app = Flask(__name__)

# Flaskのエンドポイント (24時間稼働を試みる場合のみ有効化)
# @app.route('/')
# def home():
#     return "プロセカBotは稼働中です！"

# ボットが起動した時のイベント
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('------')

    # 製作者IDを環境変数から設定する
    # Renderの環境変数に DISCORD_OWNER_ID=あなたのユーザーID (数字) を設定してください。
    global OWNER_ID
    if os.getenv('DISCORD_OWNER_ID'):
        try:
            OWNER_ID = int(os.getenv('DISCORD_OWNER_ID'))
            print(f"製作者IDが環境変数から {OWNER_ID} に設定されました。")
        except ValueError:
            print("警告: 環境変数 DISCORD_OWNER_ID が無効な数値です。")
    else:
        print("警告: 環境変数 DISCORD_OWNER_ID が設定されていません。`!set_owner`コマンドで設定するか、Renderの環境変数に設定してください。")

    # 初期ステータスを設定（メンテナンスモードの有無によって調整）
    if is_maintenance_mode:
        await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
    else:
        await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))

    # admin_commands コグをロード
    # setup_admin_commands_cog(bot) # こちらの形式でも可
    await bot.load_extension('admin_commands') # コグを読み込む推奨される方法


# --- ヘルプコマンド ---
@bot.command(name='help_proseka', description='プロセカBotのヘルプを表示します。')
@not_in_maintenance() # メンテナンスモード中は製作者以外は使用不可
async def help_proseka(ctx):
    embed = discord.Embed(title="プロセカBot ヘルプ", description="プロセカに関する情報を提供するBotです！", color=0x7289DA)

    embed.add_field(
        name="`!song <曲名>`",
        value="指定された曲の情報を表示します。\n例: `!song Tell Your World`",
        inline=False
    )
    embed.add_field(
        name="`!random_song [難易度]`",
        value="ランダムな曲を選びます。難易度を指定すると、その難易度の曲を選びます。\n例: `!random_song` または `!random_song master`",
        inline=False
    )
    embed.add_field(
        name="`!difficulty_list`",
        value="対応している難易度の一覧を表示します。",
        inline=False
    )
    embed.set_footer(text="お楽しみください！")
    await ctx.send(embed=embed)

# --- 曲情報表示コマンド ---
@bot.command(name='song', description='指定された曲の情報を表示します。')
@not_in_maintenance() # メンテナンスモード中は製作者以外は使用不可
async def get_song_info(ctx, *, query: str):
    # クエリを正規化
    normalized_query = unicodedata.normalize('NFKC', query).lower().replace(" ", "").replace("　", "")
    normalized_query = re.sub(r'[^\w]', '', normalized_query)

    found_song = None
    for song in proseka_songs:
        normalized_title = unicodedata.normalize('NFKC', song["title"]).lower().replace(" ", "").replace("　", "")
        normalized_title = re.sub(r'[^\w]', '', normalized_title)
        
        if normalized_query == normalized_title:
            found_song = song
            break

    if found_song:
        embed = discord.Embed(title=f"🎵 {found_song['title']}", color=0x0099ff)
        if found_song.get("image_url"):
            embed.set_thumbnail(url=found_song["image_url"])

        difficulty_info = []
        for diff in VALID_DIFFICULTIES:
            diff_lower = diff.lower()
            if diff_lower in found_song and found_song[diff_lower] is not None:
                difficulty_info.append(f"**{diff}:** {found_song[diff_lower]}")
        
        if difficulty_info:
            embed.add_field(name="🎶 難易度", value="\n".join(difficulty_info), inline=False)
        else:
            embed.add_field(name="🎶 難易度", value="難易度情報がありません。", inline=False)
        
        embed.set_footer(text=f"情報提供: プロセカBot")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"⚠️ **'{query}'** という曲は見つかりませんでした。\n曲名が正しいか、全角・半角、スペースなどを確認してみてください。")

# --- ランダムな曲を返すコマンド ---
@bot.command(name='random_song', description='ランダムな曲を選びます。')
@not_in_maintenance() # メンテナンスモード中は製作者以外は使用不可
async def random_song(ctx, difficulty: str = None):
    target_songs = []
    
    if difficulty:
        normalized_difficulty = difficulty.upper()
        if normalized_difficulty not in VALID_DIFFICULTIES:
            await ctx.send(f"⚠️ 無効な難易度です。有効な難易度は: `{', '.join(VALID_DIFFICULTIES)}` です。")
            return
        
        for song in proseka_songs:
            if normalized_difficulty.lower() in song and song[normalized_difficulty.lower()] is not None:
                target_songs.append(song)
        
        if not target_songs:
            await ctx.send(f"⚠️ '{normalized_difficulty}' の難易度データを持つ曲が見つかりませんでした。")
            return
    else:
        target_songs = proseka_songs[:]

    if not target_songs:
        await ctx.send("⚠️ 楽曲データがありません。`songs.py`に曲を追加してください。")
        return

    random_song_choice = random.choice(target_songs)

    embed = discord.Embed(title=f"今日のあなたへのおすすめ曲！\n🎵 {random_song_choice['title']}", color=0xff69b4)

    if random_song_choice.get("image_url"):
        embed.set_thumbnail(url=random_song_choice["image_url"])

    difficulty_info = []
    for diff in VALID_DIFFICULTIES:
        diff_lower = diff.lower()
        if diff_lower in random_song_choice and random_song_choice[diff_lower] is not None:
            difficulty_info.append(f"**{diff}:** {random_song_choice[diff_lower]}")
    
    if difficulty_info:
        embed.add_field(name="🎶 難易度", value="\n".join(difficulty_info), inline=False)
    else:
        embed.add_field(name="🎶 難易度", value="難易度情報がありません。", inline=False)
    
    embed.set_footer(text=f"情報提供: プロセカBot")
    await ctx.send(embed=embed)

# --- 難易度リスト表示コマンド ---
@bot.command(name='difficulty_list', description='対応している難易度の一覧を表示します。')
@not_in_maintenance() # メンテナンスモード中は製作者以外は使用不可
async def show_difficulty_list(ctx):
    await ctx.send(f"対応している難易度は以下の通りです: `{', '.join(VALID_DIFFICULTIES)}`")


# ボットの実行部分
# FlaskとDiscord Botを並行して実行するロジック (Render無料Web Service向け)
# 環境変数 FLASK_ENABLED=true で有効化します
# if __name__ == '__main__':
#     if os.getenv('FLASK_ENABLED', 'False').lower() == 'true':
#         def run_discord_bot():
#             bot.run(os.getenv('DISCORD_BOT_TOKEN'))

#         discord_thread = threading.Thread(target=run_discord_bot)
#         discord_thread.start()

#         port = int(os.environ.get('PORT', 10000))
#         app.run(host='0.0.0.0', port=port)
#     else:
# 通常のDiscord Bot実行
bot.run(os.getenv('DISCORD_BOT_TOKEN'))