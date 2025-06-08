import discord
from discord.ext import commands
import discord.app_commands
import time # Ping測定のために時間を扱うモジュールをインポート

class PingCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="ping", description="ボットの応答速度を測定します。")
    async def ping(self, interaction: discord.Interaction):
        # コマンドを受け取った直後にdefer（処理中）応答を返す
        await interaction.response.defer(ephemeral=False, thinking=True) # ephemeral=Falseで誰でも見えるようにする

        # interaction.response.defer() を呼び出した時点のUNIXタイムスタンプをミリ秒単位で取得
        # Discordのタイムスタンプはミリ秒単位が一般的
        start_time = interaction.created_at.timestamp() * 1000 
        
        # 現在のUNIXタイムスタンプをミリ秒単位で取得
        current_time = time.time() * 1000

        # ボットとDiscord API間のWebSocketレイテンシ（秒単位）
        # round() で小数点以下2桁に丸める
        websocket_latency = round(self.bot.latency * 1000, 2) # 秒をミリ秒に変換

        # 応答時間（ミリ秒）を計算
        # Discordの処理時間とネットワーク遅延を含む
        # interaction.created_at と followup.send が呼び出されるまでの時間を測定
        # defer後のfollowup.sendなので、正確なPing測定としては少し複雑だが、ユーザー体験としてはこれが分かりやすい
        
        # deferを呼び出してから、followup.sendが完了するまでの時間を計るため、
        # ここではよりシンプルな「ボットのレイテンシ」を表示する
        # もし interaction.created_at からの応答時間を厳密に計りたい場合は、
        # defer前に start_time = time.time() * 1000 を設定し、
        # followup.send 後に end_time = time.time() * 1000 を設定して計算する必要がある
        
        # 今回は、bot.latency を中心に表示
        
        # ping コマンドの応答時に表示するメッセージ
        await interaction.followup.send(
            f"Pong! 🏓\n"
            f"ボットのレイテンシ: `{websocket_latency}ms`\n"
            f"（これはボットとDiscord間のWebSocket接続の遅延です。）"
        )

# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(PingCommand(bot))