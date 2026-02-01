# 進捗管理

## 全体ステータス

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | コア・フレームワーク構築 (CLI & Config) | ✅ 完了 |
| Phase 2 | プラグイン機構の実装 (Pluggy & ABC) | ✅ 完了 |
| Phase 3 | データ処理パイプライン実装 (Polars & Returns) | ✅ 完了 |
| Phase 4 | Dry-Run と堅牢化 | ✅ 完了 |

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

## Phase 3: データ処理パイプライン実装 ✅

### 実装済みファイル

| ファイル | 操作 | 状態 | 内容 |
|---------|------|------|------|
| `packages/cryoflow-core/cryoflow_core/pipeline.py` | 新規 | ✅ | パイプラインランナー（108行） - scan + transform chain + output |
| `packages/cryoflow-core/cryoflow_core/cli.py` | 編集 | ✅ | モック → パイプライン実行に切り替え |
| `packages/cryoflow-sample-plugin/cryoflow_sample_plugin/transform.py` | 新規 | ✅ | ColumnMultiplierPlugin（90行） |
| `packages/cryoflow-sample-plugin/cryoflow_sample_plugin/output.py` | 新規 | ✅ | ParquetWriterPlugin（79行） |

### 実装内容の詳細

#### pipeline.py（108行）
- `_detect_format()`: ファイル拡張子から Parquet/IPC 形式を自動判別
- `load_data()`: `@safe` デコレータで例外を `Result` に自動変換、`pl.scan_parquet()` / `pl.scan_ipc()` 対応
- `execute_transform_chain()`: `returns.Result.bind()` でプラグイン連鎖実行
- `execute_output()`: 変換済みデータを出力プラグインに渡す
- `run_pipeline()`: 読込→変換→出力の統合パイプライン

#### サンプルプラグイン実装
- **ColumnMultiplierPlugin**: 指定カラムを係数で乗算（LazyFrame の計算グラフ対応）
  - `dry_run(schema)`: スキーマ検証
  - `execute(df)`: LazyFrame チェーン対応
- **ParquetWriterPlugin**: Parquet ファイルへの出力（`sink_parquet()` でストリーミング書き込み）
  - `dry_run(schema)`: スキーマ検証
  - `execute(df)`: `collect()` / `sink_parquet()` で実行

### テスト結果

| テストモジュール | テスト数 | 状態 |
|----------------|---------|------|
| `test_pipeline.py` | 20テスト | ✅ 全てパス |
| `test_transform.py` | 21テスト | ✅ 全てパス |
| `test_output.py` | 9テスト | ✅ 全てパス |
| `test_e2e.py` | 9テスト | ✅ 全てパス |
| **Phase 3合計** | **59テスト** | **✅ 全てパス** |

### 仕様書との整合性

- ✅ `spec.md` 記載のパイプライン設計と完全一致
- ✅ `returns` による鉄道指向プログラミング実装
- ✅ LazyFrame による計算グラフ構築
- ✅ エラーハンドリング統一

### 実装完了確認

コミット: `d93af83 feat: implement Phase 3 - Data processing pipeline (Polars & Returns)`
- Parquetデータ入力 → 変換プラグイン実行 → 出力プラグイン実行 の一気通貫動作確認完了

---

## Phase 4: Dry-Run と堅牢化 ✅

### 実装済みファイル

| ファイル | 操作 | 状態 | 内容 |
|---------|------|------|------|
| `packages/cryoflow-core/cryoflow_core/pipeline.py` | 編集 | ✅ | 4つのdry-run関数 + ロギング追加 |
| `packages/cryoflow-core/cryoflow_core/cli.py` | 編集 | ✅ | `check` コマンド + `--verbose` フラグ + ロギング設定 |
| `packages/cryoflow-core/tests/test_pipeline.py` | 編集 | ✅ | dry-runのユニットテスト18個 |
| `packages/cryoflow-core/tests/test_e2e.py` | 編集 | ✅ | checkコマンドの統合テスト4個 |
| `docs/spec.md` | 編集 | ✅ | プラグイン実装ガイド + CLI仕様追記 |
| `README.md` | 編集 | ✅ | checkコマンドの使用例追記 |

### 実装内容の詳細

#### pipeline.py（+80行）
- `extract_schema()`: LazyFrame/DataFrameからスキーマを抽出（`@safe`デコレータ使用）
- `execute_dry_run_chain()`: TransformPluginの検証チェーン実行
- `execute_output_dry_run()`: OutputPluginの検証実行
- `run_dry_run_pipeline()`: E2Eのdry-runパイプライン
- `execute_transform_chain()`にログ出力追加

#### cli.py（+80行）
- `setup_logging()`: ロギング基盤構築（INFO/DEBUG切り替え）
- `check`コマンド: 設定検証とスキーマ表示
- `run`コマンドに`--verbose`フラグ追加
- `check`コマンドに`--verbose`フラグ追加

#### ロギング出力例

**通常モード（`cryoflow check`）**:
```
[CHECK] Config loaded: examples/config.toml
[CHECK] Loaded 2 plugin(s) successfully.
[CHECK] Running dry-run validation...
[SUCCESS] Validation completed successfully

Output schema:
  order_id: String
  region: String
  ...
```

**詳細モード（`cryoflow check -v`）**:
```
[CHECK] Config loaded: examples/config.toml
...
INFO: Validating 1 transformation plugin(s)...
INFO:   [1/1] column_multiplier
DEBUG:     Input schema: 12 columns
DEBUG:     Output schema: 12 columns
[SUCCESS] Validation completed successfully
```

### テスト結果

#### ユニットテスト（test_pipeline.py）
- TestExtractSchema: 3テスト ✅
- TestExecuteDryRunChain: 7テスト ✅
- TestExecuteOutputDryRun: 3テスト ✅
- TestRunDryRunPipeline: 4テスト ✅

#### 統合テスト（test_e2e.py）
- TestCheckCommand: 4テスト ✅
  - test_check_command_success
  - test_check_command_missing_config
  - test_check_command_with_verbose
  - test_check_command_transform_validation_fails

**Phase 4合計**: 21テスト追加 ✅

#### 全体テスト結果
| テストモジュール | テスト数 | 状態 |
|----------------|---------|------|
| cryoflow-core | 140テスト | ✅ 全てパス |
| **合計（Phase 1-4）** | **140テスト** | **✅ 全てパス** |

### 実装完了確認

コミット: `667c6de feat: implement Phase 4 - Dry-Run and robustness enhancements`
- dry-run機能の完全実装
- CLIの`check`コマンド追加
- ロギング基盤の構築
- 包括的なテスト追加（18 + 4 = 22テスト）
- ドキュメント更新（プラグイン実装ガイド + CLI仕様）

### 主な特徴

1. **スキーマ検証**: `extract_schema()`で実データロードなしにメタデータのみ抽出
2. **エラーハンドリング**: 既存の`returns`パターンと完全整合
3. **ロギング**: 標準`logging`モジュール + `--verbose`フラグで制御
4. **ユーザビリティ**: 明確なコマンド名（`cryoflow check`）と詳細なエラーメッセージ
5. **拡張性**: 将来のJSON出力、差分表示に対応可能な設計

---

## プロジェクト構造 (現在)

```
cryoflow/
├── pyproject.toml                  # ルートパッケージ (monorepo構成、エントリポイント定義)
├── uv.lock                         # 依存ロック
├── packages/
│   ├── cryoflow-core/              # コアフレームワーク
│   │   ├── pyproject.toml          # 依存定義 (typer, pydantic, xdg-base-dirs, pluggy, returns, polars)
│   │   ├── cryoflow_core/
│   │   │   ├── __init__.py
│   │   │   ├── cli.py              # Typer CLIアプリケーション (80行)
│   │   │   ├── config.py           # Pydanticモデル + 設定ローダー (66行)
│   │   │   ├── plugin.py           # ABC基底クラス (40行)
│   │   │   ├── hookspecs.py        # pluggy Hook仕様 (20行)
│   │   │   ├── loader.py           # プラグイン動的ロード機構 (200行)
│   │   │   └── pipeline.py         # データ処理パイプライン (108行)
│   │   └── tests/                  # テストスイート (119テスト)
│   │       ├── test_config.py
│   │       ├── test_cli.py
│   │       ├── test_plugin.py
│   │       ├── test_hookspecs.py
│   │       ├── test_loader.py
│   │       ├── test_pipeline.py
│   │       ├── test_e2e.py
│   │       └── conftest.py
│   └── cryoflow-sample-plugin/     # サンプルプラグイン
│       ├── pyproject.toml          # 依存定義 (cryoflow-core, polars)
│       ├── cryoflow_sample_plugin/
│       │   ├── __init__.py
│       │   ├── transform.py        # ColumnMultiplierPlugin (90行)
│       │   └── output.py           # ParquetWriterPlugin (79行)
│       └── tests/                  # テストスイート (30テスト)
│           ├── test_transform.py
│           └── test_output.py
├── examples/
│   ├── config.toml                 # サンプル設定ファイル
│   └── data/                       # サンプルデータファイル
│       ├── sample_sales.parquet
│       ├── sample_sales.ipc
│       ├── sensor_readings.parquet
│       ├── output.parquet
│       ├── generate_sample_data.py
│       ├── generate_sensor_data.py
│       └── README.md
├── docs/
│   ├── spec.md                     # 仕様書
│   ├── implements_step_plan.md     # 実装計画
│   └── progress.md                 # 進捗管理 (本ファイル)
├── CLAUDE.md                       # プロジェクト実装ガイド
├── README.md                       # プロジェクト概要
├── flake.nix                       # Nix開発環境定義
└── .python-version                 # Python 3.14指定
```

### テスト実行結果（全体）

| パッケージ | テスト数 | 状態 |
|----------|---------|------|
| cryoflow-core | 140テスト | ✅ 全てパス |
| cryoflow-sample-plugin | 30テスト | ✅ 全てパス |
| **合計** | **170テスト** | **✅ 全てパス (100% 合格)** |

---

## 実装完了サマリー

### 全体実装状況

✅ **すべてのフェーズ完了** (Phase 1 - 4)

- **総コミット数**: 4
- **総テスト数**: 170 (全て合格)
- **コア実装行数**: 約800行
- **テスト実装行数**: 約900行

### 主な成果

1. **プラグイン駆動型アーキテクチャ**: pluggy + ABC による拡張可能な設計
2. **鉄道指向プログラミング**: returns ライブラリによる統一的なエラーハンドリング
3. **遅延評価パイプライン**: Polars LazyFrame を活用した効率的なデータ処理
4. **スキーマ検証**: dry-run機能により本実行前の事前検査が可能
5. **包括的なロギング**: `--verbose`フラグでの詳細度制御

### ドキュメント整備

- ✅ `spec.md`: 完全な仕様書（プラグイン実装ガイド含む）
- ✅ `implements_step_plan.md`: 詳細な実装計画
- ✅ `progress.md`: 進捗管理（本ファイル）
- ✅ `README.md`: プロジェクト概要 + 使用例

### キー機能

**CLI コマンド**:
- `cryoflow run [-c CONFIG] [-v]`: パイプライン実行
- `cryoflow check [-c CONFIG] [-v]`: 設定検証

**プラグイン機構**:
- TransformPlugin: データ変換処理
- OutputPlugin: 結果出力処理
- dry_run メソッド: スキーマ検証

**エラーハンドリング**:
- Result[T, Exception] による型安全なエラー処理
- CLI での詳細なエラーメッセージ出力
- 統一的な exit code 返却
