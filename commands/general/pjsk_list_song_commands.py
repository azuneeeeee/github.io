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

# --- PjskListView クラスの定義 (ページング・ソートボタン用) ---
class PjskListView(discord.ui.View):
    # ソート順の定数を見直し
    SORT_REGISTER = "register"      # 初期登録順 (実際のデータ順)
    SORT_INDEX_ASC = "index_asc"    # 登録順を基準とした昇順 (正順)
    SORT_INDEX_DESC = "index_desc"  # 登録順を基準とした降順 (逆順)

    def __init__(self, song_data, original_interactor_id, current_page=0, sort_order=SORT_REGISTER):
        super().__init__(timeout=86400) # タイムアウトを24時間 (86400秒) に設定
        self.original_song_data = list(song_data) # 元の登録順のデータを保持 (ソートのベースとして保持)
        self.original_interactor_id = original_interactor_id
        self._sorted_song_data = self._sort_songs(self.original_song_data, sort_order) # ソート済みのデータを保持
        self.current_page = current_page
        self.songs_per_page = 10 # 1ページあたりの曲数
        self.sort_order = sort_order # 現在のソート順
        
        # ソート後に最大ページ数を再計算
        self.max_pages = (len(self._sorted_song_data) + self.songs_per_page - 1) // self.songs_per_page
        if self.max_pages == 0: # 曲がない場合
            self.max_pages = 1 # 少なくとも1ページとして扱う
        
        # 現在のページが最大ページを超えないように調整
        if self.current_page >= self.max_pages:
            self.current_page = self.max_pages - 1
        if self.current_page < 0:
            self.current_page = 0

        # ここでボタンの状態を設定
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.max_pages - 1)
        
        # ★単一の昇順/降順トグルボタンのラベルとスタイルを設定★
        if self.sort_order == self.SORT_INDEX_ASC:
            self.toggle_order_button.label = "降順" # 現在が昇順なので、次は降順に切り替わる
            self.toggle_order_button.style = discord.ButtonStyle.green
        elif self.sort_order == self.SORT_INDEX_DESC:
            self.toggle_order_button.label = "昇順" # 現在が降順なので、次は昇順に切り替わる
            self.toggle_order_button.style = discord.ButtonStyle.green
        else: # self.sort_order == self.SORT_REGISTER (初期状態または登録順に戻された場合)
            self.toggle_order_button.label = "昇順" # 登録順からスタートする場合は、次は昇順にソートできるようにする
            self.toggle_order_button.style = discord.ButtonStyle.grey # デフォルトの色

        logger.debug(f"PjskListView: 初期化完了。総曲数: {len(song_data)}, 最大ページ: {self.max_pages}, 初期ページ: {self.current_page}, インタラクターID: {self.original_interactor_id}, ソート順: {self.sort_order}")

    def _sort_songs(self, songs_list, order):
        if order == self.SORT_INDEX_ASC or order == self.SORT_REGISTER: # 昇順または登録順の場合 (登録順は昇順と同じ挙動)
            return list(songs_list) # 元のリストのコピー (インデックス昇順)
        elif order == self.SORT_INDEX_DESC: # 降順の場合
            return list(reversed(songs_list)) # 元のリストを逆順にしたコピー
        else: # 未知のソート順が指定された場合は登録順(昇順)をデフォルトとする
            logger.warning(f"未知のソート順が指定されました: {order}。登録順でソートします。")
            return list(songs_list)

    def get_page_embed(self):
        start_index = self.current_page * self.songs_per_page
        end_index = start_index + self.songs_per_page
        
        # 現在のソート順でソートされたデータを使用
        page_songs = self._sorted_song_data[start_index:end_index]

        song_entries = []
        
        for i, song in enumerate(page_songs):
            # 表示される番号は、常にソートされたリストの実際のインデックス + 1 になります。
            song_entry = f"{start_index + i + 1}. **{song.get('title', 'タイトル不明')}**\n"
            song_entries.append(song_entry)

        full_description = "".join(song_entries)
        if not full_description:
            full_description = "表示できる曲がありませんでした。"

        # Embedタイトルにソート順を反映
        sort_label = {
            self.SORT_REGISTER: "登録順", 
            self.SORT_INDEX_ASC: "昇順",
            self.SORT_INDEX_DESC: "降順"
        }.get(self.sort_order, "不明な順")

        embed = discord.Embed(
            title=f"プロセカ楽曲リスト ({sort_label})",
            description=full_description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"全{len(self.original_song_data)}件中、{start_index + 1}-{min(end_index, len(self._sorted_song_data))}件を表示 | ページ {self.current_page + 1}/{self.max_pages}")
        logger.debug(f"PjskListView: Embed生成完了。ページ: {self.current_page + 1}/{self.max_pages}, ソート順: {self.sort_order}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.original_interactor_id:
            logger.debug(f"PjskListView: interaction_check OK for user ID {interaction.user.id}")
            return True
        else:
            await interaction.response.send_message("このボタンはコマンドを実行したユーザーのみ操作できます。", ephemeral=True)
            logger.warning(f"PjskListView: 不正なユーザーによるボタン操作: ユーザーID {interaction.user.id}, オリジナルインタラクターID {self.original_interactor_id}")
            return False

    async def _update_page_and_view(self, interaction: discord.Interaction):
        # Viewを更新し、メッセージを編集するヘルパー
        self.stop() # 現在のビューを停止
        # 新しいビューを作成し、現在の状態 (original_song_data, current_page, sort_order) を引き継ぐ
        new_view = PjskListView(self.original_song_data, self.original_interactor_id, self.current_page, self.sort_order) 
        await interaction.response.edit_message(embed=new_view.get_page_embed(), view=new_view)
        new_view.message = interaction.message # 新しいビューに現在のメッセージを紐付け
        
    @discord.ui.button(label="⬅️前のページ", style=discord.ButtonStyle.blurple, custom_id="prev_page", row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self._update_page_and_view(interaction)
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のページを戻りました。現在のページ: {self.current_page + 1}")
        else:
            await interaction.response.defer()

    @discord.ui.button(label="次のページ➡️", style=discord.ButtonStyle.blurple, custom_id="next_page", row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            await self._update_page_and_view(interaction)
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のページを進みました。現在のページ: {self.current_page + 1}")
        else:
            await interaction.response.defer()
            
    # ★★★ 単一の昇順/降順トグルボタン (タイトル順にはソートしない) ★★★
    # ラベルは動的に設定されるため、ここでは仮のラベルを設定 (あるいは設定しない)
    @discord.ui.button(label="ソート", style=discord.ButtonStyle.grey, custom_id="toggle_index_order", row=1)
    async def toggle_order_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.debug(f"PjskListView: '昇順/降順' トグルボタンがクリックされました。現在のソート順: {self.sort_order}")
        
        if self.sort_order == self.SORT_INDEX_ASC:
            # 現在が昇順なら、次は降順にする
            self.sort_order = self.SORT_INDEX_DESC
        elif self.sort_order == self.SORT_INDEX_DESC:
            # 現在が降順なら、次は昇順にする
            self.sort_order = self.SORT_INDEX_ASC
        else: # self.SORT_REGISTER (登録順の場合)
            # 登録順からスタートする場合は、最初は昇順にする
            self.sort_order = self.SORT_INDEX_ASC

        self._sorted_song_data = self._sort_songs(self.original_song_data, self.sort_order)
        
        # ソート後は現在のページを調整
        self.max_pages = (len(self._sorted_song_data) + self.songs_per_page - 1) // self.songs_per_page
        if self.max_pages == 0: self.max_pages = 1
        if self.current_page >= self.max_pages: self.current_page = self.max_pages - 1
        if self.current_page < 0: self.current_page = 0
        
        await self._update_page_and_view(interaction)
        logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のソートを切り替えました。新しいソート順: {self.sort_order}")

    async def on_timeout(self):
        # タイムアウト時にボタンを無効化する
        for item in self.children:
            item.disabled = True
        if self.message: # メッセージが紐付けられていれば編集
            await self.message.edit(view=self)
            logger.info("PjskListView: タイムアウトしました。ボタンを無効化しました。")


class PjskListSongCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("PjskListSongCommandsコグが初期化されています。")

    # このコマンドでは使われませんが、削除はしていません
    ALL_DIFFICULTY_TYPES = ["easy", "normal", "hard", "expert", "master", "append"]
    DISPLAY_DIFFICULTY_TYPES = {
        "easy": "EASY",
        "normal": "NORMAL",
        "hard": "HARD",
        "expert": "EXPERT",
        "master": "MASTER",
        "append": "APPEND"
    }

    @discord.app_commands.command(name="pjsk_list_song", description="プロセカの全曲リストをページ表示し、ソートできます。")
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

            # 初期表示は登録順
            view = PjskListView(all_songs, interaction.user.id, sort_order=PjskListView.SORT_REGISTER) 
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