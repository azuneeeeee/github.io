import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import json
import os
import re
import traceback
import sys
import urllib.parse 

# songs.py のパスを動的に計算して sys.path に追加
current_cog_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.abspath(os.path.join(current_cog_dir, '..'))
data_dir = os.path.join(project_root_dir, 'data')

if data_dir not in sys.path:
    sys.path.insert(0, data_dir)

try:
    from songs import proseka_songs
    SONG_DATA_MAP = {}
    for song_data in proseka_songs:
        if "title" in song_data:
            SONG_DATA_MAP[song_data["title"].lower()] = song_data
    print("DEBUG: songs.py loaded successfully and SONG_DATA_MAP created.")
except ImportError:
    print("ERROR: songs.py not found. Song data (images, levels) will not be available.")
    print(f"DEBUG: sys.path contents: {sys.path}")
    SONG_DATA_MAP = {}
except Exception as e:
    print(f"ERROR: Failed to load songs.py or create SONG_DATA_MAP: {e}")
    traceback.print_exc()
    SONG_DATA_MAP = {}
finally:
    pass


SUPPORT_GUILD_ID = 1376551581423767582

DATA_FILE = "data/pjsk_accuracy_records.json"
DATA_DIR = os.path.dirname(DATA_FILE)

VALID_DIFFICULTIES = ["easy", "normal", "hard", "expert", "master", "append"]
VALID_CLEAR_STATUSES = ["ap", "fc", "clear", "未clear"]
ACCURACY_PATTERN = re.compile(r"^\d+-\d+-\d+-\d+$")
FLICK_PATTERN = re.compile(r"^\d+/\d+/\d+$")

def load_all_records():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: JSONDecodeError in {DATA_FILE}. Initializing with empty data.")
        return {}
    except Exception as e:
        print(f"Error loading {DATA_FILE}: {e}")
        return {}

def save_all_records(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class AccuracyRecordModal(Modal, title="新規記録"):
    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__()
        self.bot = bot
        self.user_id = str(user_id)

        self.song_name = TextInput(
            label="曲名",
            placeholder="例: グリッター",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.song_name)

        self.difficulty = TextInput(
            label="難易度",
            placeholder="例: master (easy/normal/hard/expert/master/append)",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.difficulty)

    async def on_submit(self, interaction: discord.Interaction):
        song_name_input = self.song_name.value.strip()
        difficulty_input = self.difficulty.value.strip().lower()

        if difficulty_input not in VALID_DIFFICULTIES:
            await interaction.response.send_message(
                f"無効な難易度です。『{'/'.join(VALID_DIFFICULTIES)}』から選んでください。",
                ephemeral=True
            )
            return

        all_records = load_all_records()
        if self.user_id not in all_records:
            all_records[self.user_id] = {"records": {}, "last_record": None}

        user_data = all_records[self.user_id]

        if song_name_input in user_data["records"] and difficulty_input in user_data["records"][song_name_input]:
            await interaction.response.send_message(
                f"曲名『{song_name_input}』、難易度『{difficulty_input.upper()}』は既に記録されています。「リザルトを更新」ボタンから更新してください。",
                ephemeral=True
            )
            return

        if song_name_input not in user_data["records"]:
            user_data["records"][song_name_input] = {}

        user_data["records"][song_name_input][difficulty_input] = {
            "status": None,
            "accuracy": None,
            "max_combo": None,
            "flick_data": None,
            "timestamp": discord.utils.utcnow().isoformat()
        }

        user_data["last_record"] = {
            "song": song_name_input,
            "difficulty": difficulty_input,
            "timestamp": discord.utils.utcnow().isoformat()
        }

        save_all_records(all_records)

        current_record = user_data["records"][song_name_input][difficulty_input]
        embed = UpdateRecordModal.create_display_embed(interaction.user, song_name_input, difficulty_input, current_record)
        embed.title = "新しい記録を作成しました！" 
        embed.description = "この記録を更新するには「リザルトを更新」ボタンを使用してください。"

        view = RecordAccuracyView(self.bot, int(self.user_id), song_name_input, difficulty_input)
        view.set_button_states(has_record=True)

        await interaction.response.send_message(embed=embed, view=view)

        try:
            message = await interaction.original_response()
            view.message = message
        except Exception as e:
            print(f"Failed to get original response message after AccuracyRecordModal submit: {e}")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message(
            f"モーダル送信中にエラーが発生しました: `{error}`",
            ephemeral=True
        )
        traceback.print_exc()

class UpdateRecordModal(Modal, title="記録を更新"):
    def __init__(self, bot: commands.Bot, user_id: int, song_name: str, difficulty: str):
        super().__init__()
        self.bot = bot
        self.user_id = str(user_id)
        self.song_name = song_name
        self.difficulty = difficulty

        self.accuracy = TextInput(
            label="精度 (GREAT-GOOD-BAD-MISS)",
            placeholder="例: 1-0-0-0",
            required=False,
            style=discord.TextStyle.short
        )
        self.add_item(self.accuracy)

        self.max_combo = TextInput(
            label="最大コンボ数",
            placeholder="例: 1000",
            required=False,
            style=discord.TextStyle.short
        )
        self.add_item(self.max_combo)

        self.flick_data = TextInput(
            label="LATE/FAST/FLICK (任意)",
            placeholder="例: 5/10/2 (LATE/FAST/FLICK)",
            required=False,
            style=discord.TextStyle.short
        )
        self.add_item(self.flick_data)

        self.clear_status_update = TextInput(
            label="クリア状況 (任意: AP/FC/CLEAR/未CLEAR)",
            placeholder="入力しない場合は変更なし",
            required=False,
            style=discord.TextStyle.short
        )
        self.add_item(self.clear_status_update)

    async def on_submit(self, interaction: discord.Interaction):
        all_records = load_all_records()
        if self.user_id not in all_records:
            await interaction.response.send_message(
                "エラー: あなたの記録データが見つかりません。`/pjsk_record_result`で新規記録してください。",
                ephemeral=True
            )
            return

        user_data = all_records[self.user_id]
        if self.song_name not in user_data["records"] or self.difficulty not in user_data["records"][self.song_name]:
            await interaction.response.send_message(
                f"エラー: 曲名『{self.song_name}』難易度『{self.difficulty.upper()}』の記録が見つかりません。`/pjsk_record_result`で新規記録してください。",
                ephemeral=True
            )
            return

        current_record = user_data["records"][self.song_name][self.difficulty]

        accuracy_input = self.accuracy.value.strip()
        if accuracy_input:
            if not ACCURACY_PATTERN.match(accuracy_input):
                await interaction.response.send_message(
                    "無効な精度入力形式です。例: `1-0-0-0` のように入力してください。",
                    ephemeral=True
                )
                return
            current_record["accuracy"] = accuracy_input

        max_combo_input = self.max_combo.value.strip()
        if max_combo_input:
            if not max_combo_input.isdigit():
                await interaction.response.send_message(
                    "最大コンボ数は数値で入力してください。",
                    ephemeral=True
                )
                return
            current_record["max_combo"] = int(max_combo_input)

        flick_data_input = self.flick_data.value.strip()
        if flick_data_input:
            if not FLICK_PATTERN.match(flick_data_input):
                await interaction.response.send_message(
                    "無効なLATE/FAST/FLICK入力形式です。例: `5/10/2` のように入力してください。",
                    ephemeral=True
                )
                return
            current_record["flick_data"] = flick_data_input

        clear_status_update_input = self.clear_status_update.value.strip().lower()
        if clear_status_update_input:
            if clear_status_update_input not in VALID_CLEAR_STATUSES:
                await interaction.response.send_message(
                    f"無効なクリア状況です。『{'/'.join(VALID_CLEAR_STATUSES)}』から選んでください。",
                    ephemeral=True
                )
                return
            current_record["status"] = clear_status_update_input

        current_record["timestamp"] = discord.utils.utcnow().isoformat()

        user_data["last_record"] = {
            "song": self.song_name,
            "difficulty": self.difficulty,
            "timestamp": discord.utils.utcnow().isoformat()
        }

        save_all_records(all_records)

        updated_embed = self.create_display_embed(interaction.user, self.song_name, self.difficulty, current_record)
        updated_embed.description = "記録が更新されました！" 

        view = RecordAccuracyView(self.bot, int(self.user_id), self.song_name, self.difficulty)
        view.set_button_states(has_record=True)

        await interaction.response.send_message(embed=updated_embed, view=view)

        try:
            message = await interaction.original_response()
            view.message = message
        except Exception as e:
            print(f"Failed to get original response message after UpdateRecordModal submit: {e}")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message(
            f"モーダル送信中にエラーが発生しました: `{error}`",
            ephemeral=True
        )
        traceback.print_exc()

    @staticmethod
    def create_display_embed(user: discord.Member, song: str, diff: str, record: dict):
        song_info = SONG_DATA_MAP.get(song.lower())

        print(f"DEBUG: song_name (input lower): {song.lower()}")
        print(f"DEBUG: retrieved song_info: {song_info}")
        print(f"DEBUG: difficulty (input lower): {diff.lower()}")

        difficulty_colors = {
            "easy": discord.Color.green(),           # 🟢
            "normal": discord.Color.blue(),          # 🔵
            "hard": discord.Color.yellow(),          # 🟡
            "expert": discord.Color.red(),           # 🔴
            "master": discord.Color.purple(),        # 🟣
            "append": discord.Color.from_rgb(255, 192, 203) # ピンク (HEX: #FFC0CB)
        }

        embed_color = discord.Color.dark_grey() # デフォルトの色

        if diff.lower() in difficulty_colors:
            embed_color = difficulty_colors[diff.lower()]
            print(f"DEBUG: Embed color set to: {embed_color}")
        else:
            print(f"DEBUG: No specific color for difficulty '{diff.lower()}'. Using default.")


        if song_info is None:
            print(f"WARNING: song_info is None for song: '{song}'. Check songs.py data and matching.")
            difficulty_display = diff.upper()
            level_str = " (レベル情報なし)" 
            image_url = None
        else:
            difficulty_display = diff.upper()
            level_str = ""
            if diff.lower() in song_info:
                level = song_info.get(diff.lower())
                print(f"DEBUG: level retrieved: {level}")
                if level is not None:
                    level_str = f" Lv.{level}"
            image_url = song_info.get("image_url")


        final_embed_title = f"『{song}』({difficulty_display}{level_str}) の記録"
        print(f"DEBUG: Final Embed Title (Raw): {final_embed_title}")
        print(f"DEBUG: Final Embed Title Length (Raw): {len(final_embed_title)}")

        embed = discord.Embed(
            title=final_embed_title, 
            color=embed_color 
        )

        if image_url:
            embed.set_thumbnail(url=image_url)

        status_val = record.get("status")
        embed.add_field(name="クリア状況", value=status_val.upper() if status_val else "未記録", inline=True)
        embed.add_field(name="精度 (G-G-B-M)", value=record.get("accuracy", "未記録"), inline=True)
        embed.add_field(name="最大コンボ", value=record.get("max_combo", "未記録"), inline=True)

        flick_data_val = record.get("flick_data")

        if flick_data_val is not None and FLICK_PATTERN.match(flick_data_val):
            colored_flick_data = flick_data_val
        else:
            colored_flick_data = "未記録"

        embed.add_field(name="LATE/FAST/FLICK", value=colored_flick_data, inline=False)

        timestamp_str = record.get("timestamp")
        if timestamp_str:
            try:
                dt_object = discord.utils.parse_time(timestamp_str)
                embed.add_field(name="最終更新", value=f"<t:{int(dt_object.timestamp())}:F>", inline=False)
            except Exception:
                embed.add_field(name="最終更新", value="形式エラー", inline=False)
        else:
            embed.add_field(name="最終更新", value="未記録", inline=False)

        embed.set_footer(text=f"記録者: {user.display_name}")
        return embed

class ConfirmResetView(View):
    def __init__(self, bot: commands.Bot, user_id: int):
        super().__init__(timeout=86400) # 24時間
        self.bot = bot
        self.user_id = user_id
        self.confirmed_step_1 = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンは、コマンドを実行した本人しか使えません。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="はい (リセット)", style=discord.ButtonStyle.danger, custom_id="confirm_reset_yes")
    async def confirm_yes(self, interaction: discord.Interaction, button: Button):
        if not self.confirmed_step_1:
            self.confirmed_step_1 = True
            embed = discord.Embed(
                title="❗ 最終確認：本当にリセットしますか？",
                description="**全ての精度記録が完全に削除されます。この操作は取り消せません。**\n本当によろしいですか？",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            all_records = load_all_records()
            user_id_str = str(self.user_id)
            if user_id_str in all_records:
                del all_records[user_id_str]
                save_all_records(all_records)

                embed = discord.Embed(
                    title="✅ 精度情報のリセットが完了しました",
                    description="あなたの全ての精度記録が削除されました。",
                    color=discord.Color.red()
                )
                if self.message:
                    original_command_view = RecordAccuracyView(self.bot, self.user_id)
                    original_command_view.set_button_states(has_record=False)

                    try:
                        await self.message.edit(embed=embed, view=original_command_view)
                        original_command_view.message = self.message
                    except Exception as e:
                        print(f"Error editing original message after successful reset: {e}")
                else:
                    await interaction.response.send_message(embed=embed, view=None)

            else:
                embed = discord.Embed(
                    title="❌ 記録された精度情報はありません。",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=None)

            self.stop()

    @discord.ui.button(label="いいえ (キャンセル)", style=discord.ButtonStyle.secondary, custom_id="confirm_reset_no")
    async def confirm_no(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="リセットをキャンセルしました",
            description="あなたの精度記録は削除されませんでした。",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(content="リセット確認がタイムアウトしました。", embed=None, view=None)
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"Error removing ConfirmResetView on timeout: {e}")

class RecordAccuracyView(View):
    def __init__(self, bot: commands.Bot, user_id: int, song_name: str = None, difficulty: str = None):
        super().__init__(timeout=86400) # 24時間
        self.bot = bot
        self.user_id = user_id
        self.current_song = song_name
        self.current_difficulty = difficulty
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンは、コマンドを実行した本人しか使えません。", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"Error removing view on timeout: {e}")

    @discord.ui.button(label="精度を記録", style=discord.ButtonStyle.primary, custom_id="record_accuracy_button")
    async def record_accuracy_button_callback(self, interaction: discord.Interaction, button: Button):
        modal = AccuracyRecordModal(self.bot, self.user_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="リザルトを更新", style=discord.ButtonStyle.success, custom_id="update_record_button")
    async def update_record_button_callback(self, interaction: discord.Interaction, button: Button):
        if not self.current_song or not self.current_difficulty:
            await interaction.response.send_message("更新する曲と難易度が特定できません。`/pjsk_record_result`を再実行し、まず新規記録を作成してください。", ephemeral=True)
            return

        modal = UpdateRecordModal(self.bot, self.user_id, self.current_song, self.current_difficulty)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="リセット", style=discord.ButtonStyle.danger, custom_id="reset_accuracy_button")
    async def reset_accuracy_button_callback(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="⚠ 記録リセットの確認",
            description="本当に全ての精度記録をリセットしますか？この操作は取り消せません。",
            color=discord.Color.orange()
        )
        confirm_view = ConfirmResetView(self.bot, self.user_id)

        confirm_view.message = self.message

        await interaction.response.send_message(embed=embed, view=confirm_view)

        try:
            confirm_message = await interaction.original_response()
            confirm_view.message = confirm_message
        except Exception as e:
            print(f"Failed to get original response message after reset confirmation: {e}")


    def set_button_states(self, has_record: bool):
        for item in self.children:
            if isinstance(item, Button):
                if item.custom_id == "update_record_button":
                    item.disabled = not (self.current_song and self.current_difficulty and has_record)
                elif item.custom_id == "record_accuracy_button":
                    item.disabled = has_record
                elif item.custom_id == "reset_accuracy_button":
                    item.disabled = not has_record


class PjskRecordResult(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("DEBUG (pjsk_record_result): PjskRecordResult Cog initialized.")

    @app_commands.command(name="pjsk_record_result", description="プロセカの精度記録を管理します。")
    @app_commands.guilds(discord.Object(id=SUPPORT_GUILD_ID))
    async def pjsk_record_result(
        self,
        interaction: discord.Interaction
    ):
        user_id_str = str(interaction.user.id)
        all_records = load_all_records()

        user_data = all_records.get(user_id_str)

        last_song = None
        last_difficulty = None
        has_user_records = False

        if user_data:
            has_user_records = bool(user_data["records"])
            last_record_data = user_data.get("last_record")
            if last_record_data:
                last_song = last_record_data.get("song")
                last_difficulty = last_record_data.get("difficulty")

        view = RecordAccuracyView(self.bot, interaction.user.id, last_song, last_difficulty)

        embed = None
        if has_user_records and last_song and last_difficulty and \
           last_song in user_data["records"] and last_difficulty in user_data["records"][last_song]:
            current_record = user_data["records"][last_song][last_difficulty]
            embed = UpdateRecordModal.create_display_embed(interaction.user, last_song, last_difficulty, current_record)

            embed.description = "以下のボタンから操作を選択してください。"
        else:
            embed = discord.Embed(
                title="プロセカ精度記録",
                description="まだ記録がありません。以下のボタンから新規記録を開始してください。",
                color=discord.Color.green()
            )

        view.set_button_states(has_record=has_user_records)
        await interaction.response.send_message(embed=embed, view=view)

        try:
            message = await interaction.original_response()
            view.message = message
        except Exception as e:
            print(f"Failed to get original response message at command start: {e}")

    @pjsk_record_result.error
    async def pjsk_record_result_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "このコマンドは、特定のサポートサーバーでのみ利用可能です。",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"コマンドの実行中に予期せぬエラーが発生しました: `{error}`",
                ephemeral=True
            )
            print(f"Error in pjsk_record_result: {error}")
            traceback.print_exc()

async def setup(bot: commands.Bot):
    os.makedirs(DATA_DIR, exist_ok=True)
    await bot.add_cog(PjskRecordResult(bot))
    print("DEBUG (pjsk_record_result): PjskRecordResult cog loaded.")

    for command in bot.tree.walk_commands():
        if command.name == "pjsk_record_result":
            print(f"DEBUG (pjsk_record_result): '/pjsk_record_result' command found in bot.tree after cog load setup.")
            print(f"DEBUG (pjsk_record_result): - Command name: {command.name}")
            break