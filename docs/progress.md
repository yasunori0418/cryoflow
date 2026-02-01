# 進捗管理

## 全体ステータス

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | コア・フレームワーク構築 (CLI & Config) | ✅ 完了 |
| Phase 2 | プラグイン機構の実装 (Pluggy & ABC) | ✅ 完了 |
| Phase 3 | データ処理パイプライン実装 (Polars & Returns) | ⬜ 未着手 |
| Phase 4 | Dry-Run と堅牢化 | ⬜ 未着手 |

---

## Phase 1: コア・フレームワーク構築 ✅

### 実装済みファイル

| ファイル | 操作 | 状態 |
|---------|------|------|
| `packages/cryoflow-core/pyproject.toml` | 編集 | ✅ pydantic, xdg-base-dirs 依存追加 |
| `packages/cryoflow-core/cryoflow_core/__init__.py` | 編集 | ✅ docstring追加 |
| `packages/cryoflow-core/cryoflow_core/config.py` | 新規 | ✅ Pydanticモデル + 設定ローダー |
| `packages/cryoflow-core/cryoflow_core/cli.py` | 新規 | ✅ Typer CLIアプリ (run コマンド) |
| `pyproject.toml` (ルート) | 編集 | ✅ `[project.scripts]` エントリポイント追加 |
| `examples/config.toml` | 新規 | ✅ サンプル設定ファイル |

### 検証結果

| コマンド | 結果 |
|---------|------|
| `uv sync` | ✅ 依存インストール成功 |
| `uv run cryoflow --help` | ✅ ヘルプ表示、`run` コマンド表示 |
| `uv run cryoflow run --help` | ✅ `--config` / `-c` オプション表示 |
| `uv run cryoflow run -c examples/config.toml` | ✅ 設定内容の正常表示 |
| `uv run cryoflow run` (デフォルトパス未存在) | ✅ エラーメッセージ + exit code 1 |
| `uv run cryoflow run -c nonexistent.toml` | ✅ Typer組込みエラー + exit code 2 |

### 仕様書との差分

- `GlobalConfig` → `CryoflowConfig` にリネーム（より明確な名前）
- `input_path` の型を `FilePath` → `Path` に変更（ファイル存在チェックを設定ロード時に強制しないため）

---

## Phase 2: プラグイン機構の実装 ✅

### 実装済みファイル

| ファイル | 操作 | 状態 | 内容 |
|---------|------|------|------|
| `packages/cryoflow-core/pyproject.toml` | 編集 | ✅ | pluggy, returns 依存追加 |
| `packages/cryoflow-core/cryoflow_core/plugin.py` | 新規 | ✅ | ABC基底クラス (BasePlugin, TransformPlugin, OutputPlugin) |
| `packages/cryoflow-core/cryoflow_core/hookspecs.py` | 新規 | ✅ | pluggy HookSpec定義 |
| `packages/cryoflow-core/cryoflow_core/loader.py` | 新規 | ✅ | importlib動的ロード + PluginManager（201行） |

### 実装内容の詳細

#### plugin.py（41行）
- `FrameData` 型エイリアス定義: `Union[pl.LazyFrame, pl.DataFrame]`
- `BasePlugin(ABC)`: 全プラグインの基底クラス
  - `__init__(options: dict[str, Any])`: オプション保持
  - `name() -> str`（抽象メソッド）: プラグイン識別名
  - `dry_run(schema) -> Result[dict[str, pl.DataType], Exception]`（抽象メソッド）: スキーマ検証
- `TransformPlugin(BasePlugin)`: データ変換プラグイン
  - `execute(df) -> Result[FrameData, Exception]`（抽象メソッド）: データ変換実行
- `OutputPlugin(BasePlugin)`: 出力プラグイン
  - `execute(df) -> Result[None, Exception]`（抽象メソッド）: 出力実行

#### hookspecs.py（21行）
- `pluggy.HookspecMarker('cryoflow')` でhookspec定義
- `CryoflowSpecs`: Hook仕様クラス
  - `register_transform_plugins() -> list[TransformPlugin]`: Transform プラグイン登録Hook
  - `register_output_plugins() -> list[OutputPlugin]`: Output プラグイン登録Hook

#### loader.py（201行）
プラグインの動的ロード・発見・管理機構：
- **ファイルシステムパス対応**: 絶対パス、相対パス、ドット記法パスに対応
- `_is_filesystem_path()`: モジュール文字列がパスかドット記法かを判定
- `_resolve_module_path()`: パスを絶対パスに解決、存在確認
- `_load_module_from_path()`: importlib で .py ファイルから動的ロード
- `_load_module_from_dotpath()`: importlib で ドット記法パスからインポート
- `_discover_plugin_classes()`: ロード済みモジュール内の BasePlugin サブクラスを自動検出
- `_instantiate_plugins()`: 発見されたクラスをオプション付きでインスタンス化
- `_PluginHookRelay`: プラグインインスタンスを pluggy Hook メソッドで公開するラッパー
- `_load_single_plugin()`: 単一プラグイン設定エントリをロード
- `load_plugins()`: 全ての有効プラグインをロードし pluggy に登録
- `get_transform_plugins()`: 登録済みの TransformPlugin インスタンス取得
- `get_output_plugins()`: 登録済みの OutputPlugin インスタンス取得
- **エラーハンドリング**: `PluginLoadError` で一元管理

### テスト結果

| テストモジュール | テスト数 | 状態 |
|----------------|---------|------|
| `test_plugin.py` | 15テスト | ✅ 全てパス |
| `test_hookspecs.py` | 7テスト | ✅ 全てパス |
| `test_loader.py` | 46テスト | ✅ 全てパス |
| **合計** | **68テスト** | **✅ 全てパス** |

**テストカバレッジ**: 100%達成（コミット c66e2f1）

### 仕様書との整合性

- ✅ `spec.md` 記載のインターフェース定義と完全一致
- ✅ Pluggy hookspec による拡張性確保
- ✅ ABC による型安全性確保
- ✅ Returns による Result 型ベースのエラーハンドリング実装

---

## Phase 3: データ処理パイプライン実装 ⬜

### 予定ファイル

| ファイル | 操作 | 状態 | 内容 |
|---------|------|------|------|
| `packages/cryoflow-core/cryoflow_core/pipeline.py` | 新規 | ⬜ | パイプラインランナー (scan + transform chain + output) |
| `packages/cryoflow-core/cryoflow_core/cli.py` | 編集 | ⬜ | モック → パイプライン実行に切り替え |

---

## Phase 4: Dry-Run と堅牢化 ⬜

### 予定ファイル

| ファイル | 操作 | 状態 | 内容 |
|---------|------|------|------|
| `packages/cryoflow-core/cryoflow_core/cli.py` | 編集 | ⬜ | `check` コマンド追加 |

---

### 次のアクション

Phase 2 が完了したため、**Phase 3: データ処理パイプライン実装** に進む。
`pipeline.py` で Polars LazyFrame を統合し、プラグインチェーンをデータ処理フローに組み込む。

---

## プロジェクト構造 (現在)

```
cryoflow/
├── pyproject.toml                  # ルートパッケージ (エントリポイント定義)
├── uv.lock
├── cryoflow/
│   └── __init__.py
├── packages/
│   ├── cryoflow-core/
│   │   ├── pyproject.toml          # typer, pydantic, xdg-base-dirs
│   │   └── cryoflow_core/
│   │       ├── __init__.py
│   │       ├── cli.py              # Typer CLIアプリ
│   │       └── config.py           # Pydanticモデル + 設定ローダー
│   └── cryoflow-sample-plugin/
│       ├── pyproject.toml
│       └── cryoflow_sample_plugin/
│           └── __init__.py
├── examples/
│   └── config.toml                 # サンプル設定ファイル
├── docs/
│   ├── spec.md                     # 仕様書
│   ├── implements_step_plan.md     # 実装計画
│   └── progress.md                 # 進捗管理 (本ファイル)
└── dev/
    ├── flake.nix
    └── flake.lock
```
