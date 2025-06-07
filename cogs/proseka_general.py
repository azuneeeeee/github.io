import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import logging
import asyncio # 非同期処理のためにインポート

# main.py から必要なグローバルチェック関数をインポート
from main import is_not_admin_mode_for_non_owner, is_bot_owner

# main.pyからGUILD_IDとRANKMATCH_RESULT_CHANNEL_IDをインポート
try:
    from main import GUILD_ID, RANKMATCH_RESULT_CHANNEL_ID
except ImportError:
    logging.error("Failed to import GUILD_ID or RANKMATCH_RESULT_CHANNEL_ID from main.py.")
    GUILD_ID = 0
    RANKMATCH_RESULT_CHANNEL_ID = 0

class ProsekaGeneralCommands(commands.Cog):
    def __init__(self, bot: commands.Bot): # ★修正: songs_data 引数を削除★
        self.bot = bot
        # 楽曲データはボットインスタンスから取得
        self.songs_data = self.bot.proseka_songs_data # ★修正: ここでデータを取得★
        self.ap_fc_rate_cog = None # setup_hookで設定される予定
        logging.info("ProsekaGeneralCommands Cog initialized.")

    @commands.Cog.listener()
    async def on_ready(self):
        # ボットが完全に準備完了したら、クロス参照を設定
        if not self.ap_fc_rate_cog and self.bot.is_ready():
            self.ap_fc_rate_cog = self.bot.get_cog('ApFcRate')
            if self.ap_fc_rate_cog:
                logging.info("ProsekaGeneralCommands: ap_fc_rate_cog reference set via on_ready.")
            else:
                logging.warning("ProsekaGeneralCommands: ApFcRate cog not found on_ready.")

    @app_commands.command(name="pjsk_list_songs", description="プロセカの楽曲リストをソート・フィルター付きで表示します。")
    @app_commands.describe(
        sort_by="ソート基準 (level, title)",
        difficulty="難易度 (easy, normal, hard, expert, master, append)",
        level="楽曲レベル (例: 28)",
        tag="タグ (例: 2DMV)",
        producer="作詞者 (例: deco*27)",
        character_type="キャラクタータイプ (例: VIRTUAL_SINGER)",
        max_results="表示する最大楽曲数 (デフォルト: 10, 最大: 50)"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @is_not_admin_mode_for_non_owner() # 管理者モードチェックを適用
    async def pjsk_list_songs(
        self,
        interaction: discord.Interaction,
        sort_by: str = "level",
        difficulty: str = None,
        level: int = None,
        tag: str = None,
        producer: str = None,
        character_type: str = None,
        max_results: app_commands.Range[int, 1, 50] = 10
    ):
        logging.info(f"Command '/pjsk_list_songs' invoked by {interaction.user.name}.")
        await interaction.response.defer(ephemeral=False)

        # 楽曲データがロードされているか確認
        if not self.songs_data:
            await interaction.followup.send("楽曲データがまだロードされていません。ボットが完全に起動するまでお待ちください。", ephemeral=True)
            logging.warning("Songs data not loaded when /pjsk_list_songs was called.")
            return

        filtered_songs = list(self.songs_data)

        # フィルター処理
        if difficulty:
            difficulty_lower = difficulty.lower()
            if difficulty_lower not in ["easy", "normal", "hard", "expert", "master", "append"]:
                await interaction.followup.send(f"無効な難易度です。`easy`, `normal`, `hard`, `expert`, `master`, `append` から選んでください。", ephemeral=True)
                return
            filtered_songs = [s for s in filtered_songs if s.get(difficulty_lower) is not None]

        if level:
            # 難易度が指定されている場合のみレベルでフィルタリング
            if difficulty:
                filtered_songs = [s for s in filtered_songs if s.get(difficulty_lower) == level]
            else:
                await interaction.followup.send("レベルでフィルタリングするには、難易度も指定してください。", ephemeral=True)
                return

        if tag:
            tag_lower = tag.lower()
            filtered_songs = [s for s in filtered_songs if any(t.lower() == tag_lower for t in s.get("tags", []))]

        if producer:
            producer_lower = producer.lower()
            filtered_songs = [s for s in filtered_songs if any(p.lower() == producer_lower for p in s.get("producers", []))]

        if character_type:
            character_type_upper = character_type.upper()
            filtered_songs = [s for s in filtered_songs if character_type_upper in s.get("character_types", [])]

        # ソート処理
        if sort_by == "level" and difficulty:
            filtered_songs.sort(key=lambda s: s.get(difficulty.lower(), 0), reverse=True)
        elif sort_by == "title":
            filtered_songs.sort(key=lambda s: s.get("title", ""))
        else:
            if sort_by != "title": # levelソートで難易度指定がない場合のエラー
                await interaction.followup.send("`level` でソートするには、`difficulty` も指定してください。または `title` でソートしてください。", ephemeral=True)
                return

        # 結果表示
        if not filtered_songs:
            await interaction.followup.send("指定された条件に一致する楽曲は見つかりませんでした。", ephemeral=True)
            return

        response_message = "### 楽曲リスト:\n"
        for i, song in enumerate(filtered_songs[:max_results]):
            song_title = song.get("title", "不明な楽曲")
            song_level = song.get(difficulty.lower()) if difficulty else "N/A"
            response_message += f"{i+1}. **{song_title}**"
            if difficulty:
                response_message += f" ({difficulty.capitalize()}: Lv.{song_level})"
            response_message += "\n"

        # メッセージが2000文字を超える場合は分割して送信
        if len(response_message) > 2000:
            chunks = [response_message[i:i+1990] for i in range(0, len(response_message), 1990)]
            for chunk in chunks:
                await interaction.followup.send(chunk)
        else:
            await interaction.followup.send(response_message)
        
        logging.info(f"Displayed {len(filtered_songs[:max_results])} songs for {interaction.user.name}.")

    @app_commands.command(name="pjsk_random_song", description="プロセカの楽曲からランダムで1曲選曲します。")
    @app_commands.describe(
        difficulty="難易度 (easy, normal, hard, expert, master, append)",
        level="楽曲レベル (例: 28)",
        min_level="最小レベル (例: 25)",
        max_level="最大レベル (例: 30)"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @is_not_admin_mode_for_non_owner() # 管理者モードチェックを適用
    async def pjsk_random_song(
        self,
        interaction: discord.Interaction,
        difficulty: str = None,
        level: int = None,
        min_level: int = None,
        max_level: int = None
    ):
        logging.info(f"Command '/pjsk_random_song' invoked by {interaction.user.name}.")
        await interaction.response.defer(ephemeral=False)

        if not self.songs_data:
            await interaction.followup.send("楽曲データがまだロードされていません。ボットが完全に起動するまでお待ちください。", ephemeral=True)
            logging.warning("Songs data not loaded when /pjsk_random_song was called.")
            return

        eligible_songs = list(self.songs_data)

        # 難易度フィルター
        difficulty_lower = difficulty.lower() if difficulty else None
        if difficulty_lower:
            if difficulty_lower not in ["easy", "normal", "hard", "expert", "master", "append"]:
                await interaction.followup.send(f"無効な難易度です。`easy`, `normal`, `hard`, `expert`, `master`, `append` から選んでください。", ephemeral=True)
                return
            eligible_songs = [s for s in eligible_songs if s.get(difficulty_lower) is not None]
            
        # レベルフィルター
        if level is not None:
            if difficulty_lower: # 難易度が指定されている場合のみレベルでフィルタリング
                eligible_songs = [s for s in eligible_songs if s.get(difficulty_lower) == level]
            else:
                await interaction.followup.send("特定のレベルで選曲するには、難易度も指定してください。", ephemeral=True)
                return
        
        # 最小/最大レベルフィルター
        if min_level is not None:
            if difficulty_lower:
                eligible_songs = [s for s in eligible_songs if s.get(difficulty_lower, 0) >= min_level]
            else:
                await interaction.followup.send("最小レベルで選曲するには、難易度も指定してください。", ephemeral=True)
                return
        
        if max_level is not None:
            if difficulty_lower:
                eligible_songs = [s for s in eligible_songs if s.get(difficulty_lower, 99) <= max_level]
            else:
                await interaction.followup.send("最大レベルで選曲するには、難易度も指定してください。", ephemeral=True)
                return

        if not eligible_songs:
            await interaction.followup.send("指定された条件に一致する楽曲が見つかりませんでした。", ephemeral=True)
            return

        selected_song = random.choice(eligible_songs)

        embed = discord.Embed(
            title="🎵 ランダム選曲結果 🎵",
            description=f"**{selected_song.get('title', '不明な楽曲')}**",
            color=discord.Color.magenta()
        )
        
        # 各難易度のレベルを表示
        difficulty_levels = []
        for diff_key in ["easy", "normal", "hard", "expert", "master", "append"]:
            level_val = selected_song.get(diff_key)
            if level_val is not None:
                difficulty_levels.append(f"{diff_key.capitalize()}: Lv.{level_val}")
        
        if difficulty_levels:
            embed.add_field(name="難易度情報", value="\n".join(difficulty_levels), inline=False)

        if selected_song.get("image_url"):
            embed.set_thumbnail(url=selected_song["image_url"])
        
        # AP/FCレート表示機能が利用可能であれば追加
        if self.ap_fc_rate_cog:
            user_id_str = str(interaction.user.id)
            rates = self.ap_fc_rate_cog.get_user_ap_fc_rates(user_id_str, selected_song.get('title'))
            if rates:
                ap_rate_str = f"{rates['ap_rate']:.2f}% ({rates['ap_count']}/{rates['clear_count']})"
                fc_rate_str = f"{rates['fc_rate']:.2f}% ({rates['fc_count']}/{rates['clear_count']})"
                embed.add_field(name="AP/FCレート (あなた)", value=f"AP: {ap_rate_str}\nFC: {fc_rate_str}", inline=False)
            else:
                embed.add_field(name="AP/FCレート (あなた)", value="この楽曲のデータはありません。", inline=False)
        else:
            logging.warning("AP/FC Rate Cog not available for pjsk_random_song.")


        await interaction.followup.send(embed=embed)
        logging.info(f"Random song '{selected_song.get('title')}' selected for {interaction.user.name}.")

async def setup(bot): # ★修正: songs_data 引数を削除★
    cog = ProsekaGeneralCommands(bot)
    await bot.add_cog(cog)
    logging.info("ProsekaGeneralCommands Cog loaded.")

