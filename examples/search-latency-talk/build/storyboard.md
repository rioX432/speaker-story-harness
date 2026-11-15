# 検索が遅い：キャッシュで足りるか、検索エンジンを足すか | Storyboard

**Audience:** Webサービスを運用するバックエンドエンジニア（LT 12分）
**Big Idea:** 検索エンジンを足す前に、時間がクエリ・DB・ネットワークのどこにかかっているかを測って選ぶ
**Opening Question:** 検索APIが遅いとき、専用の検索エンジンを導入すれば本当に速くなるのか？
**Final Answer:** 検索エンジンの導入は既定路線ではない。既存DBで直せる部分を先に直し、運用コストを払っても利益が残る条件でのみ導入を検証する
**Fingerprint:** `3b923f5bb6d9742249dcaf512eecb515b17f68a171d760c5bc8264cb21cf1b25`
**AI Review:** current (independent: False)
**Human Approval:** missing

## Story flow

### 1. [context] 商品や記事の検索を、アプリ本体と同じリレーショナルDBのLIKE検索で始めるのは一般的で、小さな規模では十分に機能する (1.0 min)
- Audience asks: 多くのWebサービスは、検索をどこで処理している？
- Why now: 検索エンジンの話から始めず、現状の構成が妥当な出発点だと聴衆と揃える
- Evidence: E1
- Leads to: データが増えると、何のコストを確認すべきか？

### 2. [problem] 検索の遅さは、クエリの実行だけでなく、結果の整形と転送にも分かれて現れる (1.5 min)
- Audience asks: データが増えると、何のコストを確認すべきか？
- Why now: 「検索エンジンが速いらしい」という解決策ありきから離れ、測る対象を分解する
- Evidence: E2
- Leads to: エンジンを足す前に、既存DBのままで改善できないか？
- ⚠ major/open: 起こりうる課題が、実際に起きている性能問題と誤解される余地がある → 実環境の観測で示すか、「データが増えた場合のシナリオ」と明示する

### 3. [baseline] インデックスの追加と取得列の絞り込みだけで、仮のデータでは応答時間が大きく下がる (1.5 min)
- Audience asks: エンジンを足す前に、既存DBのままで改善できないか？
- Why now: 新しい技術を採用しない最良の対案を比較に含める
- Evidence: E3
- Leads to: それでも検索エンジンを検討する理由はどこにある？

### 4. [alternative] 転置インデックスは語の一致や並べ替えに向くが、データの同期と運用の手間は新たに増える (1.5 min)
- Audience asks: それでも検索エンジンを検討する理由はどこにある？
- Why now: 技術の好みでなく、設計上どんな利益と負担があるかを説明する
- Evidence: E4
- Leads to: その利益が運用の手間を払っても残るか、どう確かめる？
- ⚠ major/open: 一般的な特徴の説明が、この比較での性能利益の証明と受け取られうる → 公式一次情報と設計の違いを照合し、仮説形成の参考として位置づける

### 5. [hypothesis] 同じクエリ集合で、DB内の処理・ネットワーク込み・整形込みを別々に測る (1.0 min)
- Audience asks: その利益が運用の手間を払っても残るか、どう確かめる？
- Why now: 公平な比較条件を先に示し、恣意的なベンチマークを避ける
- Evidence: E5
- Leads to: 同じデータで実装を切り替えると、何が変わる？

### 6. [experiment] 同じ架空の商品データに対して、DB検索と検索エンジンを切り替えられ、返る結果の集合が一致した (1.5 min)
- Audience asks: 同じデータで実装を切り替えると、何が変わる？
- Why now: 数値が何を比較したものかを、先に見せて共有する
- Evidence: E6
- Leads to: エンジンの検索が速くても、その差は応答全体に残る？

### 7. [results] 仮のデータでは検索そのものはエンジンが短いが、ネットワークと整形を含めると差は小さい (2.0 min)
- Audience asks: エンジンの検索が速くても、その差は応答全体に残る？
- Why now: 期待と結果のギャップを見せ、測定条件を添えて限定する
- Evidence: E7
- Leads to: では、DBの改善と検索エンジンをどう選べばよい？
- ⚠ minor/open: 1台の環境の測定が、本番での結論と同一視されるおそれがある → 測定条件と測定終点を最小限添え、本番での結論を避ける

### 8. [decision] 支配的な処理を自分のデータで測り、応答全体で利益が残るときに検索エンジンを選ぶ (2.0 min)
- Audience asks: では、DBの改善と検索エンジンをどう選べばよい？
- Why now: 冒頭の問いに、聴講者が持ち帰れる判断として答える
- Evidence: E3, E7
- Leads to: closing

## Machine-audit observations

- AI story review has no independent-context attestation

## Human revision requests

Use the HTML board to export per-beat feedback, or tell your AI agent the changes conversationally.
