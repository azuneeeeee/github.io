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

# --- PjskListView クラスの定義 (ページングボタン用) ---
class PjskListView(discord.ui.View):
    def __init__(self, song_data, current_page=0):
        super().__init__(timeout=300) # タイムアウトを5分 (300秒) に設定
        self.song_data = song_data
        self.current_page = current_page
        self.songs_per_page = 10 # 1ページあたりの曲数
        self.max_pages = (len(self.song_data) + self.songs_per_page - 1) // self.songs_per_page
        self.update_buttons()
        logger.debug(f"PjskListView: 初期化完了。総曲数: {len(song_data)}, 最大ページ: {self.max_pages}, 初期ページ: {self.current_page}")

    def update_buttons(self):
        # ボタンを全てクリアして再構築
        self.clear_items()
        
        # Previous ボタン
        # ★★★ ここを修正 ★★★
        prev_button = discord.ui.Button(label="⬅️前のページ", style=discord.ButtonStyle.blurple, custom_id="prev_page", disabled=(self.current_page == 0))
        prev_button.callback = self.go_previous_page
        self.add_item(prev_button)

        # Next ボタン
        # ★★★ ここを修正 ★★★
        next_button = discord.ui.Button(label="次のページ➡️", style=discord.ButtonStyle.blurple, custom_id="next_page", disabled=(self.current_page >= self.max_pages - 1))
        next_button.callback = self.go_next_page
        self.add_item(next_button)
        logger.debug(f"PjskListView: ボタン更新完了。現在のページ: {self.current_page}, Previousボタン無効: {prev_button.disabled}, Nextボタン無効: {next_button.disabled}")

    def get_page_embed(self):
        start_index = self.current_page * self.songs_per_page
        end_index = start_index + self.songs_per_page
        page_songs = self.song_data[start_index:end_index]

        song_entries = []
        
        for i, song in enumerate(page_songs):
            song_entry = f"{start_index + i + 1}. **{song.get('title', 'タイトル不明')}**\n"
            song_entries.append(song_entry)

        full_description = "".join(song_entries)
        if not full_description:
            full_description = "表示できる曲がありませんでした。"

        embed = discord.Embed(
            title="プロセカ楽曲リスト",
            description=full_description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"全{len(self.song_data)}件中、{start_index + 1}-{min(end_index, len(self.song_data))}件を表示 | ページ {self.current_page + 1}/{self.max_pages}")
        logger.debug(f"PjskListView: Embed生成完了。ページ: {self.current_page + 1}/{self.max_pages}")
        return embed

    async def go_previous_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のページを戻りました。現在のページ: {self.current_page + 1}")
        else:
            await interaction.response.defer()

    async def go_next_page(self, interaction: discord.Interaction):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_page_embed(), view=self)
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のページを進みました。現在のページ: {self.current_page + 1}")
        else:
            await interaction.response.defer()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        logger.info("PjskListView: タイムアウトしました。ボタンを無効化しました。")


class PjskListSongCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("PjskListSongCommandsコグが初期化されています。")

    ALL_DIFFICULTY_TYPES = ["easy", "normal", "hard", "expert", "master", "append"]
    DISPLAY_DIFFICULTY_TYPES = {
        "easy": "EASY",
        "normal": "NORMAL",
        "hard": "HARD",
        "expert": "EXPERT",
        "master": "MASTER",
        "append": "APPEND"
    }

    @discord.app_commands.command(name="pjsk_list_song", description="プロセカの全曲リストをページ表示します。")
    @not_in_maintenance()
    async def pjsk_list_song(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer() 

        if not songs.proseka_songs:
            await interaction.followup.send("曲データが見つかりませんでした。", ephemeral=True)
            logger.warning("警告: /pjsk_list_song コマンドが実行されましたが、proseka_songs が空でした。")
            return

        try:
            all_songs = list(songs.proseka_songs) 

            if not all_songs:
                await interaction.followup.send(
                    "曲データが見つかりませんでした。",
                    ephemeral=True
                )
                logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song コマンドを使用しましたが、曲が見つかりませんでした。")
                return

            view = PjskListView(all_songs)
            initial_embed = view.get_page_embed()
            
            message = await interaction.followup.send(embed=initial_embed, view=view)
            view.message = message 

            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song コマンドを使用しました。最初のページが送信されました。")

        except Exception as e:
            await interaction.followup.send(f"曲リストの取得中にエラーが発生しました: {e}", ephemeral=True)
            logger.error(f"エラー: /pjsk_list_song コマンドの実行中に予期せぬエラーが発生しました: {e}", exc_info=True)

    async def cog_load(self):
        logger.info("PjskListSongCommandsコグがロードされました。")

    async def cog_unload(self):
        logger.info("PjskListSongCommandsコグがアンロードされました。")

async def setup(bot):
    await bot.add_cog(PjskListSongCommands(bot))