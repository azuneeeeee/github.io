import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
# random, unicodedata, re は不要になるため削除
# import random
# import unicodedata
# import re

# FlaskはRenderの無料Web Serviceで24時間稼働を試みる場合にのみ必要です。
from flask import Flask
import threading

# admin_commands コグをインポート
# OWNER_ID と is_maintenance_mode は admin_commands.py から共有される変数
from admin_commands import not_in_maintenance, setup as setup_admin_commands_cog, OWNER_ID, is_maintenance_mode

load_dotenv()

# songs モジュールは他のコマンド削除に伴い不要になるため削除
# from songs import proseka_songs, VALID_DIFFICULTIES

# Discordクライアントのインテント設定
# メッセージ内容とメンバーのインテントを有効にする
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ボットのインスタンスを作成
# command_prefix='!' は従来のプレフィックスコマンド用
# application_command_prefix='!' はスラッシュコマンドを有効にするための設定
bot = commands.Bot(command_prefix='!', intents=intents, application_command_prefix='!')

# Flaskアプリのインスタンスを作成（Renderの24時間稼働維持用）
app = Flask(__name__)

@app.route('/')
def home():
    """Renderのヘルスチェック用エンドポイント"""
    return "プロセカBotは稼働中です！"

@bot.event
async def on_ready():
    """ボットがDiscordに接続した際に実行される処理"""
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('------')

    global OWNER_ID
    # 環境変数から製作者IDを読み込む
    if os.getenv('DISCORD_OWNER_ID'):
        try:
            OWNER_ID = int(os.getenv('DISCORD_OWNER_ID'))
            print(f"製作者IDが環境変数から {OWNER_ID} に設定されました。")
        except ValueError:
            print("警告: 環境変数 DISCORD_OWNER_ID が無効な数値です。製作者IDは設定されません。")
            OWNER_ID = None
    else:
        print("警告: 環境変数 DISCORD_OWNER_ID が設定されていません。製作者専用コマンドは機能しません。")
        OWNER_ID = None

    # メンテナンスモードに応じてボットのステータスを設定
    if is_maintenance_mode:
        await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
    else:
        await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))

    try:
        # admin_commands コグをロード
        await bot.load_extension('admin_commands')
        print("admin_commands コグをロードしました。")
        # グローバルスラッシュコマンドをDiscordに同期
        # これが非常に重要で、スラッシュコマンドをDiscordに登録します
        await bot.sync_commands()
        print("スラッシュコマンドをDiscordに同期しました。")
    except Exception as e:
        print(f"admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}")

# ↓↓↓ ここから下の従来のコマンドと関連する関数を削除します ↓↓↓

# @bot.command(name="help_proseka", description="利用可能なコマンドを表示します。")
# @not_in_maintenance()
# async def help_command(ctx):
#     """
#     利用可能なコマンドを表示します。
#     """
#     help_message = (
#         "**プロセカBot コマンドリスト:**\n"
#         "`/song [曲名]` - 特定の曲の難易度情報を表示します。\n"
#         "`/random_song [難易度]` - 指定された難易度でおすすめの曲をランダムに選びます。\n"
#         "`/difficulty_list` - 利用可能な難易度リストを表示します。\n"
#         "`/set_owner [ユーザーID]` - ボットの製作者IDを設定します (製作者専用)。\n"
#         "`/owner_status` - 現在の製作者IDを表示します (製作者専用)。\n"
#         "`/toggle_maintenance` - ボットのメンテナンスモードを切り替えます (製作者専用)。\n"
#         "`/maintenance_status` - メンテナンスモードの状態を表示します (製作者専用)。\n"
#         "\n"
#         "**スラッシュコマンドは `/` を入力して確認してください。**\n"
#         "曲名や難易度は半角で入力してください。\n"
#         "難易度は `easy`, `normal`, `hard`, `expert`, `master` から選んでください。"
#     )
#     await ctx.send(help_message)

# 文字列の類似度を計算する関数（Jaccard係数）
# def jaccard_similarity(s1, s2):
#     set1 = set(s1.lower())
#     set2 = set(s2.lower())
#     intersection = len(set1.intersection(set2))
#     union = len(set1.union(set2))
#     return intersection / union if union != 0 else 0

# ひらがな・カタカナ変換と正規化
# def normalize_text(text):
#     text = unicodedata.normalize('NFKC', text) # 全角英数、カナの正規化
#     text = re.sub(r'[ァ-ヶ]', lambda x: chr(ord(x.group(0)) - 0x60), text) # カタカナをひらがなに変換
#     text = text.lower() # 小文字化
#     return text

# @bot.slash_command(name="song", description="特定の曲の難易度情報を表示します。")
# @not_in_maintenance()
# async def song(ctx: discord.ApplicationContext, song_name: str):
#     """
#     特定の曲の難易度情報を表示します。
#     """
#     normalized_input = normalize_text(song_name)
#     best_match = None
#     highest_similarity = 0.5 # 類似度の閾値

#     for song_info in proseka_songs:
#         normalized_song_name = normalize_text(song_info["name"])
#         similarity = jaccard_similarity(normalized_input, normalized_song_name)
#         if similarity > highest_similarity:
#             highest_similarity = similarity
#             best_match = song_info

#     if best_match:
#         embed = discord.Embed(
#             title=f"🎵 {best_match['name']} の難易度情報",
#             color=discord.Color.blue()
#         )
#         for diff in VALID_DIFFICULTIES:
#             embed.add_field(name=diff.capitalize(), value=f"Lv.{best_match[diff]}", inline=True)
#         await ctx.respond(embed=embed)
#     else:
#         await ctx.respond(f"曲名「{song_name}」は見つかりませんでした。\n正確な曲名を入力してください。")

# @bot.slash_command(name="random_song", description="指定された難易度でおすすめの曲をランダムに選びます。")
# @not_in_maintenance()
# async def random_song(ctx: discord.ApplicationContext, difficulty: str):
#     """
#     指定された難易度でおすすめの曲をランダムに選びます。
#     """
#     difficulty_lower = difficulty.lower()
#     if difficulty_lower not in VALID_DIFFICULTIES:
#         await ctx.respond("無効な難易度です。`easy`, `normal`, `hard`, `expert`, `master` のいずれかを指定してください。")
#         return

#     # 指定された難易度のデータを持つ曲をフィルタリング
#     available_songs = [song for song in proseka_songs if difficulty_lower in song]

#     if not available_songs:
#         await ctx.respond(f"指定された難易度 `{difficulty}` の曲が見つかりませんでした。")
#         return

#     selected_song = random.choice(available_songs)
#     embed = discord.Embed(
#         title=f"🎲 {difficulty.capitalize()} のおすすめ曲",
#         description=f"**{selected_song['name']}**\n難易度: Lv.{selected_song[difficulty_lower]}",
#         color=discord.Color.green()
#     )
#     await ctx.respond(embed=embed)

# @bot.slash_command(name="difficulty_list", description="利用可能な難易度リストを表示します。")
# @not_in_maintenance()
# async def difficulty_list(ctx: discord.ApplicationContext):
#     """
#     利用可能な難易度リストを表示します。
#     """
#     difficulties_str = ", ".join(VALID_DIFFICULTIES)
#     await ctx.respond(f"利用可能な難易度リスト: `{difficulties_str}`")

# ↑↑↑ ここまでの従来のコマンドと関連する関数を削除します ↑↑↑


# ボットの起動処理
if __name__ == '__main__':
    # Flaskサーバーを起動し、Discordボットを別スレッドで実行
    if os.getenv('FLASK_ENABLED', 'False').lower() == 'true':
        def run_discord_bot():
            try:
                bot.run(os.getenv('DISCORD_BOT_TOKEN'))
            except Exception as e:
                print(f"Discord Botの実行中にエラーが発生しました: {e}")

        discord_thread = threading.Thread(target=run_discord_bot)
        discord_thread.start()

        port = int(os.environ.get('PORT', 10000))
        print(f"Flaskサーバーをポート {port} で起動します。")
        app.run(host='0.0.0.0', port=port)
    else:
        # Flaskを無効にしている場合はDiscordボットを直接起動
        print("Flaskサーバーは起動しません。Discord Botを単独で実行します。")
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))