# 0011 Exploration Graph: 次の試行に渡すのは、機械的に確かめた失敗だけ

2026-10-14。[0003](0003-three-graphs-and-skill-library.md) の Exploration Graph（探索の過程の記録）を、ベンチの付属品から本体に移すときの決定。

## 背景

- 同じ Goal を前に試した記録を Planner に渡す実験をした（2026-10-13、`bench/exploration_memory.py`）。記録は生のまま渡した。各手の Intent と、その終わり方（成功と Observation、実行の失敗、Critic の棄却とその理由と Observation）、計画の失敗、最終判定の失敗。
- 記録を渡した 4 件は、どれも答えが出なかった。悪くした経路は、どれもモデルの判断だった。
  - Critic の誤った棄却の理由を引き継いだ。「港区と目黒区の組が無い」（2 区は接していない）。次の Planner は、これを Intent に「必須」と書き込んだ。
  - 確かめていない途中の値を、答えの材料として使った。
- Critic の判断は、外れることがある。保存した 35 件の判定のうち 7 件が誤りだった（[2026-10-14_critic_stage4.md](../reports/2026-10-14_critic_stage4.md)）。誤った判断を次の試行に渡すと、1 回の誤りが前提になり、次の試行で直す機会がなくなる。
- 一方で、モデルを使わずに確かめた失敗は、何度実行しても同じになる。例えば、実行のエラー、契約違反、出力の上限超え、同じ行の重複。

## 決定

1. `geo_voyager/exploration_graph.py` を `world_graph.py` の隣に置き、試した Goal ごとの記録を持たせる。`bench/exploration_memory.py` は削除する。
2. 出来事の型は、`goal_history.py` の 3 つ（`HistoryEntry`、`PlannerFailure`、`FinalCriticFailure`）だけにする。Exploration Graph は独自の出来事の型を持たず、Goal の実行が終わったときの出来事の列から、決定論的なフィルタ（`checked_failures`）で `CheckedFailure` を取り出して保存する。trace の dict を読み直す経路はなくす。
3. `CheckedFailure` が持つのは、次の欄だけにする。
   - 手の番号、Intent の文、Intent が宣言した資源
   - 失敗の種類と、その 1 行。失敗の種類は次の 6 つ。
     - `execution_error`: 実行のエラー。最後の例外の行
     - `timeout`: 実行の時間切れ
     - `code_contract`: 生成したコードが、実行の前の契約検査で拒まれた
     - `output_too_long`: 出力の上限超え
     - `duplicate_rows`: 同じ行の重複
     - `planner_contract`: Planner の応答が、決定論的な検査で拒まれた
   - Critic の判定と理由、Observation、実行が出した stdout、Planner の応答そのものは、欄が無いので入りようがない。
4. 次の試行の Planner に渡す文面は、保存した `CheckedFailure` だけから、決定論的に作る（`ExplorationGraph.memory`）。Critic が棄却した手、最終判定の失敗、止まり方（`final_critic_failed` は Critic の判断から来る）は渡さない。
5. 単体テストで、Critic の理由、Observation、stdout、Planner の応答、最終判定の理由に入れた目印の文字列が、保存にも文面にも出てこないことを保証する。

## 拡張の余地（まだ実装しない）

- 方針 A では、「実行のエラーでも契約違反でもないが、結果が 0 や空だったので、Critic が正しく棄却した手」は記憶に残らない。同じ 0 件の手を次の試行でも繰り返すようなら、Critic の判断文ではなく、出力そのものから機械的に読める事実（「この条件で実行したら結果は 0 だった」「0 行だった」）を、`CheckedFailure` の種類の 1 つとして足す。値を読むのはフィルタで、モデルではない。
- 足すときは、`checked_failures` に取り出し方を 1 つ足し、種類を 1 つ増やすだけにする。文面を作る側と、遮断のテストは変えない。

## 残っている経路

- Curriculum は、試した Goal の一覧で、未達の Goal に Critic の理由の先頭 150 字を添えて読んでいる（`curriculum.py`）。次の Goal を選ぶための材料で、Planner への記憶とは別の経路である。同じ問題を持ちうるので、別に扱う。

## 結果

- 前の試行から引き継ぐものは、何度実行しても同じになる事実だけになる。前の試行の判断の誤りが、次の試行の前提にならない。
- 引き継ぐ量は減る。前の試行が、Critic の棄却だけで終わった Goal には、渡すものが無い。
