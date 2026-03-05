# cryoflow への貢献ガイド

cryoflow への貢献に興味を持っていただきありがとうございます。
このドキュメントでは、開発環境のセットアップからプルリクエストの送り方まで、貢献に必要な情報をまとめています。

## 目次

- [前提条件](#前提条件)
- [開発環境のセットアップ](#開発環境のセットアップ)
- [プロジェクト構造](#プロジェクト構造)
- [テストの実行](#テストの実行)
- [コードスタイル](#コードスタイル)
- [コミット規約](#コミット規約)
- [プルリクエストの送り方](#プルリクエストの送り方)
- [Issue の報告](#issue-の報告)

---

## 前提条件

開発に参加するためには以下のツールが必要です。

- [Nix](https://nixos.org/download/) (Flakes 有効化済み)
- [direnv](https://direnv.net/) (推奨) または Nix CLI

Nix を使わない場合は以下が必要です。

- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/)

---

## 開発環境のセットアップ

### direnv を使用する場合（推奨）

```bash
# リポジトリをクローン
git clone https://github.com/yasunori0418/cryoflow
cd cryoflow

# サンプル設定をコピー
cp example.envrc .envrc

# direnv にロードを許可
direnv allow
```

ディレクトリに入ると、`dev/flake.nix` で定義された開発環境が自動的にアクティベートされます。
以下のツールが含まれた開発環境がセットアップされます。

- `uv` - Python パッケージ管理
- `ruff` - フォーマッター / リンター
- `pyright` - 静的型チェッカー
- `actionlint` - GitHub Actions ワークフローのリンター

### Nix CLI を使用する場合

```bash
# 開発環境に入る
nix develop ./dev
```

### uv を使用する場合（Nix なし）

```bash
# 依存関係のインストール
uv sync

# 仮想環境をアクティベート
source .venv/bin/activate
```

---

## プロジェクト構造

```
cryoflow/
├── cryoflow/                      # メタパッケージ（エントリーポイント）
├── packages/
│   ├── cryoflow-core/             # コアフレームワーク
│   │   ├── cryoflow_core/         # ソースコード
│   │   └── tests/                 # テストコード
│   └── cryoflow-plugin-collections/  # 組み込みプラグイン集
│       ├── cryoflow_plugin_collections/
│       └── tests/
├── dev/
│   └── flake.nix                  # 開発用 Nix Flake 設定
├── docs/                          # ドキュメント
│   ├── spec_ja.md / spec.md       # 仕様書
│   ├── plugin_development_ja.md / plugin_development.md
│   └── cicd_ja.md / cicd.md
├── examples/                      # サンプルデータと設定
├── flake.nix                      # Nix Flake (ルート)
└── pyproject.toml                 # uv ワークスペース設定
```

`packages/` 配下は uv ワークスペースとして管理されており、それぞれ独立した `pyproject.toml` を持ちます。

---

## テストの実行

### Nix 開発環境での実行（推奨）

```bash
# 全テストを実行
pytest

# 特定のパッケージのテストのみ実行
pytest packages/cryoflow-core/tests/
pytest packages/cryoflow-plugin-collections/tests/

# 詳細出力
pytest -v
```

### CI と同じ環境で実行

```bash
nix develop './dev#ci' -c pytest
```

テストパスは `pyproject.toml` の `[tool.pytest.ini_options]` に定義されています。

---

## コードスタイル

### フォーマット / リント（ruff）

```bash
# フォーマットの確認
ruff format --check .

# フォーマットの適用
ruff format .

# リントの確認
ruff check .

# リントの自動修正
ruff check --fix .
```

主な設定（`pyproject.toml` より）：

- ターゲットバージョン: Python 3.14
- 行長: 120 文字
- クォートスタイル: シングルクォート

### 型チェック（pyright）

```bash
pyright
```

**型アノテーションは必須です。**
テストコード・ドキュメント・プロダクトコードのすべてに型アノテーションを記述してください。
`Any` 型はテストの都合などやむを得ない場合を除いて使用しないでください。

### コーディング規約

- エラーハンドリングには `returns` ライブラリの `Result` 型を使用する
- 予期せぬ例外は `@safe` デコレータで `Failure` に変換する
- ABC による基底クラスのインターフェースに従う
- プラグインには必ず `dry_run` メソッドを実装する

---

## コミット規約

コミットメッセージは **英語** で記述してください。

[Conventional Commits](https://www.conventionalcommits.org/) の形式に従ってください。

```
<type>(<scope>): <subject>

<body>  # 任意

<footer>  # 任意
```

### type の種類

| type | 用途 |
| --- | --- |
| `feat` | 新機能の追加 |
| `fix` | バグ修正 |
| `docs` | ドキュメントの変更のみ |
| `style` | 機能に影響しないコードスタイルの変更 |
| `refactor` | バグ修正でも機能追加でもないコードの変更 |
| `test` | テストの追加・修正 |
| `ci` | CI 設定の変更 |
| `chore` | ビルドプロセスや補助ツールの変更 |

### 例

```
feat(plugin): add CSV input plugin

Add CsvInputPlugin that reads CSV files into LazyFrame.
Supports configurable delimiter and header options.
```

---

## プルリクエストの送り方

1. リポジトリをフォークする
2. 機能ブランチを作成する
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. 変更を加えてテストを実行する
4. コードスタイルを確認する
5. コミットしてフォークにプッシュする
6. `main` ブランチへのプルリクエストを作成する

プルリクエストでは `.github/pull_request_template.md` のテンプレートに従って記述してください。

### PR 作成前のチェックリスト

- [ ] ローカルでテストが全て通ることを確認した
- [ ] `ruff format` と `ruff check` でコードスタイルを確認した
- [ ] `pyright` で型エラーがないことを確認した
- [ ] 新機能にはテストを追加した
- [ ] 関連するドキュメントを更新した（日本語版・英語版両方）

### ドキュメントの更新

ドキュメントは日本語版（`*_ja.md`）が主軸で、英語版（`*.md`）はそれに追従する形で更新してください。

---

## Issue の報告

バグ報告、機能要望、質問などは [GitHub Issues](https://github.com/yasunori0418/cryoflow/issues) から行ってください。

バグ報告の際は以下の情報を含めると対応がスムーズです。

- 再現手順
- 期待する動作
- 実際の動作
- 環境情報（OS、Python バージョン、cryoflow バージョン）
- 関連するエラーメッセージやスタックトレース
