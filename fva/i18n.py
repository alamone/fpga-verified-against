"""The results page's own words, in English and Japanese (results/ and results/ja/).

Only the page is translated: the developers' comments quoted as evidence stay in their original
language, since they are the evidence. The Japanese uses the same terms as the "MiSTer FPGA cores"
section on kiban.alamone.net. 実機 appears once, on purpose: the rule for "checked on real hardware"
counts less because the phrase may mean the MiSTer itself, and 実機 carries that same ambiguity.

Native-speaker review (T4YK, 2026-09-30), adopted: 判定 for the reading (was 傾向), 情報量 for
confidence (it is computed from the amount of evidence; levels 少/中/多), 記述率 for coverage, with
an explanation of what a high value means; no 標準 label on update_all's default channel; alpha/beta
channels as アルファ版/ベータ版(要設定). Adapted for accuracy: the readings are MAME基準に近い /
実基板基準に近い / 両方 (his 〜に近い, but not "MAME移植" — a MAME-leaning core is not necessarily a
port — and not "Decapベース" for the hardware side, since decapping is only one kind of hardware
evidence; most hardware-leaning cores rest on schematics or PCB measurements). Coin-Op's alpha/beta
are not called 時限有償: whether they are paid or time-limited is not something we have verified.
"""

LANGS = ("en", "ja")

MSG = {
    "en": {
        "title": "FPGA Verified Against",
        "h1": "FPGA cores: verified against hardware or MAME?",
        "switch": "日本語",
        "intro": "Every arcade core in update_all's three default databases, in six independent databases developers "
                 "publish themselves, and in public repositories found by search, analyzed at the commit its "
                 "distributed build came from. Each meter summarizes the core's <b>own</b> code comments, readme and "
                 "shipped documentation files: statements pointing to MAME on the left, to the original hardware on "
                 "the right. Expand a row to see every statement, linked to its line at that commit; items that point "
                 "at MAME link to the matching line in MAME (commit {mame}).",
        "face": "<b>Taken at face value.</b> These are the developers' own statements, not independently checked. A "
                "core may be verified more, or less, than its comments say. Open source makes a false claim easy to "
                "expose, which is why developers' own words are a reasonable starting point. This method reads source "
                "code, so closed-source cores cannot be assessed <i>this way</i> and are shown separately; black-box "
                "testing against the original hardware or MAME would still be possible, but is far more work and is "
                "not done here.",
        "meta": "Rules {rules} · tool {tool} · generated {gen} · shared CPU/sound libraries and the MiSTer framework "
                "are excluded · below \"low\" confidence the bar is an outline with no needle · readings: under 40 "
                "mostly MAME, over 60 mostly hardware, otherwise both.",
        "search": "Search core, game title, ROM set or repository  ( / )",
        "f.reading": "Reading", "f.independent": "Independent",
        "f.independent.title": "Databases developers publish themselves, outside update_all's built-in list",
        "expand": "Expand all", "collapse": "Collapse all", "reset": "Reset",
        "count.all": "{n} cores", "count.some": "{n} of {t} cores",
        "none": "No cores match.", "showall": "Show all",
        "col.core": "Core", "col.db": "Database", "col.pos": "Needle position, MAME to hardware",
        "col.reading": "Reading", "col.conf": "Confidence", "col.cov": "Coverage",
        "axis.mame": "MAME", "axis.hw": "Hardware",
        "rd.mame": "Mostly MAME", "rd.both": "Both", "rd.hw": "Mostly hardware",
        "rd.none": "Not enough evidence in the code", "rd.none.chip": "Not enough evidence",
        "rd.closed": "Source not published",
        "conf.insufficient": "insufficient", "conf.low": "low", "conf.medium": "medium", "conf.high": "high",
        "db.dist": "MiSTer official", "db.repo": "Repository only",
        "db.independent": "independent database", "db.repoonly": "repository only",
        "db.byrequest": "listed by request", "channel.default": "default", "channel.optin": "opt-in ({x})",
        "channel.optin.alpha": "opt-in (alpha)", "channel.optin.beta": "opt-in (beta)",
        "kiban.link": "This game on kiban.alamone.net (prices, repairs, MiSTer cores)",
        "col.cov.title": "Share of the core's own code that contains any statement. The higher it is, the more "
                         "of the code the reading reflects; when it is low, the reading rests on a few files.",
        "anchor": "Link to this core",
        "statements": "Statements: {tally}", "t.hw": "{n} toward hardware", "t.mame": "{n} toward MAME",
        "t.neutral": "{n} not counted", "nostatements": "No statements found",
        "more": "… {n} more", "alsoinmame": "also in MAME:", "sharestext": "shares text with",
        "mamecompared": "MAME compared: {files}", "related": " + {n} related file(s)",
        "nodriver": "MAME driver: not found",
        "read": "Read: {files} HDL files, {lines} lines ({scope})",
        "scope.Quartus project": "Quartus project", "scope.files.yaml": "files.yaml",
        "scope.all HDL files: no Quartus project found": "all HDL files: no Quartus project found",
        "scope.all HDL files: no cfg/files.yaml": "all HDL files: no cfg/files.yaml",
        "approx": "approx.", "bydate": "matched by date",
        "buildsonly": "database (builds only)",
        "note.nohdl": "the repository holds builds or MRAs, no HDL",
        "note.several": "several candidate repos: {x}",
        "pub.summary": "Published by the team — {n} item(s), not evidence of how this core was verified",
        "pub.caveat": "Chosen and published by the developers. It shows what they decided to share, not how this core "
                      "was built or checked. Anything pointing to MAME would not be visible here, so this list is "
                      "one-sided by design; it places no needle and is not counted anywhere.",
        "pub.item": "Platform write-up {doc} (names “{title}”) — {files}",
        "pub.files": "{n} schematic/layout/manual file(s) in {folder}",
        "pub.nofiles": "written overview; no schematic files of its own",
        "coinop": "Coin-Op Collection also publishes open-source components ({mods}, each with datasheets and a test "
                  "bench). Which of its closed cores use them is not published, so they are not attached to any core "
                  "above.",
        "na.summary": "Repositories found but not analyzed — {n}",
        "na.intro": "Found by the GitHub search or listed in data/extra_repos.tsv. A repository is analyzed once it has "
                    "HDL and a MiSTer build committed; copies of repositories already covered are not counted twice. "
                    "Another {n} search results were not arcade cores (no MRA files, or no HDL and no build: MRA packs, "
                    "scripts, artwork) and are not listed.",
        "na.byrequest": "(listed by request)",
        "how.h": "How the needle is placed",
        "how": "Each comment (or readme sentence) is classified by the rules below. Within a module a rule adds its "
               "points × log2(1 + times it fired), so repetition counts for less than variety. A module's position is "
               "(hardware points + 1) / (all points + 2), from MAME at 0 to hardware at 100. A core's needle is the "
               "size-weighted average over modules that contain statements; the readme and the shipped documentation "
               "files each count like a quarter of the code. Modules with no statements are left out and reported as "
               "coverage. See RULES.md for the reasoning behind each rule.",
        "lg.statement": "Statement", "lg.points": "Points", "lg.side": "Side", "lg.includes": "Includes",
        "side.hardware": "hardware", "side.mame": "MAME", "side.neutral": "neither",
        "notcounted": "Not counted: ROM file names (MiSTer uses MAME's ROM sets by design) and memory addresses (a "
                      "correct core must share them with any correct emulator). Quoted comments remain under their "
                      "authors' licenses; this analysis is published under CC BY 4.0.",
    },
    "ja": {
        "title": "FPGA Verified Against(日本語)",
        "h1": "FPGAコアの検証基準:実基板か、MAMEか",
        "switch": "English",
        "intro": "update_allの標準データベース3つ、開発者が個人で公開しているデータベース6つ、検索で見つかった公開"
                 "リポジトリにあるアーケードコアすべてを、配布されているビルドのコミット時点で解析しています。メーターは"
                 "各コア<b>自体</b>のコードのコメント、README、同梱の資料をまとめたもので、MAMEを指す記述は左、実基板を"
                 "指す記述は右に寄せます。行を開くと、すべての記述がそのコミットの該当行へのリンク付きで表示されます。"
                 "MAMEを指す項目は、MAMEの該当行(コミット {mame})にもリンクします。",
        "face": "<b>記述をそのまま採用しています。</b>ここに示すのは開発者自身の記述で、独自に検証したものではありません。"
                "コアは記述以上に、あるいは記述ほどには検証されていない可能性があります。オープンソースでは事実と異なる"
                "記述はすぐに指摘されるため、開発者自身の言葉は妥当な出発点と考えています。この手法はソースコードを読む"
                "ため、ソース非公開のコアは<i>この方法では</i>評価できず、別に表示しています。実基板やMAMEとの"
                "ブラックボックステストは可能ですが、はるかに手間がかかるため、ここでは行っていません。",
        "meta": "ルール {rules} · ツール {tool} · 生成 {gen} · CPU・音源の共有ライブラリとMiSTerのフレームワークは除外 · "
                "情報量が「少」未満のコアは針のない枠のみ表示 · 判定:40未満はMAME基準に近い、60超は実基板基準に近い、"
                "それ以外は両方",
        "search": "コア名・ゲーム名・ROMセット名・リポジトリで検索 ( / )",
        "f.reading": "判定", "f.independent": "個人配布",
        "f.independent.title": "開発者が個人で公開している、update_all標準外のデータベース",
        "expand": "すべて開く", "collapse": "すべて閉じる", "reset": "リセット",
        "count.all": "{n}件のコア", "count.some": "{t}件中{n}件",
        "none": "該当するコアがありません。", "showall": "すべて表示",
        "col.core": "コア", "col.db": "配布元", "col.pos": "針の位置:左がMAME、右が実基板",
        "col.reading": "判定", "col.conf": "情報量", "col.cov": "記述率",
        "col.cov.title": "コア自身のコードのうち、判断材料となる記述を含む部分の割合。高いほど、判定がコード全体を反映して"
                         "います。低い場合は、一部のファイルの記述だけで判定しています。",
        "axis.mame": "MAME", "axis.hw": "実基板",
        "rd.mame": "MAME基準に近い", "rd.both": "両方", "rd.hw": "実基板基準に近い",
        "rd.none": "コード内の記述が少なく判断できず", "rd.none.chip": "判断材料不足",
        "rd.closed": "ソース非公開",
        "conf.insufficient": "不足", "conf.low": "少", "conf.medium": "中", "conf.high": "多",
        "db.dist": "MiSTer公式", "db.repo": "GitHubのみで配布",
        "db.independent": "個人配布(update_all標準外)", "db.repoonly": "GitHubのみで配布",
        "db.byrequest": "リクエストにより掲載",
        # 標準 alone confused readers; the grouping already says these come with update_all by default.
        "channel.default": "", "channel.optin": "{x}(要設定)",
        "channel.optin.alpha": "アルファ版(要設定)", "channel.optin.beta": "ベータ版(要設定)",
        "kiban.link": "kiban.alamone.netのこのゲームのページ(価格・修理・MiSTerコア)",
        "anchor": "このコアへのリンク",
        "statements": "記述:{tally}", "t.hw": "実基板側 {n}", "t.mame": "MAME側 {n}",
        "t.neutral": "対象外 {n}", "nostatements": "記述なし",
        "more": "…ほか{n}件", "alsoinmame": "MAMEにも記載:", "sharestext": "共通の文言:",
        "mamecompared": "比較したMAME:{files}", "related": " ほか関連ファイル{n}件",
        "nodriver": "MAMEのドライバ:見つからず",
        "read": "解析対象:HDL {files}ファイル、{lines}行({scope})",
        "scope.Quartus project": "Quartusプロジェクト", "scope.files.yaml": "files.yaml",
        "scope.all HDL files: no Quartus project found": "全HDLファイル(Quartusプロジェクトなし)",
        "scope.all HDL files: no cfg/files.yaml": "全HDLファイル(cfg/files.yamlなし)",
        "approx": "推定", "bydate": "日付で照合",
        "buildsonly": "データベース(ビルドのみ)",
        "note.nohdl": "リポジトリにはビルドとMRAのみで、HDLはありません",
        "note.several": "候補のリポジトリが複数:{x}",
        "pub.summary": "開発チームの公開資料 — {n}件(このコアの検証方法を示すものではありません)",
        "pub.caveat": "開発者が選んで公開したものです。共有すると決めた内容を示すだけで、このコアがどう作られ、どう確認"
                      "されたかを示すものではありません。MAMEを指すものはここには現れないため、この一覧は構造上一方に偏って"
                      "います。針の位置には影響せず、どこにも数えていません。",
        "pub.item": "プラットフォームの解説 {doc}(「{title}」の記載あり)— {files}",
        "pub.files": "{folder} に回路図・レイアウト・マニュアルのファイル {n}件",
        "pub.nofiles": "解説のみで、独自の回路図ファイルはなし",
        "coinop": "Coin-Op Collectionは、オープンソースの部品({mods}、それぞれデータシートとテストベンチ付き)も公開"
                  "しています。どの非公開コアがこれらを使っているかは公開されていないため、上のどのコアにも紐付けていません。",
        "na.summary": "見つかったが解析していないリポジトリ — {n}",
        "na.intro": "GitHub検索、またはdata/extra_repos.tsvで見つかったものです。HDLとMiSTer用のビルドがコミットされると"
                    "解析の対象になります。すでに対象のリポジトリの複製は、重複して数えません。このほか検索結果のうち{n}件は"
                    "アーケードコアではない(MRAファイルがない、またはHDLもビルドもないMRA集・スクリプト・アートワーク)ため、"
                    "一覧に含めていません。",
        "na.byrequest": "(リクエストにより掲載)",
        "how.h": "針の位置の決め方",
        "how": "各コメント(またはREADMEの文)を下のルールで分類します。モジュール内では、ルールごとに 点数 × log2(1 + "
               "該当回数) を加算するため、同じ記述の繰り返しより、多様な記述のほうが重くなります。モジュールの位置は "
               "(実基板の点数 + 1) / (全点数 + 2) で、0がMAME、100が実基板です。コアの針は、記述のあるモジュールの規模に"
               "よる加重平均です。READMEと同梱の資料ファイルは、それぞれコードの4分の1として数えます。記述のないモジュール"
               "は平均から除外し、コアのコードのうち記述のある部分の割合を「記述率」として示します(高いほど、判定がコード"
               "全体を反映しています)。各ルールの理由はRULES.md(英語)をご覧ください。",
        "lg.statement": "記述", "lg.points": "点数", "lg.side": "向き", "lg.includes": "含むもの",
        "side.hardware": "実基板", "side.mame": "MAME", "side.neutral": "どちらでもない",
        "notcounted": "対象外:ROMファイル名(MiSTerは設計上MAMEのROMセットを使うため)とメモリアドレス(正しいコアは、"
                      "どの正しいエミュレータとも一致するため)。引用したコメントの権利は各作者にあります。この解析結果は"
                      "CC BY 4.0で公開しています。",
    },
}

# Rule names and what each includes (fva/report.py LABEL holds the English).
LABEL_JA = {
    "hw_specific": ("MAMEのドライバにない実基板の資料を引用",
                    "回路図のシート、部品番号、チップの位置、吸い出したPAL、デキャップ — そのゲームのMAMEドライバに記載がない場合のみ"),
    "hw_ref_in_mame": ("MAMEのドライバにもある実基板の情報・測定値を引用", "対象外:MAMEから写しても同じ記述になるため"),
    "hw_verified": ("実基板で確認したと記載", "オリジナルの基板・PCB・アーケードのハードウェアと明記されている場合"),
    "hw_measured": ("実基板での測定値を記載", "値が示されている場合。MiSTer自体の測定(SignalTapなど)は対象外"),
    "hw_verified_unclear": ("「実機」で確認したと記載", "実基板ではなくMiSTer本体を指す場合もあるため、低めに数える"),
    "hw_files": ("実基板の資料ファイルを同梱", "コア自体のフォルダにある回路図のシート、回路図PDF、PALの論理式"),
    "mame_diverge": ("MAMEとの相違点を記載", "相違を述べるのは、別の参照元があるため"),
    "mame_cited": ("MAMEのソースを引用", "MAMEのファイル・関数・行"),
    "mame_verified": ("MAMEと一致する、MAMEに合わせた、またはMAMEで確認したと記載", "「ground truth: MAME」(MAMEを正とする)を含む"),
    "mame_transcribed": ("MAMEから移植・書き写した、または取り入れたと記載", ""),
    "mame_surrogate": ("MAMEの近似をそのまま採用", "MAME自体が推測・代用と注記している箇所"),
    "copied_text": ("MAMEドライバと同じ文言を含む(出典の明記なし)", "コメント中の6語連続の一致"),
}

# Why a discovered repository was not analyzed (fva/discover.py reasons), by the text before ":" / "(".
REASON_JA = {
    "copy of a covered repository": "対象リポジトリの複製",
    "source only": "ソースのみ(ビルド未コミット)",
    "a port for another FPGA board": "他のFPGAボード向けの移植",
    "superseded": "同じ開発者の旧版",
    "builds only": "ビルドのみ",
    "repository not found": "リポジトリが見つからない",
}
DETAIL_JA = [   # (English pattern, Japanese template) for the detail after the reason
    (r"^no MiSTer build committed yet$", "MiSTer用のビルドがまだコミットされていない"),
    (r"^no HDL in the repository$", "リポジトリにHDLなし"),
    (r"^the same developer's core ships as (.+)$", r"同じ開発者のコアが \1 として配布"),
]
