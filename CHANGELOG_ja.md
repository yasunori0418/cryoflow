# 変更履歴

このプロジェクトの主要な変更点はすべてこのファイルに記録されます。

フォーマットは [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) に基づき、
バージョン管理は [Semantic Versioning](https://semver.org/spec/v2.0.0.html) に準拠しています。

## [0.2.0] - 2026-02-22

### 追加

- **`InputPlugin` ABC** (`cryoflow-core`):
  - 任意のソースからデータを読み込むための新しい `InputPlugin` 基底クラスを追加
  - `execute()` は引数なしで `Result[FrameData, Exception]` を返す
  - `dry_run()` は実データを読み込まずにスキーマを返す
  - `hookspecs.py` の新しい `register_input_plugins` hookspec で登録

- **`BasePlugin` への `label` 属性追加** (`cryoflow-core`):
  - 全プラグインに `label` 文字列を付与（デフォルト値: `'default'`）
  - 複数の並行データストリームにおけるラベルベースのルーティングを実現

- **`InputPlugin` の具体的な実装** (`cryoflow-plugin-collections`):
  - `cryoflow_plugin_collections.input.parquet_scan` — `pl.scan_parquet()` を使用してParquetファイルを読み込む
  - `cryoflow_plugin_collections.input.ipc_scan` — `pl.scan_ipc()` を使用してArrow IPCファイルを読み込む

- **`libs/returns` サブモジュール分割** (`cryoflow-plugin-collections`):
  - `libs/returns/result.py` — `Result`、`Success`、`Failure` および関連ユーティリティを再エクスポート
  - `libs/returns/maybe.py` — `Maybe`、`Some`、`Nothing` および関連ユーティリティを再エクスポート
  - 後方互換性のため、両方とも `libs/returns/__init__.py` から再エクスポート

- **ドキュメント**: InputPlugin ガイドを `docs/plugin_development.md` / `docs/plugin_development_ja.md` に統合

### 変更

- **破壊的変更**: `config.py` — `RunConfig` から `input_path: Path` フィールドを削除し、`input_plugins: list[PluginConfig]` に置き換え
- **破壊的変更**: `config.py` — `plugins` フィールドを `transform_plugins` と `output_plugins`（別々のリスト）に分割・名称変更
- **破壊的変更**: `config.py` — `PluginConfig` に `label` フィールドを追加（マルチストリームルーティングに必須）
- **破壊的変更**: `pipeline.py` — `load_data()` と `_detect_format()` を削除。パイプラインはラベルをキーとする `LabeledDataMap` を基盤とするように変更
- **破壊的変更**: `loader.py` — `InputPlugin` のロード・登録処理を追加。インスタンス化時に全プラグインへ `label` を渡すように変更

### テスト

- 全テストファイルをフラットなレイアウトからモジュールごとのディレクトリ構成に再編（1ファイル1クラス）
- パイプラインテストを追加: ラベルルーティング、`LabeledDataMap` の構築、`execute_transform_chain`、`execute_output`、ドライランパイプライン
- `InputPlugin` 単体テスト、`label` 属性テストを追加
- 合計: 232テスト全て通過

---

### マイグレーションガイド

#### 設定ファイルのマイグレーション

トップレベルの `input_path` キーは廃止されました。入力データソースは `[[input_plugins]]` エントリとして宣言する必要があります。

```toml
# 変更前 (0.1.x)
input_path = "data/input.parquet"

[[plugins]]
name = "column-multiplier"
module = "cryoflow_plugin_collections.transform.multiplier"

[[plugins]]
name = "parquet-writer"
module = "cryoflow_plugin_collections.output.parquet_writer"

# 変更後 (0.2.0)
[[input_plugins]]
name = "parquet-scan"
module = "cryoflow_plugin_collections.input.parquet_scan"
label = "default"
[input_plugins.options]
input_path = "data/input.parquet"

[[transform_plugins]]
name = "column-multiplier"
module = "cryoflow_plugin_collections.transform.multiplier"
label = "default"

[[output_plugins]]
name = "parquet-writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
label = "default"
```

#### プラグイン開発のマイグレーション

旧 `plugins` 設定キーや `load_data()` パイプラインAPIを参照していたカスタムプラグインがある場合、以下の手順で更新してください。

- 設定ファイルの `plugins` を `transform_plugins` または `output_plugins` に置き換え
- `pipeline.load_data()` や `pipeline._detect_format()` に依存するコードを削除
- `InputPlugin.execute()` は **引数なし**（`TransformPlugin` / `OutputPlugin` が `df: FrameData` を受け取るのとは異なる）
- 全プラグイン設定エントリに `label` を割り当て。単一ストリームのパイプラインには `'default'` を使用

#### `libs/returns` のインポートパス（変更なし）

`libs/returns` モジュールは内部的に `result.py` と `maybe.py` に分割されましたが、全ての公開シンボルは引き続き `cryoflow_plugin_collections.libs.returns` からインポート可能です。インポートの変更は不要です。

---

## [0.1.3] - 2026-02-17

### 追加

- **Polars API の完全な再エクスポート** (`cryoflow-plugin-collections`):
  - ワイルドカードインポートを使用して polars の228以上の公開APIを全て再エクスポート
  - 3つのインポートパターンをサポート:
    1. モジュールインポート: `from libs import polars as pl; pl.col()`
    2. オブジェクトインポート: `from libs.polars import pl; pl.col()`
    3. 個別インポート: `from libs.polars import col, lit, when`
  - polars のアップデートを自動追跡するための動的な `__all__` 生成
  - メンテナンスコストゼロ、ランタイムオーバーヘッドゼロ
  - 完全な型安全性とIDEオートコンプリートのサポート

- **returns ライブラリの完全な再エクスポート** (`cryoflow-plugin-collections`):
  - returns の13の主要モジュールから146以上のユニークな公開APIを再エクスポート
  - 新たに利用可能なコンテナとユーティリティ:
    - オプション値のための `Maybe` モナド（`Some`、`Nothing`）
    - 副作用管理のための `IO` コンテナ（`IO`、`IOResult`）
    - 非同期処理のための `Future`（`Future`、`FutureResult`）
    - 依存性注入のための `Context`（`RequiresContext`）
    - パイプラインユーティリティ（`flow`、`pipe`）
    - ポイントフリー操作（`bind`、`map`、`alt`、`lash`）
    - カリー化・部分適用ユーティリティ
    - コンテナ変換のためのコンバーターとメソッド
  - 個別インポートをサポート: `from libs.returns import Maybe, IO, flow`
  - プラグイン開発者向けの完全な関数型プログラミングツールキット

### 変更

- **`__all__` 構築の改善** (`cryoflow-plugin-collections`):
  - returns モジュールを単一代入パターンを使用するようにリファクタリング
  - 破壊的な extend/再代入をリスト内包表記と一時変数に置き換え
  - 静的解析の互換性向上（Pyright 警告の削減）

### テスト

- polars 再エクスポートの包括的なテストを追加（新規4テストケース）
- returns 再エクスポートの包括的なテストを追加（新規4テストケース）
- 後方互換性を維持しつつ全44テスト通過

## [0.1.0] - 2025-02-12

### 追加

- **パス解決システム**: 設定ファイル内の全ファイルパスが設定ファイルのディレクトリからの相対パスで解決されるように変更
  - `config.py`: `_resolve_path_relative_to_config()` ヘルパー関数を追加
  - `BasePlugin`: プラグイン全体で一貫したパス解決を行うための `resolve_path()` メソッドを追加
  - 相対パス解決に関する包括的なE2Eテスト

### 変更

- **破壊的変更**: `BasePlugin.__init__()` に `config_dir` パラメータが必須になりました（省略不可）
  - 技術的負債解消のため後方互換性フォールバックを削除
  - 全プラグインはインスタンス化時に `config_dir` を明示的に受け取る必要があります
- **破壊的変更**: `input_path` の相対パスがカレントワーキングディレクトリではなく、設定ファイルのディレクトリからの相対パスで解決されるように変更
- **破壊的変更**: プラグインオプションのパスが設定ファイルのディレクトリからの相対パスで解決されるように変更
- `ParquetWriterPlugin` が出力パスに `resolve_path()` を使用するように更新
- 全サンプル設定を相対パスを使用するように更新

### ドキュメント

- `docs/spec.md` と `docs/spec_ja.md` にパス解決の動作に関する包括的なセクションを追加
- `README.md` と `README_ja.md` にパス解決ガイドラインを追記
- プラグイン開発ガイド（`docs/plugin_development.md`、`docs/plugin_development_ja.md`）を新しいAPIに合わせて更新

### マイグレーションガイド

#### 設定ファイルの場合

相対パスを設定ファイルの配置場所からの相対パスに更新してください。

```toml
# 変更前 (0.0.x): カレントワーキングディレクトリからの相対パス
input_path = "examples/data/input.parquet"

# 変更後 (0.1.0): 設定ファイルのディレクトリからの相対パス
# config.toml がプロジェクトルートにある場合:
input_path = "examples/data/input.parquet"  # プロジェクトルートから実行する場合は同じ

# config.toml が config/ にある場合:
input_path = "../examples/data/input.parquet"  # または絶対パスを使用
```

#### プラグイン開発の場合

プラグインのコンストラクタが `config_dir` を受け取るように更新してください。

```python
# 変更前 (0.0.x)
class MyPlugin(OutputPlugin):
    def execute(self, df):
        output_path = Path(self.options.get('output_path'))
        # ...

# 変更後 (0.1.0)
class MyPlugin(OutputPlugin):
    def execute(self, df):
        output_path = self.resolve_path(self.options.get('output_path'))
        # ...
```

## [0.0.4] - 2025-02-11

### 変更

- 未使用の `output_target` 設定フィールドを削除

## [0.0.3] - 2025-02-11

コア機能を含む最初の動作リリース。
