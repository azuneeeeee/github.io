import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import List, Tuple, Dict, Any
import traceback
import logging

# pjsk_record_result.py から SUPPORT_GUILD_ID をインポート
# これにより、ギルドIDをグローバルに利用可能にする
try:
    from cogs.pjsk_record_result import SUPPORT_GUILD_ID
except ImportError:
    logging.error("Failed to import SUPPORT_GUILD_ID from cogs.pjsk_record_result. Please ensure pjsk_record_result.py is correctly set up and defines SUPPORT_GUILD_ID.")
    # インポートに失敗した場合のフォールバック (ただし、これは問題を示す)
    SUPPORT_GUILD_ID = 0 # デフォルト値。実際にはmain.pyでbot.GUILD_IDが設定されるはずだが、念のため。


class RankmatchResultModal(ui.Modal, title="ランクマッチ結果入力"):
    """
    最大5人までのプレイヤーのランクマッチ結果を入力するためのモーダル。
    P-G-GO-B-M, コンボ数 の形式で入力。
    """
    def __init__(self):
        super().__init__(timeout=300) # 5分でタイムアウト

        # プレイヤーごとの入力欄 (5つ)
        # P-G-GO-B-M, コンボ数 の形式
        self.player1_input = ui.TextInput(
            label="プレイヤー1 (P-G-GO-B-M, コンボ数)",
            placeholder="例: 1000-50-5-0-0, 1200 (必須)",
            required=True,
            style=discord.TextStyle.short,
            custom_id="player1_input"
        )
        self.add_item(self.player1_input)

        self.player2_input = ui.TextInput(
            label="プレイヤー2 (P-G-GO-B-M, コンボ数)",
            placeholder="例: 950-60-10-0-0, 1150 (必須)",
            required=True,
            style=discord.TextStyle.short,
            custom_id="player2_input"
        )
        self.add_item(self.player2_input)

        self.player3_input = ui.TextInput(
            label="プレイヤー3 (P-G-GO-B-M, コンボ数)",
            placeholder="例: 任意 (未入力可)",
            required=False,
            style=discord.TextStyle.short,
            custom_id="player3_input"
        )
        self.add_item(self.player3_input)

        self.player4_input = ui.TextInput(
            label="プレイヤー4 (P-G-GO-B-M, コンボ数)",
            placeholder="例: 任意 (未入力可)",
            required=False,
            style=discord.TextStyle.short,
            custom_id="player4_input"
        )
        self.add_item(self.player4_input)

        self.player5_input = ui.TextInput(
            label="プレイヤー5 (P-G-GO-B-M, コンボ数)",
            placeholder="例: 任意 (未入力可)",
            required=False,
            style=discord.TextStyle.short,
            custom_id="player5_input"
        )
        self.add_item(self.player5_input)


    def _parse_player_data(self, player_label: str, input_str: str, player_num: int) -> Tuple[bool, Dict[str, Any], str]:
        """
        プレイヤーの入力文字列をパースし、スコアなどを計算する。
        player_label: "プレイヤー1"のような、ラベル文字列全体
        player_num: プレイヤーの番号 (1, 2, 3...)
        戻り値: (成功フラグ, データ辞書, エラーメッセージ)
        """
        if not input_str.strip():
            return True, {}, "" # 未入力の場合は成功として、空のデータを返す

        try:
            # 入力例: 1000-50-5-0-0, 1200
            parts = [s.strip() for s in input_str.split(',')]
            if len(parts) != 2:
                return False, {}, f"{player_label}の入力形式が正しくありません。(P-G-GO-B-M, コンボ数)"

            accuracy_str = parts[0]
            combo_str = parts[1]

            # 精度データのパース
            accuracy_parts = [int(p) for p in accuracy_str.split('-')]
            if len(accuracy_parts) != 5:
                return False, {}, f"{player_label}の精度入力形式が正しくありません。(P-G-GO-B-M)"

            p, g, go, b, m = accuracy_parts
            if any(val < 0 for val in [p, g, go, b, m]):
                return False, {}, f"{player_label}の精度は0以上の数字を入力してください。"

            # スコア計算: P=+3, G=+2, GO=+1
            score = (p * 3) + (g * 2) + (go * 1)
            perfect_count = p

            # コンボ数のパース
            max_combo = int(combo_str)
            if max_combo < 0:
                return False, {}, f"{player_label}の最大コンボ数は0以上の数字を入力してください。"

            player_data = {
                "name": player_label, # ここで"プレイヤー1"のような文字列を直接使用
                "accuracy": {"Perfect": p, "Great": g, "Good": go, "Bad": b, "Miss": m},
                "score": score, 
                "perfect_count": perfect_count,
                "max_combo": max_combo
            }
            return True, player_data, ""

        except ValueError as e:
            return False, {}, f"{player_label}の入力値が無効です。数字とハイフン、カンマを正しく使用してください。({e})"
        except Exception as e:
            logging.error(f"Error parsing player data for {player_label}: {e}", exc_info=True) # ロギングを追加
            return False, {}, f"{player_label}の解析中に予期せぬエラーが発生しました。({e})"

    async def on_submit(self, interaction: discord.Interaction):
        """モーダルが送信されたときの処理"""
        logging.info(f"RankmatchResultModal submitted by {interaction.user.name} (ID: {interaction.user.id}).") # ロギングを追加
        try:
            await interaction.response.defer(ephemeral=False) # 計算に時間がかかる可能性を考慮し、応答を遅延
            logging.info(f"Successfully deferred interaction for RankmatchResultModal.") # ロギングを追加
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for RankmatchResultModal: Unknown interaction (404 NotFound). This will be caught by global error handler.", exc_info=True)
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for RankmatchResultModal: {e}", exc_info=True)
            return

        players_results = []
        inputs = {
            "プレイヤー1": self.player1_input.value,
            "プレイヤー2": self.player2_input.value,
            "プレイヤー3": self.player3_input.value,
            "プレイヤー4": self.player4_input.value,
            "プレイヤー5": self.player5_input.value
        }

        for i, (player_label, input_str) in enumerate(inputs.items(), 1):
            success, data, error_msg = self._parse_player_data(player_label, input_str, i)
            if not success:
                logging.warning(f"Invalid input for {player_label} from {interaction.user.name}: {error_msg}") # ロギングを追加
                await interaction.followup.send(error_msg, ephemeral=True)
                return
            if data: # データがある（未入力ではない）場合のみ追加
                players_results.append(data)

        if not players_results:
            logging.warning(f"No player data entered by {interaction.user.name}.") # ロギングを追加
            await interaction.followup.send("プレイヤーのデータが一つも入力されていません。", ephemeral=True)
            return

        # 同順位判定のためのソート
        # スコアの高い順 -> Perfect数の高い順 -> 最大コンボ数の高い順
        players_results.sort(key=lambda x: (x["score"], x["perfect_count"], x["max_combo"]), reverse=True)
        logging.info(f"Rankmatch results sorted for {len(players_results)} players.") # ロギングを追加

        embed = discord.Embed(
            title=f"⚔️ ランクマッチ結果", 
            description="---",
            color=discord.Color.gold()
        )

        # 順位表示と2人対戦時の勝敗判定
        rank_str = ""

        # プレイヤーが2人の場合の特別処理
        if len(players_results) == 2:
            player1 = players_results[0]
            player2 = players_results[1]

            # 精度詳細文字列を生成
            accuracy_str1 = (
                f"{player1['accuracy']['Perfect']:,}-"
                f"{player1['accuracy']['Great']:,}-"
                f"{player1['accuracy']['Good']:,}-"
                f"{player1['accuracy']['Bad']:,}-"
                f"{player1['accuracy']['Miss']:,}"
            )
            accuracy_str2 = (
                f"{player2['accuracy']['Perfect']:,}-"
                f"{player2['accuracy']['Great']:,}-"
                f"{player2['accuracy']['Good']:,}-"
                f"{player2['accuracy']['Bad']:,}-"
                f"{player2['accuracy']['Miss']:,}"
            )


            if (player1["score"] == player2["score"] and
                player1["perfect_count"] == player2["perfect_count"] and
                player1["max_combo"] == player2["max_combo"]):

                rank_str += f"**引き分け！**\n\n"
                rank_str += f"**{player1['name']}**\n"
                rank_str += f"  スコア: {player1['score']:,}\n"
                rank_str += f"  Perfect数: {player1['perfect_count']:,}\n"
                rank_str += f"  最大コンボ: {player1['max_combo']:,}\n"
                rank_str += f"  精度詳細: {accuracy_str1}\n\n" # 修正された表示形式

                rank_str += f"**{player2['name']}**\n"
                rank_str += f"  スコア: {player2['score']:,}\n"
                rank_str += f"  Perfect数: {player2['perfect_count']:,}\n"
                rank_str += f"  最大コンボ: {player2['max_combo']:,}\n"
                rank_str += f"  精度詳細: {accuracy_str2}\n\n" # 修正された表示形式
            else:
                rank_str += f"**勝者: {player1['name']}**\n"
                rank_str += f"**敗者: {player2['name']}**\n\n"

                rank_str += f"**{player1['name']} (勝ち)**\n"
                rank_str += f"  スコア: {player1['score']:,}\n"
                rank_str += f"  Perfect数: {player1['perfect_count']:,}\n"
                rank_str += f"  最大コンボ: {player1['max_combo']:,}\n"
                rank_str += f"  精度詳細: {accuracy_str1}\n\n" # 修正された表示形式

                rank_str += f"**{player2['name']} (負け)**\n"
                rank_str += f"  スコア: {player2['score']:,}\n"
                rank_str += f"  Perfect数: {player2['perfect_count']:,}\n"
                rank_str += f"  最大コンボ: {player2['max_combo']:,}\n"
                rank_str += f"  精度詳細: {accuracy_str2}\n\n" # 修正された表示形式
        else: # 3人以上の場合
            current_rank = 1
            for i, player in enumerate(players_results):
                # 精度詳細文字列を生成
                accuracy_str = (
                    f"{player['accuracy']['Perfect']:,}-"
                    f"{player['accuracy']['Great']:,}-"
                    f"{player['accuracy']['Good']:,}-"
                    f"{player['accuracy']['Bad']:,}-"
                    f"{player['accuracy']['Miss']:,}"
                )

                # 前のプレイヤーと比較して同順位か判定
                if i > 0 and (player["score"] == players_results[i-1]["score"] and
                                player["perfect_count"] == players_results[i-1]["perfect_count"] and
                                player["max_combo"] == players_results[i-1]["max_combo"]):
                    # 同順位であれば、順位を更新しない
                    pass 
                else:
                    # 異なる順位であれば、現在のループインデックス+1を新しい順位とする
                    current_rank = i + 1 

                rank_str += f"**{current_rank}位**: {player['name']}\n"
                rank_str += f"  スコア: {player['score']:,}\n"
                rank_str += f"  Perfect数: {player['perfect_count']:,}\n"
                rank_str += f"  最大コンボ: {player['max_combo']:,}\n"
                rank_str += f"  精度詳細: {accuracy_str}\n\n" # 修正された表示形式

        embed.add_field(name="順位", value=rank_str, inline=False)
        embed.set_footer(text=f"集計者: {interaction.user.display_name}")

        await interaction.followup.send(embed=embed, ephemeral=False)
        logging.info(f"Rankmatch result embed sent for {interaction.user.name}.") # ロギングを追加

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """モーダル処理中にエラーが発生した場合の処理"""
        logging.error(f"Error in RankmatchResultModal for user {interaction.user.name}: {error}", exc_info=True) # ロギングを追加
        await interaction.response.send_message("モーダル処理中にエラーが発生しました。", ephemeral=True)


class ProsekaRankmatchResult(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.info("ProsekaRankmatchResult cog initialized.") # ロギングを追加

    @app_commands.command(name="pjsk_rankmatch_result", description="ランクマッチの結果を投稿・集計します。(最大5人対応)")
    # SUPPORT_GUILD_ID を直接使用
    @app_commands.guilds(discord.Object(id=SUPPORT_GUILD_ID))
    async def pjsk_rankmatch_result(self, interaction: discord.Interaction):
        """ランクマッチの結果を入力するためのモーダルを表示します。"""
        logging.info(f"Command '/pjsk_rankmatch_result' invoked by {interaction.user.name} (ID: {interaction.user.id}).") # ロギングを追加
        try:
            modal = RankmatchResultModal()
            await interaction.response.send_modal(modal)
            logging.info(f"RankmatchResultModal sent to {interaction.user.name}.") # ロギングを追加
        except Exception as e:
            logging.error(f"Failed to send RankmatchResultModal to {interaction.user.name}: {e}", exc_info=True) # ロギングを追加
            if not interaction.response.is_done():
                await interaction.response.send_message("ランクマッチ結果入力モーダルの表示に失敗しました。", ephemeral=True)


async def setup(bot):
    cog = ProsekaRankmatchResult(bot)
    await bot.add_cog(cog)
    logging.info("ProsekaRankmatchResult cog loaded.") # ロギングを追加
