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
    raise SystemExit("data/songs.py が見つかりません。")

# admin_commands から not_in_maintenance と is_owner_check をインポート
from commands.admin.admin_commands import not_in_maintenance, is_owner_check

logger = logging.getLogger(__name__)

class PjskRandomSongCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("PjskRandomSongCommandsコグが初期化されています。")

    # 利用可能な難易度タイプを定義 (小文字で内部処理、大文字で表示)
    ALL_DIFFICULTY_TYPES = ["easy", "normal", "hard", "expert", "master", "append"]
    DISPLAY_DIFFICULTY_TYPES = {
        "easy": "EASY",
        "normal": "NORMAL",
        "hard": "HARD",
        "expert": "EXPERT",
        "master": "MASTER",
        "append": "APPEND"
    }
    
    # コマンド名を 'pjsk_random_song' に変更し、新しいオプションを追加
    @discord.app_commands.command(name="pjsk_random_song", description="プロセカのランダムな曲を提示します。")
    @discord.app_commands.describe(
        min_level="最小レベル (1-37)",
        max_level="最大レベル (1-37)",
        difficulties="選曲する難易度タイプ (カンマ区切りで複数指定可例: MASTER,EXPERT)"
    )
    @not_in_maintenance() # メンテナンスモード中は利用不可
    async def pjsk_random_song(
        self,
        interaction: discord.Interaction,
        min_level: discord.app_commands.Range[int, 1, 37] = None, # 最小レベル
        max_level: discord.app_commands.Range[int, 1, 37] = None, # 最大レベル
        difficulties: str = None # カンマ区切りの文字列として受け取る
    ):
        await interaction.response.defer() # 処理に時間がかかる可能性があるため、deferで応答を保留

        if not songs.proseka_songs:
            await interaction.followup.send("曲データが見つかりませんでした。", ephemeral=True)
            logger.warning("警告: /pjsk_random_song コマンドが実行されましたが、proseka_songs が空でした。")
            return

        try:
            available_songs = []
            
            # 選択された難易度タイプをパース
            selected_difficulty_types_from_input = [] # ユーザーが入力した難易度タイプ
            if difficulties:
                raw_difficulties = [d.strip().lower() for d in difficulties.split(',') if d.strip()]
                selected_difficulty_types_from_input = [
                    d for d in raw_difficulties if d in self.ALL_DIFFICULTY_TYPES
                ]
                
                if len(raw_difficulties) != len(selected_difficulty_types_from_input):
                    invalid_types = set(raw_difficulties) - set(self.ALL_DIFFICULTY_TYPES)
                    if invalid_types:
                        await interaction.followup.send(
                            f"警告: 不正な難易度タイプが指定されました: {', '.join([self.DISPLAY_DIFFICULTY_TYPES.get(t, t.upper()) for t in invalid_types])}。無視して処理を続行します。",
                            ephemeral=True
                        )
            
            # フィルタリングに使用する難易度タイプ。指定がなければ全て
            difficulties_for_filtering = selected_difficulty_types_from_input if selected_difficulty_types_from_input else self.ALL_DIFFICULTY_TYPES
            
            logger.debug(f"デバッグ: フィルタリングに使用する難易度タイプ: {difficulties_for_filtering}")
            logger.debug(f"デバッグ: min_level={min_level}, max_level={max_level}")

            # フィルタリングロジック
            for song in songs.proseka_songs:
                song_matches_criteria = False
                
                for diff_type in difficulties_for_filtering: # フィルタリング用難易度タイプを使用
                    if diff_type in song and song[diff_type] is not None:
                        level = song[diff_type]
                        
                        level_in_range = True
                        if min_level is not None and level < min_level:
                            level_in_range = False
                        if max_level is not None and level > max_level:
                            level_in_range = False
                        
                        if level_in_range:
                            song_matches_criteria = True
                            break

                if song_matches_criteria:
                    available_songs.append(song)

            if not available_songs:
                await interaction.followup.send(
                    "指定された条件に合う曲が見つかりませんでした。条件を緩和してみてください。",
                    ephemeral=True
                )
                logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_random_song コマンドを使用しましたが、条件に合う曲が見つかりませんでした。min_level={min_level}, max_level={max_level}, difficulties_selected={difficulties_for_filtering}")
                return

            # フィルタリングされた曲の中からランダムに選択
            random_song = random.choice(available_songs)

            # --- ここから表示する難易度をランダムに選ぶロジック ---
            difficulty_info = "情報なし"
            
            # 実際に表示する難易度タイプを決定するための候補リスト
            display_candidates = []
            
            # ユーザーが難易度タイプを指定している場合
            if selected_difficulty_types_from_input:
                # ユーザーが指定した難易度タイプの中から、選ばれた曲に存在するものを候補とする
                for diff_type in selected_difficulty_types_from_input:
                    if diff_type in random_song and random_song[diff_type] is not None:
                        level_for_display = random_song[diff_type]
                        
                        # その難易度がレベル範囲内にあるかチェック
                        if (min_level is None or level_for_display >= min_level) and \
                           (max_level is None or level_for_display <= max_level):
                            display_candidates.append(diff_type)
            
            # ユーザーが難易度タイプを指定していない場合、または指定したが候補が見つからなかった場合
            if not display_candidates:
                # 選ばれた曲が持つ全ての難易度の中から、レベル範囲内のものを候補とする
                for diff_type in self.ALL_DIFFICULTY_TYPES:
                    if diff_type in random_song and random_song[diff_type] is not None:
                        level_for_display = random_song[diff_type]
                        
                        # その難易度がレベル範囲内にあるかチェック
                        if (min_level is None or level_for_display >= min_level) and \
                           (max_level is None or level_for_display <= max_level):
                            display_candidates.append(diff_type)
            
            # 最終的な表示難易度を決定
            if display_candidates:
                chosen_display_difficulty = random.choice(display_candidates) # 候補からランダムに選択
                difficulty_info = f"{self.DISPLAY_DIFFICULTY_TYPES.get(chosen_display_difficulty, chosen_display_difficulty.upper())}: {random_song[chosen_display_difficulty]}"
            
            logger.debug(f"デバッグ: 最終的に表示する難易度情報: {difficulty_info}")

            # 曲のサムネイルURLを安全に取得 (キー名を 'image_url' に変更)
            thumbnail_url = random_song.get("image_url", None)

            # Embedの作成 (タイトルを 'title' キーから取得)
            embed = discord.Embed(
                title=f"🎧 {random_song.get('title', 'タイトル情報なし')}",
                color=discord.Color.blue()
            )

            embed.add_field(name="難易度", value=difficulty_info, inline=False)

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

    # ★★★★★ ここから下の Autocomplete の部分を全て削除 ★★★★★
    # @pjsk_random_song.autocomplete('difficulties')
    # async def difficulties_autocomplete(self, interaction: discord.Interaction, current: str):
    #     """難易度タイプの入力補完を提供します。"""
    #     entered_parts = [p.strip().lower() for p in current.split(',') if p.strip()]
    #     last_part = entered_parts[-1] if entered_parts else ""

    #     options = []
    #     for diff_key in self.ALL_DIFFICULTY_TYPES:
    #         display_name = self.DISPLAY_DIFFICULTY_TYPES[diff_key]
    #         if diff_key not in entered_parts[:-1] and display_name.lower().startswith(last_part):
    #             options.append(display_name)
        
    #     return [
    #         discord.app_commands.Choice(name=opt, value=opt)
    #         for opt in options[:25]
    #     ]
    # ★★★★★ ここまで削除 ★★★★★

    async def cog_load(self):
        logger.info("PjskRandomSongCommandsコグがロードされました。")

    async def cog_unload(self):
        logger.info("PjskRandomSongCommandsコグがアンロードされました。")

async def setup(bot):
    await bot.add_cog(PjskRandomSongCommands(bot))