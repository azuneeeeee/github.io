# main.py

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import random
import unicodedata # 全角半角の違いを吸収するために使用
import re          # 特定の文字を削除するために使用

# FlaskはRenderの無料Web Serviceで24時間稼働を試みる場合にのみ必要です。
# RenderのWorkerサービスや有料プランを利用する場合は不要です。
from flask import Flask
import threading # FlaskとDiscord Botを並行して実行するために必要

# admin_commands.py から必要な関数と変数をインポート
# OWNER_IDとis_maintenance_modeはadmin_commands.pyで定義され、main.pyから参照・更新されます。
from admin_commands import not_in_maintenance, setup as setup_admin_commands_cog, OWNER_ID, is_maintenance_mode

# .env ファイルから環境変数を読み込む
# これはローカルでのテスト時に使用します。RenderではRenderの環境変数設定が優先されます。
load_dotenv()

# songs.py から楽曲データと有効な難易度リストをインポート
from songs import proseka_songs, VALID_DIFFICULTIES

# Discordのインテントを有効にする
# intents.message_content: メッセージの内容を読み取るために必要です。
# intents.members: ユーザー情報を取得するために必要です (例: 製作者の名前を表示するため)。
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# コマンドプレフィックスを設定
# 例: !song, !random_song など。スラッシュコマンドとは別で利用できます。
bot = commands.Bot(command_prefix='!', intents=intents)

# Flaskアプリのインスタンスを作成 (24時間稼働を試みる場合のみ有効化)
app = Flask(__name__)

# Flaskのエンドポイント (RenderがHTTPリクエストを送る先として機能)
@app.route('/')
def home():
    # ボットが稼働中であることを示すシンプルなメッセージ
    return "プロセカBotは稼働中です！"


# ボットが起動した時のイベント
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('------')

    # 製作者IDを環境変数から設定する
    # Renderの環境変数に DISCORD_OWNER_ID=あなたのユーザーID (数字) を設定してください。
    global OWNER_ID # admin_commands.pyで定義されているOWNER_IDをここで更新します
    if os.getenv('DISCORD_OWNER_ID'):
        try:
            OWNER_ID = int(os.getenv('DISCORD_OWNER_ID'))
            print(f"製作者IDが環境変数から {OWNER_ID} に設定されました。")
        except ValueError:
            print("警告: 環境変数 DISCORD_OWNER_ID が無効な数値です。製作者IDは設定されません。")
            OWNER_ID = None # 無効な場合はNoneに戻す
    else:
        print("警告: 環境変数 DISCORD_OWNER_ID が設定されていません。製作者専用コマンドは機能しません。")
        OWNER_ID = None # 設定されていない場合はNone

    # 初期ステータスを設定
    # メンテナンスモードの状態に基づいてボットのプレイ中ステータスを変更します。
    if is_maintenance_mode:
        await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
    else:
        await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))

    # admin_commands コグをロード
    # これにより、admin_commands.pyで定義されたスラッシュコマンドがボットに登録されます。
    try:
        await bot.load_extension('admin_commands')
        print("admin_commands コグをロードしました。")
    except Exception as e:
        print(f"admin_commands コグのロード中にエラーが発生しました: {e}")


# --- ヘルプコマンド ---
@bot.command(name='help_proseka', description='プロセカBotのヘルプを表示します。')
@not_in_maintenance() # メンテナンスモード中は製作者以外は使用不可
async def help_proseka(ctx):
    embed = discord.Embed(title="プロセカBot ヘルプ", description="プロセカに関する情報を提供するBotです！", color=0x7289DA) # Discordのブランドカラー

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
    embed.add_field(
        name="製作者専用コマンド（スラッシュコマンド）",
        value="`/toggle_maintenance`、`/owner_status`、`/maintenance_status` など。製作者のみ利用可能です。",
        inline=False
    )
    embed.set_footer(text="お楽しみください！")
    await ctx.send(embed=embed)

# --- 曲情報表示コマンド ---
@bot.command(name='song', description='指定された曲の情報を表示します。')
@not_in_maintenance() # メンテナンスモード中は製作者以外は使用不可
async def get_song_info(ctx, *, query: str):
    # クエリを正規化（全角→半角、スペース除去、小文字化、記号除去）
    # これにより「tell your world」や「ＴｅｌｌＹｏｕｒＷｏｒｌｄ」のような入力揺れに対応できます。
    normalized_query = unicodedata.normalize('NFKC', query).lower().replace(" ", "").replace("　", "")
    normalized_query = re.sub(r'[^\w]', '', normalized_query) # 英数字以外を除去

    found_song = None
    for song in proseka_songs:
        normalized_title = unicodedata.normalize('NFKC', song["title"]).lower().replace(" ", "").replace("　", "")
        normalized_title = re.sub(r'[^\w]', '', normalized_title)
        
        # 完全に一致する曲を検索
        if normalized_query == normalized_title:
            found_song = song
            break

    if found_song:
        embed = discord.Embed(title=f"🎵 {found_song['title']}", color=0x0099ff)
        
        # 画像URLがあれば埋め込みのサムネイルとして設定
        if found_song.get("image_url"):
            embed.set_thumbnail(url=found_song["image_url"])

        # 難易度情報を追加
        difficulty_info = []
        for diff in VALID_DIFFICULTIES:
            diff_lower = diff.lower() # 難易度キーは小文字で格納されていると想定
            # 辞書にキーが存在し、かつ値がNoneでない場合にのみ追加
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
        normalized_difficulty = difficulty.upper() # 入力された難易度を大文字に変換
        if normalized_difficulty not in VALID_DIFFICULTIES:
            await ctx.send(f"⚠️ 無効な難易度です。有効な難易度は: `{', '.join(VALID_DIFFICULTIES)}` です。")
            return
        
        # 指定された難易度を持つ曲のみをフィルタリング
        # かつ、その難易度の値がNoneでないことを確認
        for song in proseka_songs:
            if normalized_difficulty.lower() in song and song[normalized_difficulty.lower()] is not None:
                target_songs.append(song)
        
        if not target_songs:
            await ctx.send(f"⚠️ '{normalized_difficulty}' の難易度データを持つ曲が見つかりませんでした。")
            return
    else:
        # 難易度指定がない場合は全ての曲から選ぶ
        target_songs = proseka_songs[:] # リストのコピーを作成

    if not target_songs:
        await ctx.send("⚠️ 楽曲データがありません。`songs.py`に曲を追加してください。")
        return

    random_song_choice = random.choice(target_songs)

    embed = discord.Embed(title=f"今日のあなたへのおすすめ曲！\n🎵 {random_song_choice['title']}", color=0xff69b4) # ピンク色

    # 画像URLがあれば埋め込みのサムネイルとして設定
    if random_song_choice.get("image_url"):
        embed.set_thumbnail(url=random_song_choice["image_url"])

    # 難易度情報を追加
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
# Renderの無料Web Serviceで24時間稼働を試みる場合は、以下のFlask関連のコードを有効化してください。
# その際、requirements.txtに 'Flask' を追加し、Renderの環境変数に FLASK_ENABLED=true を設定してください。
# それ以外（Render Workerサービス、有料プランなど）の場合は、下の bot.run() のみでOKです。

if __name__ == '__main__':
    # FlaskとDiscord Botを並行して実行するロジック (Render無料Web Service向け)
    # 環境変数 FLASK_ENABLED=true で有効化します
    if os.getenv('FLASK_ENABLED', 'False').lower() == 'true':
        def run_discord_bot():
            # Discord Botの実行中にエラーが発生した場合でも、Flaskサーバーが停止しないようにtry-exceptで囲みます。
            try:
                bot.run(os.getenv('DISCORD_BOT_TOKEN'))
            except Exception as e:
                print(f"Discord Botの実行中にエラーが発生しました: {e}")
                # エラーが発生してもプログラムが終了しないように、ここで適切なログ出力や処理を行う
                # Renderが再起動するのを待つか、手動で再デプロイが必要になる場合がある

        discord_thread = threading.Thread(target=run_discord_bot)
        discord_thread.start()

        # RenderはPORT環境変数でポートを指定してくるため、それを取得してFlaskを実行
        # デフォルトポートを10000としていますが、Renderは動的に割り当てます。
        port = int(os.environ.get('PORT', 10000))
        print(f"Flaskサーバーをポート {port} で起動します。")
        app.run(host='0.0.0.0', port=port)
    else:
        # Flaskを導入しない場合の通常のDiscord Bot実行
        # RenderのWorkerサービスや有料プランを利用する場合、またはローカルテスト時
        print("Flaskサーバーは起動しません。Discord Botを単独で実行します。")
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))