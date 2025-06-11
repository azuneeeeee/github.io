import discord
from discord.ext import commands
import discord.app_commands
import random
import logging

# data/songs.py から情報をインポート
try:
    from data import songs
except ImportError:
    logging.critical("致命的なエラー: data/songs.py が見つからないか、インポートできませんでした。")
    # ボットが起動できないように、ここではエラーを発生させるか、適切なハンドリングを行う
    # 例: raise SystemExit("data/songs.py が見つかりません。")

# admin_commands から not_in_maintenance と is_owner_check をインポート
from commands.admin.admin_commands import not_in_maintenance, is_owner_check

logger = logging.getLogger(__name__)

class PjskRandomSongCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("PjskRandomSongCommandsコグが初期化されています。")

    # コマンド名を 'pjsk_random_song' に変更し、新しいオプションを追加
    @discord.app_commands.command(name="pjsk_random_song", description="プロセカのランダムな曲を提示します。")
    @discord.app_commands.describe(
        min_level="最小レベル (1-37)",
        max_level="最大レベル (1-37)",
        difficulties="選曲する難易度タイプ (複数選択可)"
    )
    @discord.app_commands.choices(
        difficulties=[ # 複数選択可能な難易度タイプ
            discord.app_commands.Choice(name="EASY", value="easy"),
            discord.app_commands.Choice(name="NORMAL", value="normal"),
            discord.app_commands.Choice(name="HARD", value="hard"),
            discord.app_commands.Choice(name="EXPERT", value="expert"),
            discord.app_commands.Choice(name="MASTER", value="master"),
            discord.app_commands.Choice(name="APPEND", value="append") # appendがある場合
        ]
    )
    @not_in_maintenance() # メンテナンスモード中は利用不可
    async def pjsk_random_song(
        self,
        interaction: discord.Interaction,
        min_level: discord.app_commands.Range[int, 1, 37] = None, # 最小レベル
        max_level: discord.app_commands.Range[int, 1, 37] = None, # 最大レベル
        difficulties: str = None # 複数選択された難易度タイプ (文字列として受け取る)
    ):
        await interaction.response.defer() # 処理に時間がかかる可能性があるため、deferで応答を保留

        if not songs.proseka_songs:
            await interaction.followup.send("曲データが見つかりませんでした。", ephemeral=True)
            logger.warning("警告: /pjsk_random_song コマンドが実行されましたが、proseka_songs が空でした。")
            return

        try:
            available_songs = []
            
            # 選択された難易度タイプをリストに変換 (例: "master,expert" -> ["master", "expert"])
            selected_difficulty_types = []
            if difficulties:
                selected_difficulty_types = difficulties.split(',')
                # 大文字小文字の区別をなくすため小文字に変換
                selected_difficulty_types = [d.lower() for d in selected_difficulty_types]
            
            logger.debug(f"デバッグ: 選択された難易度タイプ: {selected_difficulty_types}")

            # フィルタリング
            for song in songs.proseka_songs:
                # 選択された難易度タイプに合致する難易度レベルがあるかチェック
                has_selected_difficulty = False
                if not selected_difficulty_types: # 難易度タイプが指定されていない場合は全ての曲を対象
                    has_selected_difficulty = True
                else:
                    for diff_type in selected_difficulty_types:
                        if diff_type in song and song[diff_type] is not None:
                            # レベル範囲のチェック
                            level = song[diff_type]
                            if min_level is not None and level < min_level:
                                continue # 最小レベルより低い場合はスキップ
                            if max_level is not None and level > max_level:
                                continue # 最大レベルより高い場合はスキップ
                            
                            has_selected_difficulty = True
                            break # いずれかの難易度タイプとレベルが合致すればOK

                if has_selected_difficulty:
                    available_songs.append(song)


            if not available_songs:
                await interaction.followup.send(
                    "指定された条件に合う曲が見つかりませんでした。条件を緩和してみてください。",
                    ephemeral=True
                )
                logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_random_song コマンドを使用しましたが、条件に合う曲が見つかりませんでした。min_level={min_level}, max_level={max_level}, difficulties={difficulties}")
                return

            # フィルタリングされた曲の中からランダムに選択
            random_song = random.choice(available_songs)

            # 難易度情報を取得し、表示をMasterのみに絞る（または指定された難易度タイプから最適なものを選択）
            difficulty_info = "情報なし"
            display_difficulty_type = None # 表示する難易度タイプ（master, expertなど）

            # ユーザーが難易度タイプを指定した場合、その中から最も高い難易度を表示
            if selected_difficulty_types:
                # 優先順位（高い順）
                priority_difficulties = ["append", "master", "expert", "hard", "normal", "easy"]
                for diff_type in priority_difficulties:
                    if diff_type in selected_difficulty_types and diff_type in random_song and random_song[diff_type] is not None:
                        display_difficulty_type = diff_type
                        break
            
            # ユーザーが難易度タイプを指定しなかった場合、または指定された難易度タイプに合致する難易度がない場合
            if display_difficulty_type is None:
                # デフォルトの優先順位で表示する難易度を決定
                default_priority = ["append", "master", "expert", "hard", "normal", "easy"]
                for diff_type in default_priority:
                    if diff_type in random_song and random_song[diff_type] is not None:
                        display_difficulty_type = diff_type
                        break
            
            if display_difficulty_type:
                # 難易度表記を全て大文字にする
                difficulty_info = f"{display_difficulty_type.upper()}: {random_song[display_difficulty_type]}"
            
            logger.debug(f"デバッグ: 選択された曲の難易度情報: {difficulty_info}")

            # 曲のサムネイルURLを安全に取得 (キー名を 'image_url' に変更)
            thumbnail_url = random_song.get("image_url", None)

            # Embedの作成 (タイトルを 'title' キーから取得)
            embed = discord.Embed(
                title=f"🎧 {random_song.get('title', 'タイトル情報なし')}",
                color=discord.Color.blue() # プロセカっぽい色 (任意)
            )

            # アーティスト、ユニット、イベントのフィールドを削除済み

            # 難易度情報を単一で追加
            embed.add_field(name="難易度", value=difficulty_info, inline=False)

            # サムネイルがある場合のみ設定
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
                logger.debug(f"デバッグ: Embedに設定するサムネイルURL: {thumbnail_url}")
            else:
                logger.debug("デバッグ: サムネイルURLが取得できなかったため、Embedに設定しませんでした。")

            embed.set_footer(text="プロセカ ランダム選曲")

            await interaction.followup.send(embed=embed)
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_random_song コマンドを使用しました。曲: {random_song.get('title', 'タイトル情報なし')}")

        except Exception as e:
            await interaction.followup.send(f"曲の選曲中にエラーが発生しました: {e}", ephemeral=True)
            logger.error(f"エラー: /pjsk_random_song コマンドの実行中に予期せぬエラーが発生しました: {e}", exc_info=True)


    async def cog_load(self):
        logger.info("PjskRandomSongCommandsコグがロードされました。")

    async def cog_unload(self):
        logger.info("PjskRandomSongCommandsコグがアンロードされました。")

async def setup(bot):
    await bot.add_cog(PjskRandomSongCommands(bot))