# CI/CD ドキュメント

## 概要

cryoflow プロジェクトでは GitHub Actions を使用してCI/CDパイプラインを構成しています。
依存関係の更新は Renovate Bot によって自動管理されます。

全てのワークフローは Nix を使用してビルド環境を統一しており、共通の composite action (`setup-nix`) を通じて Nix のインストールと Cachix の設定を行います。

---

## アーキテクチャ全体図

```
[feature branch へのプッシュ / PR]
        |
        v
    [Test] ← packages/**/*.py または uv.lock の変更時に実行

[main ブランチへのプッシュ]
        |
        v
    [Release] ← packages/** の変更時に自動実行
        |
        v (Release 成功後に自動トリガー)
    [Publish to PyPI]

[タグのプッシュ (*.*.*)]
        |
        v
    [Cachix Push] ← マルチプラットフォームの Nix パッケージをビルド・プッシュ

[手動実行のみ]
    [Bump Version] ← バージョンを一括更新し、コミット・プッシュ
```

---

## ワークフロー詳細

### 1. Test (`test.yml`)

| 項目 | 内容 |
|------|------|
| トリガー | `feature` ブランチへの push、PR、手動実行 |
| 対象パス | `packages/**/*.py`、`uv.lock` |
| 実行環境 | `ubuntu-latest` |

#### 概要

`main` ブランチ以外へのプッシュやプルリクエスト時に、Pythonソースコードまたはロックファイルが変更された場合にテストを実行します。

#### 実行内容

1. リポジトリをチェックアウト
2. Nix 環境をセットアップ (`setup-nix` composite action)
3. CI専用の Nix 開発環境 (`dev#ci`) で pytest を実行

#### 環境変数

| 変数名 | 値 | 目的 |
|--------|-----|------|
| `TERM` | `"dumb"` | pytest 実行時の端末エミュレーション問題を回避 |

---

### 2. Release (`release.yml`)

| 項目 | 内容 |
|------|------|
| トリガー | `main` ブランチへの push、手動実行 |
| 対象パス | `packages/**` |
| 実行環境 | `ubuntu-latest` |
| 必要権限 | `contents: write` |

#### 概要

`main` ブランチの `packages/` 以下に変更がマージされた際、現在のバージョンを取得して GitHub Release を自動作成します。

#### 実行内容

1. リポジトリをチェックアウト（全履歴: `fetch-depth: 0`）
2. Nix 環境をセットアップ
3. `uv version` でプロジェクトのバージョンを取得
4. `softprops/action-gh-release` で GitHub Release を作成（リリースノートは自動生成）

#### バージョン取得の仕組み

```bash
VERSION=$(nix shell 'nixpkgs#uv' -c uv version | awk '{print $2}')
```

ルートの `pyproject.toml` に記載されたバージョンをタグ名・リリース名として使用します。

---

### 3. Publish to PyPI (`publish.yml`)

| 項目 | 内容 |
|------|------|
| トリガー | Release ワークフロー完了後、手動実行 |
| 実行環境 | `ubuntu-latest` |
| 必要権限 | `contents: read` |

#### 概要

Release ワークフローが成功した後に自動でトリガーされ、全パッケージを PyPI へ公開します。
手動実行時はタグ名を指定することで特定バージョンを公開できます。

#### トリガー条件

- `workflow_run` 経由: Release ワークフローが `success` で完了した場合のみ実行
- `workflow_dispatch` 経由: `tag_name` 入力パラメータが必須

#### 実行内容

1. リポジトリをチェックアウト
   - `workflow_run` 時: Release ワークフローの HEAD コミットを使用
   - `workflow_dispatch` 時: 現在の SHA を使用
2. Nix 環境をセットアップ
3. 全パッケージをビルド: `uv build --all-packages`
4. PyPI へ公開: `uv publish`

#### 必要なシークレット

| シークレット名 | 用途 |
|--------------|------|
| `PYPI_TOKEN` | PyPI への認証トークン |

---

### 4. Bump Version (`bump-version.yml`)

| 項目 | 内容 |
|------|------|
| トリガー | 手動実行のみ (`workflow_dispatch`) |
| 実行可能ブランチ | `main` 以外のブランチ |
| 実行環境 | `ubuntu-latest` |
| 必要権限 | `contents: write` |

#### 概要

全パッケージのバージョンを一括で更新し、変更をコミット・プッシュするワークフローです。
リリース前に `feature` ブランチや `release` ブランチで実行することを想定しています。

#### 入力パラメータ

| パラメータ | 説明 | 必須 | 例 |
|-----------|------|------|-----|
| `version` | 新しいバージョン番号 | 必須 | `1.0.0` |

#### 実行内容

1. リポジトリをチェックアウト
2. Nix 環境をセットアップ
3. 以下の全パッケージのバージョンを更新:
   - ルートパッケージ (`cryoflow`)
   - `cryoflow-core`
   - `cryoflow-plugin-collections`
4. 変更をコミット・プッシュ
   - コミット者: `github-actions[bot]`
   - コミットメッセージ: `chore: bump version to {version}`

#### 更新されるファイル

- `pyproject.toml`（ルート）
- `packages/cryoflow-core/pyproject.toml`
- `packages/cryoflow-plugin-collections/pyproject.toml`

---

### 5. Cachix Push (`cachix-push.yml`)

| 項目 | 内容 |
|------|------|
| トリガー | バージョンタグ (`*.*.*`) のプッシュ、手動実行 |
| 実行環境 | マトリックス（複数プラットフォーム） |

#### 概要

バージョンタグがプッシュされた際に、複数のプラットフォーム向けに Nix パッケージをビルドし、Cachix へプッシュします。

#### ビルドマトリックス

| OS | システム |
|----|---------|
| `ubuntu-latest` | `x86_64-linux` |
| `ubuntu-24.04-arm` | `aarch64-linux` |
| `macos-latest` | `aarch64-darwin` |

#### 実行内容

各プラットフォームで以下を実行:

1. リポジトリをチェックアウト
2. Nix 環境をセットアップ（Cachixへの書き込み権限付き）
3. Nix パッケージをビルド:
   - `nix build .#default` - 本番パッケージ
   - `nix build .#test` - テスト環境パッケージ

ビルドされた成果物は Cachix の `yasunori0418` キャッシュへ自動的にプッシュされます。

---

## 共通インフラ

### Setup Nix Action (`.github/actions/setup-nix`)

全ワークフローが使用する composite action です。

#### 実行内容

1. `cachix/install-nix-action` で Nix をインストール
2. `cachix/cachix-action` で Cachix の `yasunori0418` キャッシュを設定

#### 入力パラメータ

| パラメータ | 説明 | 必須 |
|-----------|------|------|
| `cachix-auth-token` | Cachix 認証トークン | 任意 |

#### 必要なシークレット

| シークレット名 | 用途 |
|--------------|------|
| `CACHIX_AUTH_TOKEN` | Cachix への認証・書き込みトークン |

---

## 依存関係の自動更新 (Renovate)

Renovate Bot によって以下の依存関係が自動更新されます。

### 管理対象

| マネージャー | 対象 |
|------------|------|
| `pep621` | Python ライブラリ (`pyproject.toml`) |
| `nix` | Nix flake 入力 (`flake.nix`、`dev/flake.nix`) |
| `github-actions` | GitHub Actions のバージョン |

### 更新ルール

| ルール | 内容 |
|-------|------|
| Python ライブラリ | ライブラリごとに個別 PR を作成 |
| ルート `flake.nix` の入力 | `nix flake inputs (root)` としてグループ化 |
| `dev/flake.nix` の入力 | `nix flake inputs (dev)` としてグループ化 |
| ロックファイルメンテナンス | 毎週月曜日 午前5時前に実行 |

---

## リリースフロー

通常のリリース手順は以下の通りです。

```
1. feature ブランチで開発・テスト（Test ワークフロー）
2. Bump Version ワークフロー（手動）でバージョンを更新
3. main ブランチへ PR をマージ
4. Release ワークフローが自動実行 → GitHub Release 作成
5. Publish ワークフローが自動実行 → PyPI へ公開
6. Cachix Push ワークフローがタグに反応 → Nix パッケージをビルド・キャッシュ
```
