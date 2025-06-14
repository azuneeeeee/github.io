# プロセカbot
Discordというアプリで使えるプロセカのBOTです。<br>
### 何が出来るのか？
- 普通のランダム選曲が出来る
- ランクマ形式でランダム選曲が出来る
- AP率、FC率等の計算が出来る
- プロセカに収録されている楽曲確認出来る
- 疑似ランクマでリザルトの精度を計算が出来る<br>
BOTの招待リンクは[こちら](https://discord.com/oauth2/authorize?client_id=1374468062815981610&permissions=2147765248&integration_type=0&scope=bot+applications.commands)<br>
サーバーを所有していない方は[こちら](https://discord.gg/cvD9dG5UjA)のサポートサーバーに参加してください。
## １BOTをサーバーに導入
(サーバー所有していない方はスキップで大丈夫です。)<br>
上の招待リンクを踏むとこのような画面に飛ばされます。<br>
![image](https://github.com/user-attachments/assets/7df97e83-b5b1-407c-a7a4-10b24d6c9a17)<br>
画像に写っている「あずねーうのFF限定プロセカサーバー」って書かれてる場所で自分の導入したいサーバーを選択して「はい」を押してください。<br>
### :warning:サーバーの管理者権限を所有していないとBOT導入出来ません。:warning:
「はい」を押したら、BOTの権限を設定できます。<br>
デフォルトだと、下記の権限にチェック付いてると思います。<br>
【チャンネルを見る：メッセージを送信：メッセージの管理：埋め込みリンク：メッセージ履歴を読む】<br>
![image](https://github.com/user-attachments/assets/ddd94dfe-7611-45e4-a663-cbed96da429a)<br>
### :warning:全てチェック入れた状態で招待しないとうまくBOTが機能しない可能性があります。:warning:
認証を押したらBOTの導入完了です。<br>
(Discordのアカウントを二段階認証している方は二段階認証する必要があります)<br>
## サーバーに参加(サーバー所有していない方向け)
サーバー所有していない方向けと書いてありますが、BOT導入していて、サポートサーバーに参加したいって方でも参加出来ます。<br>
<br>
サーバー参加したら最初にルールの同意が必要になります。<br>
<br>
### PC版、web版↓
![image](https://github.com/user-attachments/assets/ea0e6a63-a45c-4b75-a752-72ede6d6e238)<br>
### スマホ版↓
![image](https://github.com/user-attachments/assets/e3c5b62b-3124-4cd9-8bfd-f13ceb43c236)<br>
:red_circle:の円で囲まれてる部分を押すと、次のよう画面に飛ばされます。<br>
同意の所にチェックを入れ、「完了！」を押してください。<br>
<br>
上の画像にも書いてあった「認証はこちらから」の部分をタップし、「🤖認証する」押してください。<br>
そしたら下の画像で🔴の円で囲まれてる部分、「Click here」を押しサイトに飛んでください。<br>
![image](https://github.com/user-attachments/assets/6d64062c-b83e-463f-87f5-4f44ecdc0bc8)
![image](https://github.com/user-attachments/assets/4e16445c-4c7c-44e6-b38f-4a1354a7977b)
１「Login to verify」を押す。<br>
<br>
２ Discordにログインし、スクロールしてから認証を押す。<br>
<br>
３ ログインしたら、Verifiを押す。(下の画像の部分)<br>
<br>
４ 画面中央に出てくる「Hold to verify」を長押しすれば、認証完了です。<br>
<br>
![image](https://github.com/user-attachments/assets/9231b5b0-799a-476a-97ed-cb6b801a8c25)
### :warning:認証を1時間以内で行わないとサーバーからキックされるので注意:warning:<br>
<br>
プロセカコマンド1⃣というチャンネルを探し、開いたら準備完了です！<br>

## ２ BOT使い方<br>
このBOTには下記のコマンドが使用可能です。<br>
- pjsk_random_song
- pjsk_rankmatch_song
- pjsk_list_song
- pjsk_ap_fc_rate
- pjsk_rankmatch_result
- pjsk_record_result(サポートサーバー限定コマンド)<br>
  全部のコマンドを詳しく説明して行きます！<br>
## ２-１ pjsk_random_song<br>
このコマンドは、いつもの一人でやる時に使えるランダム選曲出来るコマンドです。<br>
<br>
え？だったら普通の使えば良くね？って思いますよね？<br>
<br>
**このコマンドは、複数の難易度を指定でき、かつ、選ばれるレベル範囲も指定出来ちゃいます！**<br>
<br>
pjsk_random_songだけで送信するとランダム選曲かつ、難易度もランダムに選ばれます。<br>

### 難易度指定<br>
/pjsk_random_songをチャット欄に打ったら「difficulty」を押し、難易度を入力してください。<br>
<br>
HARDのみの場合は「HARD」MASTERの場合は「MASTER」<br>
<br>
複数難易度を指定したい場合はこのように打ちます。<br>
<br>
「EXPERT,MASTER,APPEND」<br>
<br>
この場合はEXPERTとMASTERとAPPENDの中からランダム選曲かつ難易度も3つの中から選ばれます。<br>
<br>
複数難易度を指定したい場合は必ず「コンマ(,)」を入れてくださいね。<br>

### レベル範囲を指定<br>
/pjsk_random_songをチャット欄に打ったら「level_min level_max」を押し、範囲を入力してください(数字のみ)<br>
<br>
スマホのアプリ版を使ってる方は「任意」と書かれてるところを右にスクロールすれば出てきます。<br>
<br>
「level_min」選ばれる範囲の最低レベル<br>
「level_max」選ばれる範囲の最高レベル<br>
<br>
例<br>
/pjsk_random_song level_min:30 level_max:31<br>
<br>
この場合はレベル30〜31の範囲でのみ選曲してくれます。<br>
これに難易度を指定することも可能です。<br>
<br>
例<br>
/pjsk_random_song difficulty:APPEND level_min:28 level_max:33<br>
<br>
この場合は難易度APPENDのみでレベル28〜33の範囲で選曲してくれるって事です。<br>

## ２-２ pjsk_rankmatch_song<br>
pjsk_rankmatch_songはランクマ形式でランダム選曲が出来ます。<br>
<br>
チャット欄に打って、ランクを選択するだけで使用出来ます。<br>
<br>
簡単だね<br>

## ２-３ pjsk_ap_fc_rate<br>
pjsk_ap_fc_rateはAP率、FC率等を自動計算してくれるコマンドです。<br>
<br>
送信するとこのような埋め込みが送信されます。<br>
![image](https://github.com/user-attachments/assets/21c15282-1bd7-4a93-a4e3-042f86cad828)
- 「AP」(ALL PERFECTの略)
- 「FC」(FULL COMBOの略)
- 「クリア」
- 「クリア失敗」<br>
<br>
この4つのボタンを押すと「総試行回数」が増えて、何回やったか分かるようになります。<br>
<br>
このコマンドの使用中にpjsk_rankmatch_songや、pjsk_random_songを使用すると、メッセージが再送信され、内容引き継がれるようになってます。<br>
<br>
pjsk_ap_fc_rateの任意の項目でこれがあると思います。<br>
<br>
- 「initial_ap」<br>
- 「initial_fc」<br>
- 「initial_clear」<br>
- 「initial_fail」<br>
<br>
この任意で入力出来る項目は、使用中にBOTがオフラインになったりしても、手動で回数を入力すれば引き継げるようになってます。<br>
<br>
## ２-４ pjsk_list_song
このコマンドはプロセカに収録されている楽曲リストを見ることができます。<br>
<br>
デフォルトだと配信順に設定されています。<br>
<br>
レベル順は難易度フィルターを設定したら自動並び替えられます。<br>
<br>
## ２-5 pjsk_rankmatch_result<br>
このコマンドはプロセカ疑似ランクマした際にランクマッチ形式でスコア計算してくれるコマンドです。<br>

### 疑似ランクマとは<br>
疑似ランクマは、みんなでライブで最大5人までランクマッチみたいな対戦をする事を言います<br>

### 使い方<br>
コマンドを送信すると、下の画像のような画面に飛ばされます。
![image](https://github.com/user-attachments/assets/4f59ecb5-ff22-4048-827f-eab730a44809)<br>
5つの入力出来る部分があると思います。<br>
<br>
2人〜最大5人まで入力可能です。<br>
<br>
プレイヤー○の横に「P-G-GO-B-M」と書いてあります。<br>
<br>
これは「PERFECT-GREAT-GOOD-BAD-MISS」を略して書いてます。<br>
<br>
例<br>
1000-0-0-0-0, 1000<br>
999-0-0-0-1, 500<br>
<br>
精度を入力したら、コンマ(,)を入れ、最大コンボ数を入れます。<br>
<br>
プレイヤー１、２は入力必須ですが、３〜5は任意になります。<br>
<br>
2人でやった場合は勝ちか負けか引き分けかスコアで勝敗付きます。<br>
<br>
スコアが同じの場合は、PERFECT数、最大コンボ数の順で勝敗付きます。<br>
<br>
残りライフは、他のプレイヤーからわざわざ聞かないと行けないっていう理由もあり、導入しておりません。<br>
<br>
3人以上でプレイする場合は勝敗のつき方は変わりませんが、順位が出るようになります。<br>
<br>
計算が苦手な方にオススメですね<br>

## ３ サポートサーバー専用コマンド<br>
## ３-１ pjsk_record_result<br>
このコマンドは1曲だけ精度を記録する事ができるコマンドです。<br>
<br>
コマンドを送信すると、下の画像のような埋め込みが出てきます。<br>
![image](https://github.com/user-attachments/assets/a3b50628-0c7c-4dcc-a53f-09cc95e8ad30)<br>
「精度を記録する」を押します。<br>
最初は曲のタイトルと難易度のみ入力可能です。<br>
<br>
入力したら、埋め込みの色が、難易度に合った色になり、曲に合ったジャケットの画像が右上に表示されます。<br>
この状態コマンドを再送信すると、下のような埋め込みになります。<br>
![image](https://github.com/user-attachments/assets/61c3e05a-e360-4b49-9bf3-ed2e7f7d9d03)
再送信する意味はありませんが、曲のタイトルと難易度、レベルが表示されます。<br>
<br>
「リザルトを記録」を押すと、精度、最大コンボ、LATE/FAST/FLICK、現在のクリア状況が入力できます。<br>
<br>
入力すると、下のようになります。<br>
![image](https://github.com/user-attachments/assets/25a2d3ed-e857-4cd2-95c8-c4840c9ac0ea)
例なので、わざわざこのように入力する必要はありません。<br>
<br>
練習したい時に使っていただけると幸いです。<br>
# さいごに<br>
ここまで読んでくれた方、ありがとうございます！<br>
良かったらプロセカbot，使ってみてくださいね！
