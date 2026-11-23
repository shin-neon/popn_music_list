# popn_music_list

pop'n music 曲探しをするスマホ・PC向け静的検索サイト。

## データについて
- 2026-11-21に提供されたAC旧曲・新曲Wiki、Lively Wiki、Lively公式HTMLを抽出・照合。
- AC限定は、AC曲一覧にあり、Lively公式・Lively Wikiのいずれにも見当たらない曲。表記差で誤判定の可能性あり。
- Lively Wikiにあり公式に見当たらないAC曲は「要確認」に隔離。
- 同名曲は簡易統合。譜面別バージョン差、移植・改題、BPM表記差等は未精査。
- レベルは抽出元表の値。L/E/N/H/EX の列順。曲によって譜面差あり。
- 作品欄は元Wikiの区分見出しをベースにしており、厳密な初出ではない場合あり。
- データは自動更新されません。最新の収録状況はゲーム内・公式サイトを優先してください。
- GitHub Pages等のHTTPサーバーで使用（ローカルfile://ではfetchが制限される場合あり）。

## マスタデータの作成
1. `build_ac_music_list\run.bat` を実行すると、e-amusementのpop'n music公式曲一覧からバージョン値 `0`〜`29` を順に取得し、各バージョンのページングをたどって `build_ac_music_list\ac_master.csv` を作成します。
2. `build_lively_music_list\run.bat` を実行すると、Lively公式収録曲ページを取得し、曲名とアーティスト名が一致するACデータから作品・譜面レベルを補って `build_lively_music_list\lively_master.csv` を作成します。

どちらもPython 3と標準ライブラリのみを使用します。ACページがログイン画面やエラー画面を返した場合は、誤った空マスタを作らずエラーで終了します。ID・パスワードやCookieは使用しません。

## v1.1 更新内容
- タイトルを「楽曲検索補助ツール」に変更、紹介文を削除。
- 登場作品の表記を指定された pop'n music 1〜29 の名称に統一。
- 初登場作品が不明・家庭用・Lively・イベント分類の曲は、誤った作品番号を付与せず元の分類を維持。
- 作品選択の並びを番号順に整理。


v1.3: Added five user-confirmed missing AC songs. Full audit is still in progress.


## v1.4 修正
クラシック2〜11のrowspan由来の欠落10曲を追加。AC・Lively両方に分類。なお全HTMLのrowspanを含む全件再解析は未完了です。


## v1.5
元HTMLとの結合セル対応の再照合結果を反映。UPPER譜面は通常譜面と別の曲として登録。詳細はAUDIT.mdを参照。

## v1.6
- 画面内のハート記号を削除。
- 収録区分の初期値を「すべて」に変更し、表示順を「すべて → AC限定 → Livelyのみ → AC＋Lively → 要確認」に変更。
- 条件リセットも「すべて」に戻るよう変更。

## v1.7
公式AC・Lively CSVの和集合から再構築。AC 1909行、Lively 1445行（完全重複3行除外）。2043件。通常/UPPER別。レベルはAC優先、両機種の値を別フィールドに保持。Eは公式CSVにないため未設定。BPM等は旧データから補完。
