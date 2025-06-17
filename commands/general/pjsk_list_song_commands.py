import discord
from discord.ext import commands
import discord.app_commands
import logging
import os
import importlib.util

try:
    from data import songs # songs.pyは変更しないが、楽曲リストはここから取得
except ImportError:
    logging.critical("致命的なエラー: data/songs.py が見つからないか、インポートできませんでした。")
    raise SystemExit("data/songs.py が見つかりません。")

from commands.admin.admin_commands import not_in_maintenance

logger = logging.getLogger(__name__)

# 楽曲詳細フォルダのベースパスを設定
BASE_SONG_DETAILS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'data', '楽曲詳細')
)

# 楽曲タイトルと対応するユニットフォルダ名のマッピングを保持する辞書
# key: 楽曲タイトル (songs.pyのタイトル), value: ユニットフォルダ名
_song_title_to_unit_folder_map = {}


def sanitize_filename(filename: str) -> str:
    """
    ファイル名として安全な文字列に変換します。
    スペースをアンダースコアに、その他ファイル名に使えない文字を置き換えます。
    """
    filename = filename.replace(' ', '_').replace('　', '_') # 半角・全角スペースをアンダースコアに
    invalid_chars = r'\/:*?"<>|' # Windowsで無効な文字
    for char in invalid_chars:
        filename = filename.replace(char, '_') 
    
    return filename


def build_song_unit_mapping():
    """
    data/楽曲詳細 以下のフォルダ構造をスキャンし、楽曲タイトルとユニットフォルダ名のマッピングを構築する。
    Bot起動時に一度だけ実行される。
    """
    logger.info(f"楽曲詳細フォルダからユニットマッピングを構築中: {BASE_SONG_DETAILS_DIR}")
    _song_title_to_unit_folder_map.clear() # 既存のマッピングをクリア

    if not os.path.exists(BASE_SONG_DETAILS_DIR):
        logger.warning(f"楽曲詳細のベースディレクトリが見つかりません: {BASE_SONG_DETAILS_DIR}")
        return

    for unit_folder_name in os.listdir(BASE_SONG_DETAILS_DIR):
        unit_folder_path = os.path.join(BASE_SONG_DETAILS_DIR, unit_folder_name)
        if os.path.isdir(unit_folder_path):
            logger.debug(f"ユニットフォルダを検出: {unit_folder_name}")
            for filename in os.listdir(unit_folder_path):
                if filename.endswith(".py"):
                    song_title_candidate_from_file = os.path.splitext(filename)[0]
                    
                    found_match = False
                    for song_in_songs_py in songs.proseka_songs:
                        proseka_title = song_in_songs_py.get('title')
                        if proseka_title:
                            sanitized_proseka_title = sanitize_filename(proseka_title)
                            
                            if song_title_candidate_from_file == sanitized_proseka_title:
                                if proseka_title in _song_title_to_unit_folder_map:
                                    logger.warning(f"警告: 楽曲 '{proseka_title}' が複数のユニットフォルダ ({_song_title_to_unit_folder_map[proseka_title]} と {unit_folder_name}) で見つかりました。最初に見つかったものを使用します。")
                                else:
                                    _song_title_to_unit_folder_map[proseka_title] = unit_folder_name
                                logger.debug(f"マッピング追加: '{proseka_title}' -> '{unit_folder_name}'")
                                found_match = True
                                break 
                    
                    if not found_match:
                        logger.debug(f"楽曲詳細ファイル '{filename}' (ユニット: {unit_folder_name}) に対応する songs.py の楽曲が見つかりませんでした。")
    logger.info(f"楽曲-ユニットマッピング構築完了。{len(_song_title_to_unit_folder_map)} 件のマッピングを作成しました。")


def load_song_detail_file(unit_folder_name: str, song_title_from_songs_py: str) -> dict | None:
    """
    指定されたユニットフォルダ内の楽曲詳細Pythonファイルを動的に読み込む。
    songs.pyのタイトルからファイル名を推測する。
    """
    file_name_for_load = sanitize_filename(song_title_from_songs_py) + ".py"
    
    song_file_path = os.path.join(BASE_SONG_DETAILS_DIR, unit_folder_name, file_name_for_load)

    logger.debug(f"楽曲詳細ファイルを探しています: {song_file_path}")

    if not os.path.exists(song_file_path):
        logger.warning(f"楽曲詳細ファイルが見つかりません: {song_file_path}")
        return None

    try:
        module_name = f"song_detail_{unit_folder_name}_{file_name_for_load.replace('.py', '').replace(' ', '_').replace('-', '_').replace('.', '').replace('!', '').replace('?', '').replace('(', '').replace(')', '')}"
        
        spec = importlib.util.spec_from_file_location(module_name, song_file_path)
        if spec is None:
            logger.error(f"エラー: 楽曲詳細ファイルの仕様をロードできませんでした: {song_file_path}")
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        loaded_detail = getattr(module, 'song_detail_data', None)

        if loaded_detail is None or not isinstance(loaded_detail, dict):
            logger.warning(f"警告: 楽曲詳細ファイル '{song_file_path}' から期待される変数 'song_detail_data' が見つからないか、辞書ではありません。")
            return None
        
        logger.debug(f"楽曲詳細をロードしました: {song_title_from_songs_py} ({unit_folder_name})")
        return loaded_detail

    except Exception as e:
        logger.error(f"エラー: 楽曲詳細ファイル '{song_file_path}' のロード中に予期せぬエラーが発生しました: {e}", exc_info=True)
        return None


# ★新規追加★ 楽曲詳細表示用のView
class SongDetailView(discord.ui.View):
    # original_list_view: 楽曲リスト表示を管理する PjskListView のインスタンス
    # original_message: Botが送信した元のメッセージオブジェクト（リスト表示と詳細表示で共有）
    def __init__(self, original_list_view: 'PjskListView', original_message: discord.Message):
        super().__init__(timeout=86400)
        self.original_list_view = original_list_view
        self.original_message = original_message
        logger.debug(f"SongDetailView: 初期化完了。元のリストViewのinteractor_id: {original_list_view.original_interactor_id}")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.original_list_view.original_interactor_id:
            logger.debug(f"SongDetailView: interaction_check OK for user ID {interaction.user.id}")
            return True
        else:
            await interaction.response.send_message("このボタンはコマンドを実行したユーザーのみ操作できます。", ephemeral=True)
            logger.warning(f"SongDetailView: 不正なユーザーによるボタン操作: ユーザーID {interaction.user.id}, オリジナルインタラクターID {self.original_list_view.original_interactor_id}")
            return False

    @discord.ui.button(label="← リストに戻る", style=discord.ButtonStyle.red, custom_id="back_to_list", row=0)
    async def back_to_list_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が楽曲詳細からリストに戻りました。")
        
        self.stop() # このViewを停止
        
        # original_list_view の _update_page_and_view はEmbedとViewの状態を更新する
        # このViewは PjskListView のインスタンスを参照しており、その View の状態（ページ、ソート順など）は維持されている。
        await interaction.response.edit_message(
            embed=self.original_list_view.get_page_embed(), 
            view=self.original_list_view # ここで元の PjskListView インスタンスを渡す
        )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.original_message: 
            try:
                await self.original_message.edit(view=self)
            except discord.NotFound:
                logger.warning("SongDetailView: タイムアウト時に元のメッセージが見つかりませんでした。")
            logger.info("SongDetailView: タイムアウトしました。UIを無効化しました。")


class PjskListView(discord.ui.View):
    SORT_DEFAULT = "default"        
    SORT_JAPANESE_ALPHA = "japanese_alpha"
    SORT_LEVEL_BASE = "level_" 
    SORT_EASY_LEVEL = "level_easy"
    SORT_NORMAL_LEVEL = "level_normal" 
    SORT_HARD_LEVEL = "level_hard"     
    SORT_EXPERT_LEVEL = "level_expert"   
    SORT_MASTER_LEVEL = "level_master"   
    SORT_APPEND_LEVEL = "level_append"

    ORDER_ASC = "asc"
    ORDER_DESC = "desc"

    DIFFICULTY_MAPPING = {
        "easy": "EASY", "normal": "NORMAL", "hard": "HARD",
        "expert": "EXPERT", "master": "MASTER", "append": "APPEND"
    }

    def _get_sort_options_list(self):
        options = [
            discord.SelectOption(label="配信順", value=self.SORT_DEFAULT, description="ゲームへの配信順で並べ替えます。"),
            discord.SelectOption(label="50音順", value=self.SORT_JAPANESE_ALPHA, description="楽曲タイトルを50音順で並べ替えます。"),
        ]
        for key, display_name in self.DIFFICULTY_MAPPING.items():
            options.append(
                discord.SelectOption(label=f"{display_name} Lv順", value=f"{self.SORT_LEVEL_BASE}{key}", description=f"{display_name}難易度のレベル順で並べ替えます。")
            )
        return options
    
    def __init__(self, song_data, original_interactor_id, current_page=0, sort_method=SORT_DEFAULT, sort_order=ORDER_ASC):
        super().__init__(timeout=86400)
        self.original_song_data = list(song_data)
        self.original_interactor_id = original_interactor_id
        self.sort_method = sort_method 
        self.sort_order = sort_order 
        
        # NOTE: _sort_songs は、ソート方法や順序が変わるたびに呼び出される
        self._sorted_song_data = self._sort_songs(self.original_song_data, self.sort_method, self.sort_order)
        
        self.current_page = current_page
        self.songs_per_page = 10 
        
        self.total_displayable_songs = len(self._sorted_song_data)
        self.max_pages = (self.total_displayable_songs + self.songs_per_page - 1) // self.songs_per_page
        if self.max_pages == 0: 
            self.max_pages = 1 
        
        if self.current_page >= self.max_pages:
            self.current_page = self.max_pages - 1
        if self.current_page < 0:
            self.current_page = 0

        # PjskListViewのインスタンス変数としてSelectメニューを保持
        self.sort_select: discord.ui.Select | None = None
        self.song_detail_select: discord.ui.Select | None = None

        self.update_buttons_state() # ボタンの初期状態を設定

        # 初回のみ add_item を呼び出す
        # 以降は _update_page_and_view で options, placeholder, disabled などを更新
        self._add_sort_select_menu(initial_add=True)
        self._add_song_detail_select_menu(initial_add=True)

        logger.debug(f"PjskListView: 初期化完了。総曲数: {len(song_data)}, 表示対象曲数: {self.total_displayable_songs}, 最大ページ: {self.max_pages}, 初期ページ: {self.current_page}, インタラクターID: {self.original_interactor_id}, ソート方法: {self.sort_method}, ソート方向: {self.sort_order}")
    
    def update_buttons_state(self):
        """ページングボタンとソート順切り替えボタンの状態を更新するヘルパーメソッド"""
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.max_pages - 1)

        if self.sort_order == self.ORDER_ASC:
            self.toggle_order_button.label = "降順"
            self.toggle_order_button.style = discord.ButtonStyle.red 
        else:
            self.toggle_order_button.label = "昇順"
            self.toggle_order_button.style = discord.ButtonStyle.green 

    def _add_sort_select_menu(self, initial_add: bool = False):
        """ソート選択Selectメニューを追加（または更新）するヘルパーメソッド"""
        current_sort_label = {
            self.SORT_DEFAULT: "配信順", 
            self.SORT_JAPANESE_ALPHA: "50音順",
            **{f"{self.SORT_LEVEL_BASE}{key}": f"{value} Lv順" for key, value in self.DIFFICULTY_MAPPING.items()}
        }.get(self.sort_method, "ソート方法を選択...")

        if initial_add or not self.sort_select: # 初回追加時、またはselectオブジェクトがまだない場合
            self.sort_select = discord.ui.Select(
                placeholder=f"現在のソート: {current_sort_label}",
                options=self._get_sort_options_list(), 
                custom_id="sort_options_select",
                row=1 
            )
            self.sort_select.callback = self.sort_options_select_callback
            self.add_item(self.sort_select)
        else: # 既にSelectがある場合は、optionsとplaceholderを更新
            self.sort_select.placeholder = f"現在のソート: {current_sort_label}"
            self.sort_select.options = self._get_sort_options_list()


    def _add_song_detail_select_menu(self, initial_add: bool = False):
        """楽曲詳細選択Selectメニューを追加（または更新）するヘルパーメソッド"""
        current_page_songs = self._sorted_song_data[
            self.current_page * self.songs_per_page : (self.current_page + 1) * self.songs_per_page
        ]
        
        song_detail_options = []
        for song in current_page_songs:
            title = song.get('title', '不明なタイトル')
            if len(title) > 100: 
                 logger.warning(f"楽曲タイトルが長すぎます（100文字以上）: {title}。Selectメニューで問題が発生する可能性があります。")

            if title in _song_title_to_unit_folder_map:
                song_detail_options.append(
                    discord.SelectOption(label=title, value=title)
                )
            else:
                logger.debug(f"楽曲 '{title}' の詳細情報ファイルが見つからないため、詳細選択メニューに追加しません。")
        
        if initial_add or not self.song_detail_select: # 初回追加時、またはselectオブジェクトがまだない場合
            if song_detail_options:
                self.song_detail_select = discord.ui.Select(
                    placeholder="楽曲を選択して詳細を見る", 
                    options=song_detail_options,
                    custom_id="song_detail_select",
                    row=2,
                    disabled=False 
                )
            else:
                self.song_detail_select = discord.ui.Select(
                    placeholder="詳細情報のある楽曲がありません。",
                    options=[discord.SelectOption(label="選択肢なし", value="no_option", default=True, description="詳細情報のある楽曲がありません。")],
                    custom_id="song_detail_select",
                    row=2,
                    disabled=True
                )
            self.song_detail_select.callback = self.song_detail_select_callback
            self.add_item(self.song_detail_select)
        else: # 既にSelectがある場合は、options, placeholder, disabled を更新
            if song_detail_options:
                self.song_detail_select.placeholder = "楽曲を選択して詳細を見る"
                self.song_detail_select.options = song_detail_options
                self.song_detail_select.disabled = False
            else:
                self.song_detail_select.placeholder = "詳細情報のある楽曲がありません。"
                self.song_detail_select.options = [discord.SelectOption(label="選択肢なし", value="no_option", default=True, description="詳細情報のある楽曲がありません。")]
                self.song_detail_select.disabled = True
            
        if not song_detail_options and not initial_add: # 通常の更新でオプションがない場合
             logger.debug("現在のページには詳細情報のある楽曲がないため、詳細選択メニューは無効化されました。")


    def _sort_songs(self, songs_list, method, order): 
        logger.debug(f"_sort_songs: ソート方法 '{method}', 方向 '{order}' でソートを開始します。")

        filtered_songs = list(songs_list) 
        
        if method == self.SORT_APPEND_LEVEL:
            original_count = len(filtered_songs)
            temp_filtered = []
            for song in filtered_songs:
                append_level = song.get("append")
                if isinstance(append_level, (int, float)):
                    temp_filtered.append(song)
                else:
                    logger.debug(f"  _sort_songs: APPEND Lv順ソートのため、曲 '{song.get('title', '不明なタイトル')}' はAPPENDレベルがないため除外されました。")
            filtered_songs = temp_filtered
            logger.debug(f"  _sort_songs: APPEND Lv順ソートで {original_count} 曲中 {len(filtered_songs)} 曲がフィルタリングされました。")


        if method == self.SORT_DEFAULT:
            logger.debug("_sort_songs: 配信順でソートします。")
            # 配信順は元のリストの順序
            # reverseはリストを反転させるだけなので、元のデータのコピーを直接操作
            return list(filtered_songs) if order == self.ORDER_ASC else list(reversed(filtered_songs))

        elif method == self.SORT_JAPANESE_ALPHA:
            logger.debug("_sort_songs: 50音順でソートします。")
            # 50音順ソートのロジック:
            # 漢字、ひらがな、カタカナが混在する場合の正しい50音順ソートは複雑。
            # 一般的には日本語テキストの比較ライブラリ(MeCab, janomeなど)を使うか、
            # フリガナデータがあればそれを使う。
            # 今回は簡易的に文字列比較に任せる。
            # ただし、現状では songs.py にフリガナ情報がないため、タイトル文字列の直接比較になる。
            return sorted(filtered_songs, key=lambda s: s.get('title', ''), reverse=(order == self.ORDER_DESC))

        elif method.startswith(self.SORT_LEVEL_BASE):
            difficulty_key = method.replace(self.SORT_LEVEL_BASE, "")
            logger.debug(f"_sort_songs: {difficulty_key.upper()} のレベル順でソートします。")
            
            def get_level(song):
                level = song.get(difficulty_key) 
                
                if level is None:
                    # レベル情報がない場合は、ソート順の最後に来るように大きな値を返す
                    return float('inf') 
                
                if isinstance(level, (int, float)): 
                    return level
                else:
                    logger.warning(f"  _sort_songs.get_level: 曲 '{song.get('title', '不明なタイトル')}' の難易度 '{difficulty_key}' のレベルが数値ではありません。値: {level}。ソートから除外または末尾に配置します。")
                    return float('inf') # 数値でない場合もソートの最後に来るように大きな値を返す

            # レベルでソートし、レベルが同じ場合はタイトルでソート
            sorted_data = sorted(filtered_songs, key=lambda s: (get_level(s), s.get('title', '')), reverse=(order == self.ORDER_DESC))
            return sorted_data
        
        else:
            logger.warning(f"_sort_songs: 未知のソート方法が指定されました: {method}。デフォルトでソートします。")
            return list(filtered_songs) 

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
                level = song.get(difficulty_key) 
                if isinstance(level, (int, float)): 
                    level_info = f" (Lv.{level})"
            
            song_entry = f"{display_num}. **{title}**{level_info}\n"
                    
            song_entries.append(song_entry)

        full_description = "".join(song_entries)
        if not full_description:
            full_description = "表示できる曲がありませんでした。"

        sort_label = {
            self.SORT_DEFAULT: "配信順", 
            self.SORT_JAPANESE_ALPHA: "50音順",
            **{f"{self.SORT_LEVEL_BASE}{key}": f"{value} Lv順" for key, value in self.DIFFICULTY_MAPPING.items()}
        }.get(self.sort_method, "不明なソート順")
        
        order_label = "昇順" if self.sort_order == self.ORDER_ASC else "降順"
        embed_title_suffix = f" ({sort_label}・{order_label})" if sort_label != "不明なソート順" else f" ({order_label})"


        embed = discord.Embed(
            title=f"プロセカ楽曲リスト{embed_title_suffix}", 
            description=full_description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"全{self.total_displayable_songs}件中、{start_index + 1}-{min(end_index, len(self._sorted_song_data))}件を表示 | ページ {self.current_page + 1}/{self.max_pages}")
        logger.debug(f"PjskListView: Embed生成完了。ページ: {self.current_page + 1}/{self.max_pages}, ソート方法: {self.sort_method}, ソート方向: {self.sort_order}")
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
        # ソートデータとページングを再計算
        self._sorted_song_data = self._sort_songs(self.original_song_data, self.sort_method, self.sort_order)
        self.max_pages = (self.total_displayable_songs + self.songs_per_page - 1) // self.songs_per_page
        if self.max_pages == 0: self.max_pages = 1 
        if self.current_page >= self.max_pages: self.current_page = self.max_pages - 1
        if self.current_page < 0: self.current_page = 0


        self.update_buttons_state() # ボタンの状態を更新
        self._add_sort_select_menu() # ソートSelectを更新（オプションとプレースホルダー）
        self._add_song_detail_select_menu() # 楽曲詳細Selectを更新（オプションとプレースホルダー、disabled状態）

        await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

        
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
            
    @discord.ui.button(label="昇順/降順切替", style=discord.ButtonStyle.secondary, custom_id="toggle_order_button", row=0)
    async def toggle_order_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.sort_order == self.ORDER_ASC:
            self.sort_order = self.ORDER_DESC
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のソート方向を降順に切り替えました。")
        else:
            self.sort_order = self.ORDER_ASC
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のソート方向を昇順に切り替えました。")
        
        self.current_page = 0 
        await self._update_page_and_view(interaction)

    async def sort_options_select_callback(self, interaction: discord.Interaction):
        selected_value = interaction.data['values'][0]
        logger.debug(f"PjskListView: ソートオプションが選択されました: {selected_value}")

        self.sort_method = selected_value 
        self.current_page = 0 
        await self._update_page_and_view(interaction)
        logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song のソート方法を {self.sort_method} に切り替えました。")

    async def song_detail_select_callback(self, interaction: discord.Interaction):
        selected_title = interaction.data['values'][0]

        # Selectメニューにダミーオプションしかなかった場合は処理を終了
        if selected_title == "no_option":
            await interaction.response.send_message("この選択肢は無効です。詳細情報のある楽曲を選択してください。", ephemeral=True)
            return

        logger.debug(f"PjskListView: 楽曲詳細オプションが選択されました: {selected_title}")

        unit_folder_name = _song_title_to_unit_folder_map.get(selected_title)

        if not unit_folder_name:
            await interaction.response.send_message(
                f"楽曲 '{selected_title}' のユニット情報が見つからないため、詳細をロードできません。", 
                ephemeral=True
            )
            logger.warning(f"楽曲詳細: 楽曲 '{selected_title}' に対応するユニットフォルダが見つかりません。")
            return
        
        detail_data = load_song_detail_file(unit_folder_name, selected_title)

        if detail_data is not None:
            embed = discord.Embed(
                title=f"🎵 {selected_title} 詳細情報 🎵",
                color=discord.Color.blue()
            )
            
            fields_added = False
            if 'artist' in detail_data and detail_data['artist']:
                embed.add_field(name="アーティスト", value=detail_data['artist'], inline=False)
                fields_added = True
            if 'description' in detail_data and detail_data['description']:
                embed.add_field(name="概要", value=detail_data['description'], inline=False)
                fields_added = True
            if 'lyrics_url' in detail_data and detail_data['lyrics_url']:
                embed.add_field(name="歌詞", value=f"[こちら]({detail_data['lyrics_url']})", inline=True)
                fields_added = True
            if 'music_video_url' in detail_data and detail_data['music_video_url']:
                embed.add_field(name="MV", value=f"[こちら]({detail_data['music_video_url']})", inline=True)
                fields_added = True
            
            if not fields_added:
                embed.description = "この楽曲の詳細情報はまだ登録されていません。"
                embed.set_footer(text=f"ユニット: {unit_folder_name}")
            else:
                embed.set_footer(text=f"ユニット: {unit_folder_name}")

            song_detail_view = SongDetailView(self, self.message) 

            await interaction.response.edit_message(embed=embed, view=song_detail_view)
            
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が楽曲 '{selected_title}' の詳細を閲覧しました。")
        else:
            await interaction.response.send_message(
                f"楽曲 '{selected_title}' の詳細情報ファイルが見つからないか、読み込みに失敗しました。", 
                ephemeral=True
            )
            logger.warning(f"楽曲詳細: 楽曲 '{selected_title}' の詳細情報がロードできませんでした。")


    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message: 
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                logger.warning("PjskListView: タイムアウト時に元のメッセージが見つかりませんでした。")
            logger.info("PjskListView: タイムアウトしました。UIを無効化しました。")


class PjskListSongCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("PjskListSongCommandsコグが初期化されています。")

    ALL_DIFFICULTY_TYPES = ["easy", "normal", "hard", "expert", "master", "append"]
    DISPLAY_DIFFICULTY_TYPES = {
        "easy": "EASY", "normal": "NORMAL", "hard": "HARD",
        "expert": "EXPERT", "master": "MASTER", "append": "APPEND"
    }

    @discord.app_commands.command(name="pjsk_list_song", description="プロセカの全曲リストをページ表示し、ソートできます。") # ★変更点★ guild_ids を削除
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

            view = PjskListView(all_songs, interaction.user.id, sort_method=PjskListView.SORT_DEFAULT, sort_order=PjskListView.ORDER_ASC) 
            initial_embed = view.get_page_embed()
            
            message = await interaction.followup.send(embed=initial_embed, view=view)
            view.message = message # ★ここが重要★ PjskListViewインスタンスに送信されたメッセージオブジェクトを保持させる

            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song コマンドを使用しました。最初のページが送信されました。")

        except Exception as e:
            await interaction.followup.send(f"曲リストの取得中にエラーが発生しました: {e}", ephemeral=True)
            logger.error(f"エラー: /pjsk_list_song コマンドの実行中に予期せぬエラーが発生しました: {e}", exc_info=True)

    async def cog_load(self):
        logger.info("PjskListSongCommandsコグがロードされました。楽曲-ユニットマッピングを構築します。")
        build_song_unit_mapping() # Bot起動時にマッピングを構築
        logger.info("PjskListSongCommandsコグのロードが完了しました。")


    async def cog_unload(self):
        logger.info("PjskListSongCommandsコグがアンロードされました。")

async def setup(bot):
    await bot.add_cog(PjskListSongCommands(bot))