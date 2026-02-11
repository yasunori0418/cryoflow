# cryoflow

Polars LazyFrame を中核とした、プラグイン駆動型の列指向データ処理CLIツール。

**cryoflow** は Apache Arrow (IPC/Parquet) 形式のデータをカスタマイズ可能なプラグインチェーンを通して処理するための強力なツールです。複雑なデータ変換、検証、出力操作をシンプルな設定ファイルで実現できます。

## 特徴

- 🔌 **プラグイン駆動アーキテクチャ**: カスタムプラグインを作成して機能を拡張
- ⚡ **遅延評価**: Polars LazyFrame による効率的なデータ処理
- 📋 **設定ベース**: TOML 設定ファイルでデータパイプラインを定義
- ✅ **ドライラン対応**: 処理前に設定とスキーマを検証
- 🛡️ **堅牢なエラーハンドリング**: Result 型による鉄道指向プログラミング
- 🔄 **ストリーミング対応**: Parquet と Apache Arrow IPC フォーマットに対応
- 🎯 **型安全性**: データロードから出力まで一貫した型安全性

## 前提条件

- Python 3.14 以上
- [uv](https://docs.astral.sh/uv/)（推奨）または pip

## インストール

### uv を使用（推奨）

GitHub リポジトリから直接インストール：

```bash
uv tool install git+https://github.com/yasunori0418/cryoflow
```

お試し実行（インストール不要）：

```bash
uvx --from git+https://github.com/yasunori0418/cryoflow cryoflow --help
```

> **注意**: PyPI 公開後は以下でもインストール可能になります：

```bash
uv tool install cryoflow
```

### pip を使用

> **注意**: PyPI 公開後に利用可能になります。

```bash
pip install cryoflow
```

### Nix を使用

Nix をインストール済みの場合、以下で直接実行できます：

```bash
nix run github:yasunori0418/cryoflow -- --help
```

または、NixOS の設定ファイルや flake.nix に追加できます：

```nix
inputs = {
  cryoflow.url = "github:yasunori0418/cryoflow";
};
```

### ソースからのインストール

```bash
git clone https://github.com/yasunori0418/cryoflow
cd cryoflow
uv sync  # or pip install -e .
```

### Nix Flake と direnv を使用した開発環境

開発目的の場合、direnv または Nix CLI を使用して開発環境をロードできます：

#### direnv を使用（推奨）

```bash
# サンプル設定をコピー
cp example.envrc .envrc

# direnv にロードを許可
direnv allow
```

このディレクトリに入ると、direnv は自動的に `dev/flake.nix` で定義された環境をアクティベートします。uv、ruff、pyright などのツールがすべて含まれた開発環境がセットアップされます。

#### Nix CLI を使用

```bash
# dev/flake.nix の開発環境に入る
nix develop ./dev
```

## クイックスタート

### 1. 設定ファイルの作成

`config.toml` ファイルを作成します：

```toml
input_path = "data/input.parquet"

[[plugins]]
name = "column-multiplier"
module = "cryoflow_plugin_collections.transform.multiplier"
enabled = true
[plugins.options]
column_name = "amount"
multiplier = 2

[[plugins]]
name = "parquet-writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
enabled = true
[plugins.options]
output_path = "data/output.parquet"
```

### 2. パイプラインの実行

```bash
cryoflow run -c config.toml
```

### 3. 設定の検証

実行前に設定を検証します：

```bash
cryoflow check -c config.toml
```

## 使用方法

### CLIコマンド

#### `run` - データ処理パイプラインの実行

設定ファイルで定義されたデータ処理パイプラインを実行します。

```bash
# デフォルト設定ファイルを使用（XDG_CONFIG_HOME/cryoflow/config.toml を検索）
cryoflow run

# カスタム設定ファイルを指定
cryoflow run -c path/to/config.toml

# 詳細ログを出力（デバッグ用）
cryoflow run -c config.toml -v
```

#### `check` - 設定とスキーマの検証

パイプライン設定とスキーマを検証します。実際のデータは処理されません。プリフライト確認に便利です。

```bash
# 設定の妥当性を確認
cryoflow check -c config.toml

# 詳細ログ付きで確認
cryoflow check -c config.toml -v
```

**check コマンドの用途**:

- TOML 設定ファイルの構文検証
- 必要なプラグインがロード可能か確認
- スキーマ変換の検証（変換後のカラム型確認）
- 大規模データ処理前のプリフライト確認

### 設定ファイル

設定ファイルは TOML 形式で以下の内容を定義します：

- **input_path**: 入力 Parquet/IPC ファイルのパス
- **output_target**: 出力対象の指定（プラグイン依存）
- **plugins**: プラグイン設定の配列

各プラグインエントリで指定する項目：

- **name**: プラグイン識別子
- **module**: プラグインをロードする Python モジュールパス
- **enabled**: プラグインを実行するか（true/false）
- **options**: プラグイン固有の設定オプション

### 設定ファイルの例

```toml
# 入出力の指定
input_path = "examples/data/sample_sales.parquet"
output_target = "examples/data/output.parquet"

# 最初のプラグイン: データ変換
[[plugins]]
name = "column-multiplier"
module = "cryoflow_plugin_collections.transform.multiplier"
enabled = true
[plugins.options]
column_name = "total_amount"
multiplier = 2

# 2番目のプラグイン: 結果の出力
[[plugins]]
name = "parquet-writer"
module = "cryoflow_plugin_collections.output.parquet_writer"
enabled = true
[plugins.options]
output_path = "examples/data/output.parquet"
```

### 設定ファイルの検索パス

cryoflow は以下の順序で設定ファイルを検索します：

1. `-c` オプションで指定されたパス
2. `$XDG_CONFIG_HOME/cryoflow/config.toml`（通常は `~/.config/cryoflow/config.toml`）
3. デフォルトの例設定（利用可能な場合）

## プラグインシステム

プラグインはcryoflow の中核の拡張機構です。2つのプラグインタイプがあります：

### TransformPlugin

パイプラインでデータを変換します。DataFrame/LazyFrame を受け取り、変換済みの結果を返します。

```python
class MyTransformPlugin(TransformPlugin):
    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        # 変換ロジックの実装
        return Success(df.with_columns(...))

    def dry_run(self, schema: dict) -> Result[dict, Exception]:
        # スキーマで変換を検証
        return Success(new_schema)
```

### OutputPlugin

データをストレージに出力します。最終的な DataFrame/LazyFrame を受け取り、出力操作を処理します。

```python
class MyOutputPlugin(OutputPlugin):
    def execute(self, df: FrameData) -> Result[None, Exception]:
        # 出力ロジックの実装
        df.sink_parquet("output.parquet")
        return Success(None)

    def dry_run(self, schema: dict) -> Result[None, Exception]:
        # 出力可能性を検証
        return Success(None)
```

すべてのプラグインは `dry_run` メソッドを持ち、実データを流さずにスキーマ検証が可能です。

## エラーハンドリング

cryoflow は `returns` ライブラリを使用した鉄道指向プログラミングで堅牢なエラー処理を実現しています。

- プラグイン間のデータ受け渡しは `Result[FrameData, Exception]` でラップ
- パイプライン制御では `flow`/`bind` コンビネータを使用し、`Failure` 発生時に即座に処理を中断
- サイレント失敗がない - すべてのエラーが明示的に処理される

## データフロー構成

```
設定読み込み
    ↓
プラグイン発見
    ↓
パイプライン構築
    ↓
実行 / 出力
```

1. **設定読み込み**: TOML ファイルから設定を読み込み、Pydantic で検証
2. **プラグイン発見**: `importlib` で指定モジュールをロードし、`pluggy` に登録
3. **パイプライン構築**: ソースデータを LazyFrame に変換、`TransformPlugin` フックを実行して計算グラフを構築
4. **実行 / 出力**: `OutputPlugin` フックを実行。ここで `collect()` または `sink_*()` が呼ばれ、実処理が実行される

## 技術スタック

| カテゴリ | ライブラリ/技術 | 用途 |
| --- | --- | --- |
| Core | Polars | 列指向データ処理エンジン（LazyFrame 主軸） |
| CLI | Typer | モダン CLI フレームワークとコマンド定義 |
| Plugin | pluggy + importlib | プラグイン機構、フック管理、動的ロード |
| Config | Pydantic + TOML | 型安全な設定定義とバリデーション |
| Path | xdg-base-dirs | XDG Base Directory 仕様への準拠 |
| Error | returns | Result Monad による関数型エラーハンドリング |
| Base | ABC (標準ライブラリ) | プラグインインターフェース定義 |

## 例

サンプルデータと設定ファイルは `examples/` ディレクトリに用意されています：

```bash
# サンプルパイプラインを実行
cryoflow run -c examples/config.toml

# サンプル設定を検証
cryoflow check -c examples/config.toml
```

examples ディレクトリに含まれるもの：

- `config.toml`: パイプライン設定の例
- `data/sample_sales.parquet`: サンプル売上データ（Parquet 形式）
- `data/sample_sales.ipc`: 同じデータを Arrow IPC 形式で
- `data/sensor_readings.parquet`: センサーデータの例

## ドキュメント

詳細な情報については以下をご参照ください：

- [仕様書](docs/spec_ja.md) - 完全な API 仕様とインターフェース設計
- [実装計画](docs/implements_step_plan_ja.md) - 技術実装の詳細
- [進捗](docs/progress_ja.md) - プロジェクト開発進捗

英語版のドキュメントは `docs/{filename}.md` をご参照ください。

## トラブルシューティング

### 設定ファイルが見つからない

**エラー**: `Configuration file not found`

**解決方法**:
- ファイルパスが正しいか確認してください
- `-c` オプションを使用して設定ファイルを明示的に指定してください
- デフォルト位置を使用する場合、`~/.config/cryoflow/config.toml` が存在するか確認してください

### プラグインが見つからない

**エラー**: `Module not found: cryoflow_plugin_collections`

**解決方法**:
- 必要なプラグインをインストール: `pip install cryoflow-plugin-collections`
- 設定ファイル内のモジュールパスが正しいか確認してください

### スキーマ検証エラー

**エラー**: `Schema validation failed`

**解決方法**:
- `cryoflow check -c config.toml -v` を実行して詳細なログを確認してください
- カラム名と型が入力データと一致しているか確認してください
- プラグインのオプションが正しいか確認してください

### その他の問題

- `examples/` ディレクトリの設定例を参照してください
- `-v` フラグで詳細ログを出力してください
- `docs/` ディレクトリのドキュメントを確認してください

## ライセンス

このプロジェクトは MIT ライセンスの下でライセンスされています。詳細については [LICENSE](LICENSE) ファイルを参照してください。

## 貢献

貢献をお待ちしています。プルリクエストを提出していただければ幸いです。

## サポート

問題報告、質問、提案については [GitHub リポジトリ](https://github.com/yasunori0418/cryoflow/issues) で Issue を開いてください。
