# Geo-Voyager: 未知の地理空間的洞察を発見する自律型AIエージェント

[English](./README.md) | [日本語](./README.ja.md)

Geo-Voyager は、生成 AI によって反復的に疑問を生成し、その疑問に対する仮説を立案・検証することで、現実世界の地理空間的洞察（Geospatial Insights）を最大化する、自律的 AI エージェントシステムです。

## 概要

Geo-Voyagerは、LangChainとOllamaを使用して以下のような自律的なサイクルを実行します：
- 現実世界の地理空間パターンに関する興味深い疑問の生成
- 検証可能な仮説の立案
- OpenStreetMapなどのソースからのデータ収集と分析
- 検証済みの洞察と再利用可能な分析スキルのライブラリ構築

## 主要な機能

- **疑問生成**: 現実世界の地理空間パターンに関する興味深い疑問を生成します
- **仮説立案・検証**: 生成された疑問に対する仮説を立案し、データ収集と分析を通じて検証します
- **データ収集**: OpenStreetMap Overpass API などのデータソースから、仮説検証に必要なデータを収集します
- **スキルライブラリ**: 仮説検証に成功した API クエリやコードをスキルとして蓄積し、再利用します
- **仮説・洞察ライブラリ**: 生成された仮説と検証結果を記録し、洞察を蓄積します

## 前提条件

- Node.js (v18以降)
- npmまたはpnpm
- Ollama（qwen2.5:14bモデルがインストールされていること）
- SQLite

## インストール

1. リポジトリのクローン:
```bash
gh repo clone yuiseki/Geo-Voyager
cd Geo-Voyager
```

2. 依存関係のインストール:
```bash
npm install
# または pnpmを使用する場合
pnpm install
```

3. データベースのセットアップ:
```bash
# .envファイルにSQLiteデータベースのURLを設定
echo "DATABASE_URL=\"file:./prisma/dev.db\"" > .env

# データベースの初期化
make clean
```

## 使用方法

システムの実行:
```bash
make
```

## システムフロー

Geo-Voyagerは、以下のステップを反復的に実行することで、地理空間的洞察を発見します：

1. **疑問生成**: 生成AIを用いて、現実世界の地理空間パターンに関する疑問を生成します
2. **仮説立案**: 生成された疑問に対し、検証可能な仮説を立案します
3. **仮説検証**: データ収集と分析を行い、仮説の真偽を検証します
4. **洞察記録**: 検証に成功した仮説を洞察として記録します
5. **スキル改善**: 検証に用いたデータ収集や分析のプロセスをスキルとして蓄積し、改善します

詳細なシステムフローは、[フローチャート](./docs/flowchart-overview.md)をご覧ください。

## ドキュメント

- [要件とアーキテクチャ](./docs/requirements.md)
- [スキル開発ガイド](./src/lib/skills/README.md)
- [課題分析](./docs/analysis/issues-analysis.md)

## 開発

### プロジェクト構造

- `src/` - メインソースコード
  - `lib/skills/` - 再利用可能な分析スキル
- `prisma/` - データベーススキーマとマイグレーション
- `docs/` - プロジェクトドキュメント

### データベーススキーマ

プロジェクトはPrismaとSQLiteを使用して以下を管理します：
- 疑問とその状態
- 仮説と検証結果
- 仮説検証用のタスク
- 再利用可能なスキルライブラリ

詳細は[schema.prisma](./prisma/schema.prisma)をご覧ください。

### コントリビューション

1. 変更用の新しいブランチを作成
2. [スキルREADME](./src/lib/skills/README.md)のコーディング規約に従う
3. すべてのスキルが独立して自己完結していることを確認
4. 新機能には適切なドキュメントを追加
5. 変更内容を明確に説明したプルリクエストを提出

## ライセンス

WTFPL

## 技術詳細

- TypeScriptとNode.jsで構築
- LangChainとOllama（qwen2.5:14bモデル）を使用したAI操作
- PrismaORMとSQLiteによるデータ管理
- OpenStreetMap Overpass APIによる地理空間データ
- その他のデータソース：World Bank、UN OCHA HDX
