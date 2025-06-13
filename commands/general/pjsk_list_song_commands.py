import discord
from discord.ext import commands
import discord.app_commands
import logging

# data/songs.py から情報をインポート
try:
    from data import songs
except ImportError:
    logging.critical("致命的なエラー: data/songs.py が見つからないか、インポートできませんでした。")
    raise SystemExit("data/songs.py が見つかりません。")

# admin_commands から not_in_maintenance をインポート
from commands.admin.admin_commands import not_in_maintenance

logger = logging.getLogger(__name__)

class PjskListSongCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("PjskListSongCommandsコグが初期化されています。")

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

    @discord.app_commands.command(name="pjsk_list_song", description="プロセカの曲リストを表示します。フィルタリングも可能です。")
    @discord.app_commands.describe(
        min_level="最小レベル (1-37)",
        max_level="最大レベル (1-37)",
        difficulties="難易度タイプでフィルタ (カンマ区切り例: MASTER,EXPERT)",
        title_keyword="タイトルに含むキーワードでフィルタ"
    )
    @not_in_maintenance() # メンテナンスモード中は利用不可
    async def pjsk_list_song(
        self,
        interaction: discord.Interaction,
        min_level: discord.app_commands.Range[int, 1, 37] = None,
        max_level: discord.app_commands.Range[int, 1, 37] = None,
        difficulties: str = None,
        title_keyword: str = None
    ):
        await interaction.response.defer() # 処理に時間がかかる可能性があるため、deferで応答を保留

        if not songs.proseka_songs:
            await interaction.followup.send("曲データが見つかりませんでした。", ephemeral=True)
            logger.warning("警告: /pjsk_list_song コマンドが実行されましたが、proseka_songs が空でした。")
            return

        try:
            filtered_songs = []

            # 難易度タイプのパース
            selected_difficulty_types_from_input = []
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
            difficulties_for_filtering = selected_difficulty_types_from_input if selected_difficulty_types_from_input else self.ALL_DIFFICULTY_TYPES

            # フィルタリングロジック
            for song in songs.proseka_songs:
                # タイトルキーワードフィルタ
                if title_keyword and title_keyword.lower() not in song.get('title', '').lower():
                    continue

                song_matches_criteria = False
                if not difficulties_for_filtering and min_level is None and max_level is None:
                    # 難易度やレベルの指定がない場合は、どの難易度でもOKとみなす
                    song_matches_criteria = True
                else:
                    for diff_type in difficulties_for_filtering:
                        if diff_type in song and song[diff_type] is not None:
                            level = song[diff_type]
                            level_in_range = True
                            if min_level is not None and level < min_level:
                                level_in_range = False
                            if max_level is not None and level > max_level:
                                level_in_range = False
                            
                            if level_in_range:
                                song_matches_criteria = True
                                break # この曲はこの難易度で条件を満たした

                if song_matches_criteria:
                    filtered_songs.append(song)

            if not filtered_songs:
                await interaction.followup.send(
                    "指定された条件に合う曲が見つかりませんでした。条件を緩和してみてください。",
                    ephemeral=True
                )
                logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song コマンドを使用しましたが、条件に合う曲が見つかりませんでした。min_level={min_level}, max_level={max_level}, difficulties_selected={difficulties_for_filtering}, title_keyword='{title_keyword}'")
                return

            # 結果のソート (タイトル順)
            filtered_songs.sort(key=lambda s: s.get('title', ''))

            # Embedに表示する文字列を生成
            song_entries = []
            for song in filtered_songs:
                diff_levels = []
                for diff_type_key in self.ALL_DIFFICULTY_TYPES:
                    if diff_type_key in song and song[diff_type_key] is not None:
                        # フィルタリングされた難易度タイプのみ表示、または全表示
                        if not selected_difficulty_types_from_input or diff_type_key in selected_difficulty_types_from_input:
                            diff_levels.append(f"{self.DISPLAY_DIFFICULTY_TYPES[diff_type_key]}: {song[diff_type_key]}")
                
                # 表示する難易度情報が空の場合のFallback
                if not diff_levels and (min_level is not None or max_level is not None or selected_difficulty_types_from_input):
                    # レベルや難易度指定がある場合は、条件に合わない譜面レベルは表示しない
                    pass
                elif not diff_levels: # レベルや難易度指定なしで、譜面情報もなし
                    diff_levels.append("難易度情報なし")

                song_entry = f"**{song.get('title', 'タイトル不明')}**\n" \
                             f"  {', '.join(diff_levels)}\n"
                song_entries.append(song_entry)

            # 複数のEmbedに分割して送信
            embeds = []
            current_embed_description = []
            current_embed_length = 0
            max_description_length = 3500 # Discordのdescription制限より少し少なめに設定

            for entry in song_entries:
                if current_embed_length + len(entry) > max_description_length:
                    # 新しいEmbedを作成して追加
                    embed = discord.Embed(
                        title="プロセカ楽曲リスト",
                        description="".join(current_embed_description),
                        color=discord.Color.blue()
                    )
                    embeds.append(embed)
                    current_embed_description = []
                    current_embed_length = 0
                
                current_embed_description.append(entry)
                current_embed_length += len(entry)
            
            # 最後のEmbedを追加
            if current_embed_description:
                embed = discord.Embed(
                    title="プロセカ楽曲リスト",
                    description="".join(current_embed_description),
                    color=discord.Color.blue()
                )
                embeds.append(embed)

            # Embedを送信
            if embeds:
                for i, embed in enumerate(embeds):
                    # 最初のEmbedにのみフッターを追加
                    if i == 0:
                        embed.set_footer(text=f"合計: {len(filtered_songs)}件 | ページ {i+1}/{len(embeds)}")
                    else:
                        embed.set_footer(text=f"ページ {i+1}/{len(embeds)}")
                    
                    if i == 0: # 最初のEmbedはfollowup.sendで
                        await interaction.followup.send(embed=embed)
                    else: # 2番目以降はinteraction.channel.sendで
                        await interaction.channel.send(embed=embed)
                logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song コマンドを使用しました。{len(filtered_songs)}件の曲がフィルタリングされ、{len(embeds)}件のEmbedで表示されました。")
            else:
                await interaction.followup.send("リスト表示中にエラーが発生しました。", ephemeral=True)
                logger.error("エラー: /pjsk_list_song コマンドでEmbedを生成できませんでした。")

        except Exception as e:
            await interaction.followup.send(f"曲リストの取得中にエラーが発生しました: {e}", ephemeral=True)
            logger.error(f"エラー: /pjsk_list_song コマンドの実行中に予期せぬエラーが発生しました: {e}", exc_info=True)

    async def cog_load(self):
        logger.info("PjskListSongCommandsコグがロードされました。")

    async def cog_unload(self):
        logger.info("PjskListSongCommandsコグがアンロードされました。")

async def setup(bot):
    await bot.add_cog(PjskListSongCommands(bot))