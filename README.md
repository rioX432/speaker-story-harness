# Speaker Story Harness

**資料を生成する前に、登壇のストーリーを人間とAIが共同設計するためのハーネス。**

このリポジトリは `rioX432/kotlinfest-2026` の `deck-narrative`、`deck-audience-review`、`deck-prose`、`deck-figure`、`deck-direction`、理解グラフ・根拠台帳・独立レビューから、登壇固有の技術・動画・デザインアセットを切り離す方針で再構成した個人用パッケージです。**元リポジトリの丸ごとコピーではありません。** 元コードの移植方法と採否は [`docs/EXTRACTION.md`](docs/EXTRACTION.md) に記録しています。

## 最大の変更点

スライド生成開始前に、**聴衆の課題 → 現状の手段 → 代替案 → 技術選択の理由 → 検証 → 結論**を説明するストーリーを、人間にレビューしてもらいます。構成順が論理的に見えるだけでは合格しません。「その問題は実在するか」「なぜ今その技術を比較するか」「結論が冒頭の課題へ答えるか」もAIが疑います。

```text
BRIEF → STORY → 独立AI批評 → STORYBOARD (HTML) → 人間の修正指示 ↺
                                                    ↓ 人間が明示的に承認
                                        DRAFT SLIDES → NOTES → VISUAL QA → REHEARSAL
```

AIがストーリーを作成・評価しても、人間の承認を代行しません。スライド作成後に中心的な主張を変えれば、ストーリーの再確認が必要です。1枚ごとに承認を求め続ける設計ではなく、**重要な意思決定の手前だけ**に確認点を置きます。

## すぐ試す

Python 3.10+、標準ライブラリのみでストーリー工程が動きます。

```bash
# サンプルの現在の構成とリスクを確認
python3 harness/storyflow.py audit examples/search-latency-talk
python3 harness/storyflow.py board examples/search-latency-talk
open examples/search-latency-talk/build/storyboard.html  # macOS

# 新しい登壇を開始
python3 harness/storyflow.py init talks/my-talk --title '新しい登壇' --minutes 12
# AIが talks/my-talk/brief.json, story.json, evidence.json を作り込む
python3 harness/storyflow.py review-request talks/my-talk
# 別コンテキストのAIでレビューし、reviews/ai-story-review.json を生成
python3 harness/storyflow.py board talks/my-talk
```

HTMLの各章に感想を書いて **Export feedback** すると `human-feedback.json` がダウンロードされます。これをAIに渡して構成を修正させるか、次のコマンドで取り込めます。

```bash
python3 harness/storyflow.py feedback talks/my-talk --file ~/Downloads/human-feedback.json
# AIが修正し、再度 review-request と board を実行
# 人間が「この構成で進めて」と明示した後にのみ実行
python3 harness/storyflow.py approve talks/my-talk --human-confirmed --note '構成と論点を確認済み'
python3 harness/storyflow.py draft talks/my-talk
python3 harness/storyflow.py deck-audit talks/my-talk
```

`approve` はAIの独立レビューがない場合や重大指摘が未解決の場合は停止します。人間が意図的に進めるなら `--override-reason '具体的な理由'` を追加できます。これは**人間の確認を機械的に証明する手段ではなく、発表者の判断を記録する操作**です。

## Codex / Claude Code と一緒に使う

最初に `AGENTS.md` を読み、`.agents/skills/story-orchestrator/SKILL.md` から開始。Claude Code向けの `.claude/skills/` からも同じSkillへアクセスできます。

AIへの最初の指示例：

> このリポジトリのstory-orchestratorに従って、登壇の構成だけを設計して。最初に現場での課題・代替案・検証の必要性を深掘りし、独立AI批評を受け、HTMLストーリーボードを提示して。**私が構成を確認するまではスライド生成しない。**

コンテキストが切り替えられない場合は、独立レビューを実施済みと表示せず `reviewer_independent: false` または未実施で記録すること。

## 主なファイル

| 場所 | 意味 |
| --- | --- |
| `brief.json` | 目的、聴講者、持ち帰り、時間、公開制約 |
| `story.json` | Big Idea、問いと答え、章ごとの主張・接続・時間・根拠ID |
| `evidence.json` | 事実・仮説・PoC・未検証の出所と適用範囲 |
| `reviews/ai-story-review.json` | AIの意味レビュー。本文のハッシュにひも付く |
| `build/storyboard.html` | 人間が読んで章ごとの指示を出すレビュー画面 |
| `approvals/story-approved.json` | 現行ストーリーへの明示的な承認記録 |
| `draft/slides.md` | 承認後のみ生成できるスライド骨子。最終資料ではない |

資料本体はMarp、Slidev、Google Slides、既存PythonのPPTX/PDFジェネレーターなどを交換可能な出力として扱います。**このリポジトリのCLIがそれらを自動インストール・レンダリングするわけではありません。** 続く制作は [`docs/PRODUCTION.md`](docs/PRODUCTION.md) と各Skillの担当範囲に従います。

## 状態と安全性

- **PASS** は機械的整合性を示すだけ。論理・説得力・理解度を自動認証しません。
- **UNVERIFIED** は重要な人間/AIレビューや根拠が未確認という意味。成功へ丸めません。
- 誤った数値や未検証を隠す代わりに、主張の範囲を適切に限定します。
- 仕事で知り得た非公開コードや社内方針、イベント固有の動画、フォント等は移植しません。
- 同梱の `examples/search-latency-talk` は架空の題材で、数値はすべて説明用の仮の値です。実在のサービスや製品の性能を示すものではありません。
- 公開リポジトリとして配布します。`scripts/publish-public.sh` は本人のGitHub認証環境で明示的に実行する手順で、CLIが自動でpushすることはありません。

## テスト

```bash
python3 -m unittest discover -s tests -v
python3 harness/storyflow.py audit examples/search-latency-talk
```

新規リポジトリの作成・GitHubへのpushはこの配布物には含まれていません。個人環境で `gh` 認証済みなら [`scripts/publish-public.sh`](scripts/publish-public.sh) で公開リポジトリを新設できます。

## ライセンス

[MIT License](LICENSE)
