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

# --- PjskListView クラスの定義 (ページング・ソート選択メニュー用) ---
class PjskListView(discord.ui.View):
    # ソート方法の定数
    SORT_DEFAULT = "default"        # 配信順 (元の登録順)
    SORT_JAPANESE_ALPHA = "japanese_alpha" # 50音順 (タイトル昇順)
    # 各難易度のレベル順ソートの基底
    SORT_LEVEL_BASE = "level_" 
    SORT_EASY_LEVEL = "level_easy"
    SORT_NORMAL_LEVEL = "level_normal"
    SORT_HARD_LEVEL = "level_hard"
    SORT_EXPERT_LEVEL = "level_expert"
    SORT_MASTER_LEVEL = "level_master"
    SORT_APPEND_LEVEL = "level_append"

    DIFFICULTY_MAPPING = {
        "easy": "EASY",
        "normal": "NORMAL",
        "hard": "HARD",
        "expert": "EXPERT",
        "master": "MASTER",
        "append": "APPEND"
    }

    def __init__(self, song_data, original_interactor_id, current_page=0, sort_method=SORT_DEFAULT):
        super().__init__(timeout=86400) # タイムアウトを24時間 (86400秒) に設定
        self.original_song_data = list(song_data) # 元の登録順のデータを保持 (ソートのベースとして保持)
        self.original_interactor_id = original_interactor_id
        self.sort_method = sort_method # 現在のソート方法 (例: "default", "japanese_alpha", "level_expert" など)
        
        # ソート実行
        self._sorted_song_data = self._sort_songs(self.original_song_data, self.sort_method) 
        
        self.current_page = current_page
        self.songs_per_page = 10 # 1ページあたりの曲数
        
        # ソート後に最大ページ数を再計算
        self.max_pages = (len(self._sorted_song_data) + self.songs_per_page - 1) // self.songs_per_page
        if self.max_pages == 0: 
            self.max_pages = 1 
        
        # 現在のページが最大ページを超えないように調整
        if self.current_page >= self.max_pages:
            self.current_page = self.max_pages - 1
        if self.current_page < 0:
            self.current_page = 0

        # ここでボタンの状態を設定
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.max_pages - 1)

        # ★ソート選択メニューの初期値設定★
        # current_sort_value は、ソート方法と、もしレベルソートなら難易度を結合した値
        # 例: "default", "japanese_alpha", "level_easy"
        self.main_sort_select.current_sort_value = self.sort_method 
        
        # ★難易度選択メニューの表示・非表示と初期値設定★
        # 現在のソート方法がレベルソートの場合のみ、難易度選択メニューを追加する
        if self.sort_method.startswith(self.SORT_LEVEL_BASE):
            selected_difficulty_key = self.sort_method.replace(self.SORT_LEVEL_BASE, "")
            self.difficulty_select.current_difficulty_value = selected_difficulty_key
            self.add_item(self.difficulty_select) # Viewに難易度選択メニューを追加
        else:
            # レベルソートではない場合、難易度選択メニューは表示しない
            # この View を再構築する際に、もし以前の View で難易度セレクタがあったとしても
            # 新しい View インスタンスでは条件に合致しなければ追加されない
            pass 

        logger.debug(f"PjskListView: 初期化完了。総曲数: {len(song_data)}, 最大ページ: {self.max_pages}, 初期ページ: {self.current_page}, インタラクターID: {self.original_interactor_id}, ソート方法: {self.sort_method}")

    def _sort_songs(self, songs_list, method):
        if method == self.SORT_DEFAULT:
            return list(songs_list) # 元の登録順のコピー

        elif method == self.SORT_JAPANESE_ALPHA:
            # 50音順ソート (タイトルでソート)
            # 全角カタカナに変換してソートすることで、より正確な50音順ソートを実現
            # PyKakasiなど外部ライブラリを使うとより厳密だが、ここでは簡易的に文字列比較
            return sorted(songs_list, key=lambda s: s.get('title', ''))

        elif method.startswith(self.SORT_LEVEL_BASE):
            difficulty_key = method.replace(self.SORT_LEVEL_BASE, "")
            
            def get_level(song):
                # 難易度情報が辞書形式で存在し、指定された難易度のレベルがあればそれを返す
                # なければ非常に大きな値を返してリストの最後にする
                difficulties = song.get('difficulties', {})
                level_data = difficulties.get(difficulty_key)
                if level_data and 'level' in level_data:
                    return level_data['level']
                return float('inf') # レベルがない曲は最後に配置

            # まずレベルでソートし、同じレベルの場合はタイトルでソート
            return sorted(songs_list, key=lambda s: (get_level(s), s.get('title', '')))
        
        else: # 未知のソート方法が指定された場合はデフォルトを返す
            logger.warning(f"未知のソート方法が指定されました: {method}。デフォルトでソートします。")
            return list(songs_list)

    def get_page_embed(self):
        start_index = self.current_page * self.songs_per_page
        end_index = start_index + self.songs_per_page
        
        page_songs = self._sorted_song_data[start_index:end_index]

        song_entries = []
        
        for i, song in enumerate(page_songs):
            display_num = start_index + i + 1
            title = song.get('title', 'タイトル不明')
            
            level_info = ""
            if self.sort_method.startswith(self.SORT_LEVEL_BASE):
                difficulty_key = self.sort_method.replace(self.SORT_LEVEL_BASE, "")
                difficulties = song.get('difficulties', {})
                level_data = difficulties.get(difficulty_key)
                if level_data and 'level' in level_data:
                    level_info = f" (Lv.{level_data['level']})"
            
            song_entry = f"{display_num}. **{title}**{level_info}\n"
            song_entries.append(song_entry)

        full_description = "".join(song_entries)
        if not full_description:
            full_description = "表示できる曲がありませんでした。"

        # Embedタイトルにソート方法を反映
        sort_label = {
            self.SORT_DEFAULT: "配信順", 
            self.SORT_JAPANESE_ALPHA: "50音順",
            **{f"{self.SORT_LEVEL_BASE}{key}": f"{value} Lv順" for key, value in self.DIFFICULTY_MAPPING.items()}
        }.get(self.sort_method, "不明なソート順")

        embed = discord.Embed(
            title=f"プロセカ楽曲リスト ({sort_label})",
            description=full_description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"全{len(self.original_song_data)}件中、{start_index + 1}-{min(end_index, len(self._sorted_song_data))}件を表示 | ページ {self.current_page + 1}/{self.max_pages}")
        logger.debug(f"PjskListView: Embed生成完了。ページ: {self.current_page + 1}/{self.max_pages}, ソート方法: {self.sort_method}")
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
        # 新しいビューを作成し、現在の状態を引き継ぐ
        new_view = PjskListView(self.original_song_data, self.original_interactor_id, self.current_page, self.sort_method) 
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
            
    # ★★★ ソート方法選択メニュー ★★★
    @discord.ui.select(
        cls=discord.ui.Select, # 型ヒントのために cls を明示的に指定
        placeholder="ソート方法を選択...",
        options=[
            discord.SelectOption(label="配信順", value="default", description="ゲームへの配信順で並べ替えます。"),
            discord.SelectOption(label="50音順", value="japanese_alpha", description="楽曲タイトルを50音順で並べ替えます。"),
            discord.SelectOption(label="難易度レベル順", value="level_select", description="難易度を選択してレベル順で並べ替えます。")
        ],
        custom_id="main_sort_select",
        row=1 # ページングボタンの下に配置
    )
    async def main_sort_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_value = select.values[0]
        logger.debug(f"PjskListView: ソート方法が選択されました: {selected_value}")

        if selected_value == self.SORT_DEFAULT:
            self.sort_method = self.SORT_DEFAULT
            self.current_page = 0 # ソート方法が変わったら最初のページに戻る
            await self._update_page_and_view(interaction)
        elif selected_value == self.SORT_JAPANESE_ALPHA:
            self.sort_method = self.SORT_JAPANESE_ALPHA
            self.current_page = 0 
            await self._update_page_and_view(interaction)
        elif selected_value == "level_select":
            # 難易度レベル順が選択された場合、難易度選択メニューを追加/表示するため、Viewを再構築
            # ただし、まだ具体的な難易度は選択されていないので、ソート方法は変更しないでおく
            # ここでは Embed を更新せず、難易度選択メニューを追加した View を送り返す
            # あるいは、デフォルトで MASTER_LEVEL にソートしておくなどの方針も考えられる
            # 今回は、難易度選択が必須になるため、まずは難易度選択メニューを表示させる
            # デフォルトとして MASTER Lv順を仮に適用する
            self.sort_method = self.SORT_MASTER_LEVEL # デフォルトでMaster Lv順にする
            self.current_page = 0
            await self._update_page_and_view(interaction)
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のソート方法を難易度レベル順に切り替えました。")
        else:
            await interaction.response.send_message("無効なソート方法が選択されました。", ephemeral=True)
            logger.warning(f"PjskListView: 無効なソート方法が選択されました: {selected_value}")

    # ★★★ 難易度選択メニュー (難易度レベル順が選択された場合に表示) ★★★
    @discord.ui.select(
        cls=discord.ui.Select,
        placeholder="難易度を選択...",
        options=[
            discord.SelectOption(label="EASY", value="easy"),
            discord.SelectOption(label="NORMAL", value="normal"),
            discord.SelectOption(label="HARD", value="hard"),
            discord.SelectOption(label="EXPERT", value="expert"),
            discord.SelectOption(label="MASTER", value="master"),
            discord.SelectOption(label="APPEND", value="append")
        ],
        custom_id="difficulty_select",
        row=2 # ソート方法選択メニューの下に配置
    )
    async def difficulty_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_difficulty = select.values[0]
        logger.debug(f"PjskListView: 難易度が選択されました: {selected_difficulty}")
        
        # 選択された難易度でソート方法を更新
        self.sort_method = f"{self.SORT_LEVEL_BASE}{selected_difficulty}"
        self.current_page = 0 # ソート方法が変わったら最初のページに戻る
        await self._update_page_and_view(interaction)
        logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のソート難易度を {selected_difficulty} に切り替えました。")

    async def on_timeout(self):
        # タイムアウト時に全てのUIコンポーネントを無効化する
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

            # 初期表示は「配信順」
            # Viewの初期化時にソート方法を渡す
            view = PjskListView(all_songs, interaction.user.id, sort_method=PjskListView.SORT_DEFAULT) 
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