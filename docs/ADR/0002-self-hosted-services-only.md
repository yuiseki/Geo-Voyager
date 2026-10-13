# 0002 地理サービスは自前のものだけを使う

- 日付: 2026-10-08
- 状態: 採用

## 背景

探索のループは、同じサービスに長時間、大量に問い合わせる。公開の OpenStreetMap のサーバーにこの負荷をかけてはいけない。

## 決定

- 登録するのは自前のサービスだけにする（`geo_voyager/services.py`）。
  - overpass.yuiseki.net、nominatim.yuiseki.net、valhalla.yuiseki.net、taginfo.yuiseki.net。
  - YuisekinGeoSPARQL（固定したグラフ。答えを確かめる oracle としても使う）。
- 公開の OSM サーバーは、実行でもテストでも確認でも呼ばない。
- User-Agent は `Geo-Voyager/0.1.0 (+https://github.com/yuiseki/Geo-Voyager)` に固定する。User-Agent が無いと自前のサービスも 403 を返す。
- Dataset は Hugging Face の固定リビジョンから読む。

## 結果

- 自前の Overpass のデータは 2025-09-14 で止まっている。件数の答えはこの時点のもの。
- サービスの説明（`services.py`）には、実際に問い合わせて確かめたことだけを書き、integration の契約テストで保つ。
