# 実装計画

プロジェクトを4つのフェーズに分割し、段階的に実装します。

## Phase 1: コア・フレームワーク構築 (CLI & Config) ✅ 完了

**目標**: 設定ファイルを読み込み、Typerでコマンドが起動することを確認する。

### 1-1. プロジェクトセットアップ

- uv workspace による monorepo 構成（`cryoflow-core`, `cryoflow-plugin-collections`）
- Python 3.14 ターゲット
- Nix flake による開発環境

### 1-2. Config実装 (`cryoflow_core/config.py`)

- `PluginConfig`: name, module, enabled(=True), options(=dict) の Pydantic モデル
- `CryoflowConfig`: input_path(Path), output_target(str), plugins(list[PluginConfig])
- `ConfigLoadError`: ファイル未検出 / TOMLパースエラー / バリデーションエラーをラップする例外
- `get_default_config_path()`: `xdg_config_home() / "cryoflow" / "config.toml"` を返却
- `load_config(config_path)`: TOML読み込み → Pydantic検証 → `CryoflowConfig` 返却
- Python 3.14 stdlib `tomllib` を使用（外部TOML依存不要）

### 1-3. Typer実装 (`cryoflow_core/cli.py`)

- `app = typer.Typer(no_args_is_help=True)` + `@app.callback()` でサブコマンド構造を確立
- `cryoflow run` コマンド: `-c / --config` オプション（`exists=True, dir_okay=False, resolve_path=True`）
- 現時点ではモック実装（読み込んだ設定内容を表示するのみ）
- `ConfigLoadError` → stderr出力 + exit code 1

### 1-4. エントリポイント

- ルート `pyproject.toml` に `[project.scripts] cryoflow = "cryoflow_core.cli:app"` を登録

### 1-5. サンプル設定

- `examples/config.toml` にサンプル設定ファイルを作成

### エラーハンドリング設計

| 障害 | 検出箇所 | ユーザー表示 |
|------|----------|------------|
| ファイル未検出 (XDGデフォルト) | `load_config()` → `ConfigLoadError` | `Config file not found: ~/.config/cryoflow/config.toml` |
| ファイル未検出 (`--config`指定) | Typer `exists=True` | Typer組込みエラーメッセージ |
| TOML構文エラー | `load_config()` → `ConfigLoadError` | `Failed to parse TOML config: ...` |
| Pydanticバリデーション | `load_config()` → `ConfigLoadError` | `Config validation failed: ...` |

---

## Phase 2: プラグイン機構の実装 (Pluggy & ABC) ✅ 完了

**目標**: 外部ファイルに定義されたクラスをロードし、メソッドを呼び出せるようにする。

### 2-1. ABC基底クラス実装 (`cryoflow_core/plugin.py`)

- 型エイリアス: `FrameData = Union[pl.LazyFrame, pl.DataFrame]`
- `BasePlugin(ABC)`: `__init__(options)`, `name()`, `dry_run(schema)` を定義
- `TransformPlugin(BasePlugin)`: `execute(df) -> Result[FrameData, Exception]`
- `OutputPlugin(BasePlugin)`: `execute(df) -> Result[None, Exception]`

### 2-2. HookSpec定義 (`cryoflow_core/hookspecs.py`)

- `pluggy.HookspecMarker("cryoflow")` で hookspec を定義
- `register_transform_plugins() -> list[TransformPlugin]`
- `register_output_plugins() -> list[OutputPlugin]`

### 2-3. Plugin Loader (`cryoflow_core/loader.py`)

- 設定ファイルの `module` パス文字列から `importlib` で動的インポート
- クラスをインスタンス化し `PluginManager` に登録
- ロード失敗時のエラーハンドリング

### 2-4. テスト用プラグイン作成

- `cryoflow-plugin-collections` に Identity プラグイン（何もしない変換）を実装
- プラグインのロード・登録・実行のテスト

### 追加依存

- `cryoflow-core`: `pluggy`, `returns`
- `cryoflow-plugin-collections`: `cryoflow-core`, `polars`

---

## Phase 3: データ処理パイプライン実装 (Polars & Returns) ✅ 完了

**目標**: 実際にParquetを読み込み、処理して保存できるようにする。

### 3-1. LazyFrame統合 (`cryoflow_core/pipeline.py`)

- `pl.scan_parquet` / `pl.scan_ipc` によるデータ読み込み
- 入力パスの拡張子に基づく自動判別

### 3-2. Pipeline Runner

- プラグインリストを `returns` の `flow` / `bind` で連鎖
- `TransformPlugin.execute` を順次実行し、計算グラフ（LazyFrame）を構築
- `Failure` が返れば即座に処理を中断

### 3-3. Output実装

- `OutputPlugin.execute` で結果を評価（`collect()` / `sink_parquet()` 等）
- `cli.py` の `run` コマンドをモックからパイプライン実行に切り替え

### 3-4. 結合テスト

- サンプルParquetファイルを用いた入力→変換→出力の一気通貫テスト

---

## Phase 4: Dry-Run と堅牢化

**目標**: 実データを流さずにスキーマ検証を行い、エラーハンドリングを完成させる。

### 4-1. Dry-Run実装

- `cryoflow check` コマンド（または `run --dry-run`）の追加
- 各プラグインの `dry_run` メソッドを連鎖させ、最終的な出力スキーマを表示

### 4-2. エラーハンドリング強化

- `returns` の `safe` デコレータで予期せぬ例外を `Failure` に変換
- プラグイン境界でのエラーラップ統一

### 4-3. ロギング

- 処理ステップごとのログ出力を整備

---

## 実装済みパイプラインの確認

Phase 3 完了。以下が実装されました：

### 3-1. `pipeline.py` - コアパイプライン実装
- `_detect_format()`: ファイル拡張子から Parquet/IPC 形式を自動判別
- `load_data()`: `@safe` デコレータで例外を `Result` に自動変換
- `execute_transform_chain()`: `returns.Result.bind()` でプラグインを連鎖実行
- `execute_output()`: 変換済みデータを出力プラグインに渡す
- `run_pipeline()`: 読込→変換→出力の統合パイプライン

### 3-2. サンプルプラグイン実装
- `ColumnMultiplierPlugin`: 指定カラムを係数で乗算（LazyFrame の計算グラフ対応）
- `ParquetWriterPlugin`: Parquet ファイルへの出力（`sink_parquet()` でストリーミング書き込み）

### 3-3. テストカバレッジ
- `test_pipeline.py`: パイプライン関数の単体テスト (20テスト)
- `test_transform.py`: 変換プラグインの単体テスト (21テスト)
- `test_output.py`: 出力プラグインの単体テスト (9テスト)
- `test_e2e.py`: E2E統合テスト (4テスト)
- **合計**: 149テスト全て合格

### 3-4. CLI 統合
- `cli.py` の `run` コマンドをパイプライン実行に拡張
- 出力プラグイン検証ロジック（1プラグインのみサポート）
- Success/Failure の処理と詳細なエラーメッセージ表示

### 3-5. 実動作確認
```bash
python -c "from cryoflow_core.cli import app; app(['run', '-c', 'examples/config.toml'])"
```
✅ Parquet → (total_amount × 2) → Parquet として正常に動作

---

## 次のアクション

Phase 3 完了。**Phase 4: Dry-Run と堅牢化** に進む準備完了。
- `cryoflow check` コマンドの実装
- スキーマ検証の強化
- ロギングシステムの統備
