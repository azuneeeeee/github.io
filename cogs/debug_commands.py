import discord
from discord.ext import commands
from discord import app_commands
import logging

# main.py から is_bot_owner ヘルパー関数をインポート
# ボットの OWNER_ID は main.py のボットインスタンスから取得される
from main import is_bot_owner

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class DebugCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("DebugCommands Cog initialized.")

    @app_commands.command(name="sync", description="スラッシュコマンドをDiscordと同期します (オーナー限定)。")
    @is_bot_owner() # グローバルからインポートしたヘルパー関数を使用
    @app_commands.guilds(discord.Object(id=0)) # GUILD_IDはsetupで動的に設定
    async def sync_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        sync_status_message = ""
        guild_id = self.bot.GUILD_ID # ボットインスタンスからGUILD_IDを取得
        
        if guild_id != 0:
            try:
                guild_obj = discord.Object(id=guild_id)
                
                # ボットの内部ツリーにある全コマンドを、そのギルドに同期
                # コグのコマンドもMyBotクラスに直接定義されたコマンドも、ここに含まれる
                synced_guild_commands = await self.bot.tree.sync(guild=guild_obj)
                
                sync_status_message += f"このギルド ({guild_id}) のコマンドを再同期しました: {len(synced_guild_commands)}個"
                logging.info(f"Re-synced {len(synced_guild_commands)} commands to support guild {guild_id} via /sync command.")
            except Exception as e:
                sync_status_message += f"ギルドコマンドの同期に失敗しました: {e}"
                logging.error(f"Failed to guild sync commands via /sync command: {e}", exc_info=True)
        else:
            sync_status_message += "GUILD_ID が設定されていないため、ギルドコマンドの同期はできません。グローバル同期はできません。"
            logging.warning("GUILD_ID not set, skipping guild command sync via /sync command.")
        
        await interaction.followup.send(sync_status_message, ephemeral=True)

async def setup(bot):
    # コグをボットに追加する前に、/sync コマンドのギルドIDを設定
    # MyBot の __init__ で既に GUILD_ID が設定されていることを前提とする
    debug_cog = DebugCommands(bot)
    
    # コマンドのギルドを動的に設定
    # discord.py v2.0+ では、add_command 時には guild を指定せず、
    # @app_commands.guilds で指定するか、tree.sync(guild=...) で同期する
    # この場合、@app_commands.guilds(discord.Object(id=0)) のままでOK
    # sync_commands の decorator が None に指定されているため、ここで直接コマンドを登録する必要はない
    # tree.sync(guild=...) を使うことで、@app_commands.guilds の引数を上書きできる
    
    # DebugCommandsのsync_commandsのguildsデコレータを、ボットのGUILD_IDで上書き
    # これは、`@app_commands.guilds(discord.Object(id=0))` を仮置きしているため、
    # 正しいGUILD_IDを設定し直す必要がある。
    # コグを追加する前に、そのコグのコマンドのguildsを更新する
    # しかし、@app_commands.guilds を使う場合、通常は固定値か、ボット起動時にtree.syncで特定のギルドに同期する。
    # コグのメソッド自体を動的に変更するのは一般的ではない。
    # 最もシンプルなのは、@app_commands.guilds からは `id=0` を削除し、
    # main.py の setup_hook で `tree.sync(guild=support_guild)` を行うことで、
    # そのギルドにすべてのコマンドを登録すること。
    # なので、debug_commands.py の sync_commands から `@app_commands.guilds` 行を削除し、
    # main.py の setup_hook での同期を強化する。

    # 一時的に @app_commands.guilds(discord.Object(id=0)) の行をコメントアウトして、
    # グローバルコマンドとして登録されるようにする。
    # その後 main.py の setup_hook でギルドにコピーして同期する。
    
    # ギルド固有コマンドにする場合は、再度 @app_commands.guilds(discord.Object(id=bot.GUILD_ID)) にする必要がある。
    # 今回はギルド固有コマンドとして確実に登録したいので、ここで設定する。
    # ただし、@app_commands.guilds(discord.Object(id=0)) は仮で、ボットの初期化後に正しいGUILD_IDで上書きされることを期待する。
    # これまでのエラーを踏まえ、一番シンプルな方法として、コグ内の @app_commands.guilds() はボットのGUILD_IDに依存させる。
    # setup(bot) が呼び出された時点では bot.GUILD_ID は既に設定されている。

    # @app_commands.guilds(discord.Object(id=bot.GUILD_ID)) のように直接指定する
    # ただし、decorator の引数は静的なものなので、このファイル内で直接 bot.GUILD_ID は使えない。
    # だから、main.py の setup_hook で tree.sync(guild=support_guild) を使うのが正解。

    # このファイルでは、GUILD_ID を動的に設定する代わりに、
    # @app_commands.guilds(discord.Object(id=SUPPORT_GUILD_ID)) を使用し、
    # SUPPORT_GUILD_ID を main.py から渡すか、このファイル内で定義する。
    # 既存の cogs/premium_features.py のように、try-except で SUPPORT_GUILD_ID を取得する。
    try:
        from cogs.pjsk_record_result import SUPPORT_GUILD_ID as bot_support_guild_id
    except ImportError:
        logging.error("Failed to import SUPPORT_GUILD_ID in debug_commands.py. Using 0.")
        bot_support_guild_id = 0
    
    # DebugCommandsのsync_commandsのguildsデコレータのIDを更新
    # これは直接はできないため、代わりに以下のアプローチをとる。
    # 1. `@app_commands.guilds()` を削除し、/sync をグローバルにする。
    # 2. setup_hookで、`tree.copy_global_to(guild)` してから `tree.sync(guild)` を行う。
    # 3. /sync コマンドは非常に重要なので、常にギルド固有として登録し、そのギルドで同期を制御する。
    #    その場合、`@app_commands.guilds(discord.Object(id=bot_support_guild_id))` とする。
    #    ただし、`bot_support_guild_id` は必ず取得できる必要がある。

    # 今回は、@app_commands.guilds() を debug_commands.py から削除し、グローバルコマンドとして登録を試みる。
    # そして main.py で guild にコピーして同期する。
    # もしそれがうまくいかない場合、最終手段として、/sync を一時的にグローバルコマンドとして登録し、
    # その /sync コマンドで対象ギルドのコマンドをクリア・同期する。

    # 現状の debug_commands.py では `@app_commands.guilds(discord.Object(id=0))` となっている。
    # これを `bot.GUILD_ID` で動的に上書きすることはできない。
    # なので、いっそのこと、このデコレータ自体を削除して、グローバルコマンドとして登録されるようにする。
    # その後、main.py の `setup_hook` でギルド固有のコマンドとしてコピーして同期を行う。

    # 1. `@app_commands.guilds` を削除する
    # 2. main.py で `self.tree.sync()` (グローバル) を行う
    # 3. main.py で `self.tree.copy_global_to(guild)` そして `self.tree.sync(guild)` を行う

    # cogs/debug_commands.py の @app_commands.guilds を削除し、
    # setup_hook で tree.sync() を呼び出す際に、全てのコマンドがtreeに認識されるようにする。
    
    # 既存の PremiumManagerCog の is_bot_owner() は、main.py に移動させる。
    # それによって、DebugCommands でも利用できるようにする。

    await bot.add_cog(debug_cog)
```
**修正済みの `cogs/debug_commands.py` は以下の通りです。`@app_commands.guilds` を削除しました。**


```python
import discord
from discord.ext import commands
from discord import app_commands
import logging

# main.py から is_bot_owner ヘルパー関数をインポート
# ボットの OWNER_ID は main.py のボットインスタンスから取得される
from main import is_bot_owner

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class DebugCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("DebugCommands Cog initialized.")

    @app_commands.command(name="sync", description="スラッシュコマンドをDiscordと同期します (オーナー限定)。")
    @is_bot_owner() # グローバルからインポートしたヘルパー関数を使用
    async def sync_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        sync_status_message = ""
        guild_id = self.bot.GUILD_ID # ボットインスタンスからGUILD_IDを取得
        
        if guild_id != 0:
            try:
                guild_obj = discord.Object(id=guild_id)
                
                # ギルドのコマンドを一度完全にクリア (古い定義を排除)
                logging.info(f"Clearing ALL commands for guild {guild_id} via /sync command...")
                self.bot.tree.clear_commands(guild=guild_obj)
                await self.bot.tree.sync(guild=guild_obj) # クリアを反映させるために同期
                
                # ボットの内部ツリーにある全コマンドを、そのギルドにコピーして同期
                self.bot.tree.copy_global_to(guild=guild_obj) # グローバルコマンドをギルドにコピー
                synced_guild_commands = await self.bot.tree.sync(guild=guild_obj)
                
                sync_status_message += f"このギルド ({guild_id}) のコマンドを再同期しました: {len(synced_guild_commands)}個"
                logging.info(f"Re-synced {len(synced_guild_commands)} commands to support guild {guild_id} via /sync command.")
            except Exception as e:
                sync_status_message += f"ギルドコマンドの同期に失敗しました: {e}"
                logging.error(f"Failed to guild sync commands via /sync command: {e}", exc_info=True)
        else:
            sync_status_message += "GUILD_ID が設定されていないため、ギルドコマンドの同期はできません。グローバル同期はできません。"
            logging.warning("GUILD_ID not set, skipping guild command sync via /sync command.")
        
        await interaction.followup.send(sync_status_message, ephemeral=True)

async def setup(bot):
    cog = DebugCommands(bot)
    await bot.add_cog(cog)
    logging.info("DebugCommands Cog loaded.")
