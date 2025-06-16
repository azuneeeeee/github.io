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
    # 各難易度のレベル順の基底
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

    # セレクトメニューのオプションを生成するヘルパーメソッド
    def _get_sort_options_list(self): # メソッド名を変更して混乱を避ける
        options = [
            discord.SelectOption(label="配信順", value=self.SORT_DEFAULT, description="ゲームへの配信順で並べ替えます。"),
            discord.SelectOption(label="50音順", value=self.SORT_JAPANESE_ALPHA, description="楽曲タイトルを50音順で並べ替えます。"),
        ]
        # 各難易度のレベル順オプションを追加
        for key, display_name in self.DIFFICULTY_MAPPING.items():
            options.append(
                discord.SelectOption(
                    label=f"{display_name} Lv順", 
                    value=f"{self.SORT_LEVEL_BASE}{key}", 
                    description=f"{display_name}難易度のレベル順で並べ替えます。"
                )
            )
        return options

    def __init__(self, song_data, original_interactor_id, current_page=0, sort_method=SORT_DEFAULT):
        super().__init__(timeout=86400) # タイムアウトを24時間 (86400秒) に設定
        self.original_song_data = list(song_data) # 元の登録順のデータを保持 (ソートのベースとして保持)
        self.original_interactor_id = original_interactor_id
        self.sort_method = sort_method # 現在のソート方法
        
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

        # Selectメニューをインスタンス化し、optionsを設定して追加
        current_sort_label = {
            self.SORT_DEFAULT: "配信順", 
            self.SORT_JAPANESE_ALPHA: "50音順",
            **{f"{self.SORT_LEVEL_BASE}{key}": f"{value} Lv順" for key, value in self.DIFFICULTY_MAPPING.items()}
        }.get(self.sort_method, "ソート方法を選択...")

        sort_select = discord.ui.Select(
            placeholder=f"現在のソート: {current_sort_label}",
            options=self._get_sort_options_list(), 
            custom_id="sort_options_select",
            row=1 
        )
        sort_select.callback = self.sort_options_select_callback
        self.add_item(sort_select)

        logger.debug(f"PjskListView: 初期化完了。総曲数: {len(song_data)}, 最大ページ: {self.max_pages}, 初期ページ: {self.current_page}, インタラクターID: {self.original_interactor_id}, ソート方法: {self.sort_method}")

    def _sort_songs(self, songs_list, method):
        logger.debug(f"_sort_songs: ソート方法 '{method}' でソートを開始します。")

        # ソート対象となる曲リスト
        filtered_songs = list(songs_list) # まずは元のリストのコピー
        
        # ★★★ APPEND Lv順の場合のみフィルタリングを実行 ★★★
        if method == self.SORT_APPEND_LEVEL:
            original_count = len(filtered_songs)
            temp_filtered = []
            for song in filtered_songs:
                # songに 'append' キーがあり、かつその値が数値であることを確認
                append_level = song.get("append")
                if isinstance(append_level, (int, float)):
                    temp_filtered.append(song)
                else:
                    logger.debug(f"  _sort_songs: APPEND Lv順ソートのため、曲 '{song.get('title', '不明なタイトル')}' はAPPENDレベルがないため除外されました。")
            filtered_songs = temp_filtered
            logger.debug(f"  _sort_songs: APPEND Lv順ソートで {original_count} 曲中 {len(filtered_songs)} 曲がフィルタリングされました。")


        if method == self.SORT_DEFAULT:
            logger.debug("_sort_songs: 配信順でソートします。")
            return list(filtered_songs) # フィルタリング後のリストを返す

        elif method == self.SORT_JAPANESE_ALPHA:
            logger.debug("_sort_songs: 50音順でソートします。")
            return sorted(filtered_songs, key=lambda s: s.get('title', ''))

        elif method.startswith(self.SORT_LEVEL_BASE):
            difficulty_key = method.replace(self.SORT_LEVEL_BASE, "")
            logger.debug(f"_sort_songs: {difficulty_key.upper()} のレベル順でソートします。")
            
            def get_level(song):
                level = song.get(difficulty_key) 
                
                if level is None:
                    logger.debug(f"  _sort_songs.get_level: 曲 '{song.get('title', '不明なタイトル')}' に難易度 '{difficulty_key}' のレベル情報がありません。")
                elif not isinstance(level, (int, float)):
                    logger.warning(f"  _sort_songs.get_level: 曲 '{song.get('title', '不明なタイトル')}' の難易度 '{difficulty_key}' のレベルが数値ではありません。値: {level}")

                if isinstance(level, (int, float)): 
                    return level
                
                return float('inf') 

            sorted_data = sorted(filtered_songs, key=lambda s: (get_level(s), s.get('title', '')))
            return sorted_data
        
        else:
            logger.warning(f"_sort_songs: 未知のソート方法が指定されました: {method}。デフォルトでソートします。")
            return list(filtered_songs) # フィルタリング後のリストを返す

    def get_page_embed(self):
        start_index = self.current_page * self.songs_per_page
        end_index = start_index + self.songs_per_page
        
        page_songs = self._sorted_song_data[start_index:end_index]

        song_entries = []
        
        for i, song in enumerate(page_songs):
            display_num = start_index + i + 1
            title = song.get('title', 'タイトル不明')
            
            level_info = ""
            # 現在のソート方法が難易度レベルソートの場合のみレベル情報を表示
            if self.sort_method.startswith(self.SORT_LEVEL_BASE):
                difficulty_key = self.sort_method.replace(self.SORT_LEVEL_BASE, "")
                level = song.get(difficulty_key) 
                if isinstance(level, (int, float)): 
                    level_info = f" (Lv.{level})"
            
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
        # フッターの総件数はフィルタリング後の数ではなく、元の全曲数（フィルタリングされた場合も含む）を表示するのが一般的だが、
        # ここではフィルタリング後のソート済みデータ長を使用し、表示されている件数を正確に反映させる
        # ただし、フッターの「全X件中」のXは original_song_data の長さを使うのがよりユーザーフレンドリー
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
            
    async def sort_options_select_callback(self, interaction: discord.Interaction):
        selected_value = interaction.data['values'][0]
        logger.debug(f"PjskListView: ソートオプションが選択されました: {selected_value}")

        self.sort_method = selected_value 
        self.current_page = 0 
        await self._update_page_and_view(interaction)
        logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のソート方法を {self.sort_method} に切り替えました。")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message: 
            await self.message.edit(view=self)
            logger.info("PjskListView: タイムアウトしました。UIを無効化しました。")


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