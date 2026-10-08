# 学習した Skill の連続再利用（2026-10-08）

実 Retriever / Selector / Generator / Worker / Critic と Docker / Gateway / 固定 Dataset を使って検証しました。
本番コードは変更せず、既存 integration test に学習直後の同一 Intent・言い換え Intent の再利用を追加しました。

## 同じ新規一時 Library での連続3実行

学習した Skill UUID: `e64b7b7d-bea5-4247-9cfc-085853ebe490`

| 実行 | Intent | selected | learned | Library | Generator / 保存 |
|---|---|---|---|---|---|
| 1 | 東京都23区の平均人口を求める | None | `e64b7b7d-bea5-4247-9cfc-085853ebe490` | 6→7 | 各1回 |
| 2 | 東京都23区の平均人口を求める | `e64b7b7d-bea5-4247-9cfc-085853ebe490` | None | 7→7 | 追加呼び出しなし |
| 3 | 東京都23区について、1区あたりの平均人口を計算して | `e64b7b7d-bea5-4247-9cfc-085853ebe490` | None | 7→7 | 追加呼び出しなし |

Critic は1回目のみ success=True。2・3回目は同じ学習済み code を実行し、Observation が1回目と一致することを確認しました。

```text
東京都23区の平均人口は 423185.9130434783 です。
```

生成と保存の累積回数は3実行後もそれぞれ1回です。
学習済み Skill は2・3回目とも top-4 の4位に入り、Selector が選びました。

### 検索 UUID の順位

| 順位 | 1回目 | 2回目 | 言い換え |
|---|---|---|---|
| 1 | `befbc141-baad-41bc-abdf-dc34311c3111` | `befbc141-baad-41bc-abdf-dc34311c3111` | `befbc141-baad-41bc-abdf-dc34311c3111` |
| 2 | `e722f367-1ff1-4796-89a3-48cfd1dfcb68` | `e722f367-1ff1-4796-89a3-48cfd1dfcb68` | `e722f367-1ff1-4796-89a3-48cfd1dfcb68` |
| 3 | `f2d4785a-779a-4927-b75d-65d1e4852ab2` | `f2d4785a-779a-4927-b75d-65d1e4852ab2` | `f2d4785a-779a-4927-b75d-65d1e4852ab2` |
| 4 | `72c549dd-e449-4bef-97f1-e3a2eab27d64` | `e64b7b7d-bea5-4247-9cfc-085853ebe490` | `e64b7b7d-bea5-4247-9cfc-085853ebe490` |

Library: `/tmp/geo-voyager-skill-growth-5841c52c57af4c04a59606bdb99beb07/test_reuse_admin_and_station_t0/skill_library`

[連続3実行の UUID / Observation / 呼び出し回数の記録](skill_growth.json)

## 前回の UUID 4038ef3d の追加確認

前回の一時 Library は確認後の pytest 実行で古い一時ディレクトリとして自動整理されました。
保存済みの実行記録から、初期6件と同一 UUID・code・description の平均人口 Skill を元のパスへ復元しました。
元のディレクトリを保持したままの追試ではなく、同じ保存内容を復元しての追試です。

復元した UUID: `4038ef3d-4721-4a91-905d-a1b8be10367d`

平均人口の同一 Intent と言い換え Intent を連続実行し、両方で検索1位・選択を確認しました。
両実行とも learned=None、Generator / Critic / 保存の呼び出しなし、Library は7件のままです。
Observation は前回の実行記録と完全一致しました。

[前回保存内容を復元した再利用の記録](learned_skill_reuse.json)

## 検証

- 全 unit test: 202件成功。
- 拡張 integration test: 1件成功（既存人口最大・最北端駅の再利用、平均人口の学習・一致再利用・言い換え再利用）。
- 前回 Skill の復元後の実再利用: 2 Intent 成功。
- リポジトリの初期 Skill Library は6件・同一内容のまま。検証 container / network は削除。
- 学習直後の後続 Intent が filesystem Library の新しい Skill を検索して使用することを確認。文字列の完全一致によるキャッシュは追加していません。
- 再利用には top-k 入りと Selector 適合判定の両方が必要です。この2表現の成功を確認した結果であり、任意の言い換えの保証ではありません。

## 再実行

既存の一時 Library が pytest の自動整理対象にならないよう、毎回新しい専用 basetemp を指定します。同じ既存パスを basetemp に再指定しないでください。

```bash
skill_growth_test_dir="/tmp/geo-voyager-skill-growth-$(python3 -c 'from uuid import uuid4; print(uuid4().hex)')"
GEO_VOYAGER_EMBEDDING_BASE_URL=http://10.105.167.163:8080 \
GEO_VOYAGER_EMBEDDING_MODEL=granite-embedding \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest integration/test_intent_executor.py \
  --basetemp "$skill_growth_test_dir" -q -s -W error
```
