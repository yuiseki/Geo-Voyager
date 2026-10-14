# 0001 生成コードは sandbox で動かし、外へは Gateway だけを通す

- 日付: 2026-10-08
- 状態: 採用

## 背景

LLM が書いた Python をそのまま実行する。コードの中身は事前に確かめられない。

## 決定

- 生成コードは host では実行せず、Docker sandbox で実行する（`geo_voyager/docker_sandbox.py`）。
  - UID/GID 65534、read-only root filesystem、cap-drop ALL、no-new-privileges、`--pull never`。
  - 既定の枠は memory 128 MiB、CPU 1、PID 128、60 秒（2026-10-14 に 30 秒から変更。Hub 経由の読み込みが 15〜40 秒かかり、正しいコードを止めていた）。分析の枠（[0007](0007-analysis-sandbox.md)）は memory 8 GiB、CPU 4、600 秒。
- Worker は internal network にだけつなぐ。外へ出られるのは Gateway だけで、Gateway は登録済みの Dataset（固定リビジョンの URL）と登録済みのサービスの read-only API だけを中継する。
- ベンチでは、固定リビジョンの表を手元に一度だけ写し（`geo_voyager/dataset_mirror.py`）、Gateway はその写しから range 読み込みに応える。写しが無い表は Hub から中継する。Hub 経由では range 読み込みのたびに米国の CDN へ新しい接続を張り（1 回約 1 秒）、23 区の読み込みが sandbox で 20 秒、手元から直接で 5 秒だった（2026-10-14）。
- 任意 URL、redirect の追跡、認証 header の転送はしない。

## 結果

- 新しいデータや API を使うには、catalog（`datasets.py`、`services.py`）への登録が要る。モデルが勝手に取りに行くことはできない。
- 仕様の詳細は [reference/sandbox_and_gateway.md](../reference/sandbox_and_gateway.md) と [reference/services.md](../reference/services.md)。
