# Cryoflow プラグイン開発ガイド

## 目次

- [1. はじめに](#1-はじめに)
- [2. プラグイン基礎](#2-プラグイン基礎)
  - [2.1 プラグインの種類](#21-プラグインの種類)
  - [2.2 基本アーキテクチャ](#22-基本アーキテクチャ)
  - [2.3 プラグインのライフサイクル](#23-プラグインのライフサイクル)
- [3. 開発環境のセットアップ](#3-開発環境のセットアップ)
  - [3.1 必要なパッケージ](#31-必要なパッケージ)
  - [3.2 プロジェクト構造](#32-プロジェクト構造)
- [4. InputPlugin 実装ガイド](#4-inputplugin-実装ガイド)
  - [4.1 ラベル機能とマルチストリーム処理](#41-ラベル機能とマルチストリーム処理)
  - [4.2 基本実装](#42-基本実装)
  - [4.3 実装例: CSV ファイル読み込みプラグイン](#43-実装例-csv-ファイル読み込みプラグイン)
- [5. TransformPlugin 実装ガイド](#5-transformplugin-実装ガイド)
  - [5.1 基本実装](#51-基本実装)
  - [5.2 実装例: カラム乗算プラグイン](#52-実装例-カラム乗算プラグイン)
  - [5.3 LazyFrame の活用](#53-lazyframe-の活用)
- [6. OutputPlugin 実装ガイド](#6-outputplugin-実装ガイド)
  - [6.1 基本実装](#61-基本実装)
  - [6.2 実装例: Parquet 出力プラグイン](#62-実装例-parquet-出力プラグイン)
- [7. dry_run メソッド実装](#7-dry_run-メソッド実装)
  - [7.1 目的と役割](#71-目的と役割)
  - [7.2 実装パターン](#72-実装パターン)
- [8. エラーハンドリング](#8-エラーハンドリング)
  - [8.1 Result 型の使用](#81-result-型の使用)
  - [8.2 エラーメッセージのベストプラクティス](#82-エラーメッセージのベストプラクティス)
  - [8.3 よくあるエラーパターン](#83-よくあるエラーパターン)
- [9. テストの書き方](#9-テストの書き方)
  - [9.1 基本的なテスト構造](#91-基本的なテスト構造)
  - [9.2 実装例](#92-実装例)
- [10. プラグインの配布](#10-プラグインの配布)
  - [10.1 パッケージ構造](#101-パッケージ構造)
  - [10.2 依存関係の定義](#102-依存関係の定義)
  - [10.3 配布方法](#103-配布方法)
- [11. 設定ファイルでの使用](#11-設定ファイルでの使用)
- [12. リファレンス](#12-リファレンス)
  - [12.1 型定義](#121-型定義)
  - [12.2 基底クラス API](#122-基底クラス-api)
  - [12.3 Polars メソッド参照](#123-polars-メソッド参照)

---

## 1. はじめに

Cryoflow は、Polars LazyFrame を中核としたプラグイン駆動型の列指向データ処理CLIツールです。このガイドでは、Cryoflow 用のカスタムプラグインを開発する方法を解説します。

### 対象読者

- Python の基礎知識がある方
- Polars に触れたことがある、または学習意欲のある方
- データ処理のワークフローを自動化したい方

### このガイドで学べること

- プラグインの基本構造と種類
- InputPlugin、TransformPlugin、OutputPlugin の実装方法
- ラベル機能を使ったマルチストリーム処理
- エラーハンドリングとテストのベストプラクティス
- プラグインのパッケージング・配布方法

---

## 2. プラグイン基礎

### 2.1 プラグインの種類

Cryoflow には3種類のプラグインがあります。

#### InputPlugin（入力プラグイン）

- **役割**: データソースからデータを読み込み、FrameData を生成する
- **用途**: ファイル読み込み（Parquet/IPC/CSV等）、データベースクエリなど
- **特徴**: `execute` は引数なし。LazyFrame を返すことを推奨

#### TransformPlugin（変換プラグイン）

- **役割**: データフレームを受け取り、変換したデータフレームを返す
- **用途**: フィルタリング、カラム追加、集計、結合など
- **特徴**: LazyFrame の計算グラフを構築する（実際の計算は OutputPlugin で実行される）

#### OutputPlugin（出力プラグイン）

- **役割**: データフレームを受け取り、ファイルやデータベースなどに出力する
- **用途**: Parquet/CSV/IPC 出力、データベース書き込み、API送信など
- **特徴**: `collect()` や `sink_*()` を呼び出し、実際にデータ処理を実行する

**プラグイン種別の比較:**

| プラグイン種別 | execute の引数 | execute の戻り値 | 役割 |
|---|---|---|---|
| **InputPlugin** | なし | `Result[FrameData, Exception]` | データを生成・読み込む |
| **TransformPlugin** | `df: FrameData` | `Result[FrameData, Exception]` | データを変換する |
| **OutputPlugin** | `df: FrameData` | `Result[None, Exception]` | データを出力する |

### 2.2 基本アーキテクチャ

すべてのプラグインは以下の共通インターフェースを実装します。

```python
from abc import ABC, abstractmethod
from typing import Any

from cryoflow_plugin_collections.libs.polars import pl, DataType
from cryoflow_plugin_collections.libs.returns import Result
from cryoflow_plugin_collections.libs.core import FrameData

# FrameData は cryoflow_plugin_collections.libs.core で定義されている
# FrameData = pl.LazyFrame | pl.DataFrame

class BasePlugin(ABC):
    def __init__(self, options: dict[str, Any], config_dir: Path) -> None:
        """プラグインの初期化

        Args:
            options: 設定ファイルから渡されるプラグイン固有のオプション
            config_dir: 設定ファイルが存在するディレクトリ（相対パス解決用）
        """
        self.options = options
        self._config_dir = config_dir

    def resolve_path(self, path: str | Path) -> Path:
        """設定ファイルのディレクトリを基準にパスを解決

        絶対パスはそのまま、相対パスは設定ファイルのディレクトリを基準に解決されます。

        Args:
            path: 解決するパス

        Returns:
            解決された絶対パス
        """
        path = Path(path)
        if not path.is_absolute():
            path = self._config_dir / path
        return path.resolve()

    @abstractmethod
    def name(self) -> str:
        """プラグイン識別名を返す"""

    @abstractmethod
    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """スキーマ検証を行い、処理後のスキーマを返す"""
```

### 2.3 プラグインのライフサイクル

```
1. 設定ファイルの読み込み
   ↓
2. プラグインのロード (importlib)
   ↓
3. プラグインのインスタンス化 (__init__ が呼ばれる)
   ↓
4. [オプション] dry_run による事前検証 (cryoflow check)
   ↓
5. InputPlugin の execute 実行（データ読み込み）
   ↓
6. TransformPlugin の execute 実行（データ変換）
   ↓
7. OutputPlugin の execute 実行（データ出力）
```

---

## 3. 開発環境のセットアップ

### 3.1 必要なパッケージ

プラグイン開発には `cryoflow-plugin-collections` パッケージのみが必要です。このパッケージから、プラグイン開発に必要なライブラリ（`polars`、`returns`、`cryoflow-core`）が re-export されています。

```toml
[project]
dependencies = [
    "cryoflow-plugin-collections",  # プラグイン開発用ライブラリ（polars, returns, cryoflow-core を含む）
]

[project.optional-dependencies]
dev = [
    # テスト関連のパッケージは任意です（開発者の好みに応じて選択）
    "pytest>=8.0.0",         # テストフレームワーク（推奨）
    "pytest-cov>=5.0.0",     # カバレッジ測定（オプション）
]
```

**インポート方法**:

```python
# Polars のインポート
from cryoflow_plugin_collections.libs.polars import pl

# Result 型のインポート
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

# 基底クラスと型定義のインポート
from cryoflow_plugin_collections.libs.core import (
    InputPlugin,
    TransformPlugin,
    OutputPlugin,
    FrameData,
)
```

**注意**: `polars` や `returns` を直接依存関係に追加する必要はありません。`cryoflow-plugin-collections` から提供されるものを使用してください。

### 3.2 プロジェクト構造

推奨されるプロジェクト構造：

```
my-cryoflow-plugins/
├── pyproject.toml
├── my_plugins/
│   ├── __init__.py
│   ├── input/
│   │   ├── __init__.py
│   │   └── my_input.py        # InputPlugin 実装
│   ├── transform/
│   │   ├── __init__.py
│   │   └── my_transform.py    # TransformPlugin 実装
│   └── output/
│       ├── __init__.py
│       └── my_output.py        # OutputPlugin 実装
└── tests/
    ├── test_input.py
    ├── test_transform.py
    └── test_output.py
```

---

## 4. InputPlugin 実装ガイド

### 4.1 ラベル機能とマルチストリーム処理

すべてのプラグインは `label` を持ちます（デフォルト値: `'default'`）。

`label` は、**複数の入力データストリームを識別**するために使用されます。同じラベルを持つプラグイン同士が連携します:

```
InputPlugin(label='sales')  →  data_map['sales']  →  TransformPlugin(label='sales')
InputPlugin(label='master') →  data_map['master'] →  TransformPlugin(label='master')
```

単一データストリームの場合は、`label` を省略するか `'default'` を指定します。

### 4.2 基本実装

```python
from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure
from cryoflow_plugin_collections.libs.core import InputPlugin, FrameData


class MyInputPlugin(InputPlugin):
    def name(self) -> str:
        """プラグイン識別名（ログやエラーメッセージに使用）"""
        return 'my_input'

    def execute(self) -> Result[FrameData, Exception]:
        """データを読み込む（引数なし）"""
        try:
            # self.options からオプションを取得
            input_path_opt = self.options.get('input_path')
            if input_path_opt is None:
                return Failure(ValueError("Option 'input_path' is required"))

            # self.resolve_path() で相対パスを設定ファイル基準で解決
            input_path = self.resolve_path(input_path_opt)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))

            # LazyFrame を返す（collect() は呼ばない）
            return Success(pl.scan_parquet(input_path))
        except Exception as e:
            return Failure(e)

    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """実データを読み込まずにスキーマを返す"""
        try:
            input_path_opt = self.options.get('input_path')
            if input_path_opt is None:
                return Failure(ValueError("Option 'input_path' is required"))

            input_path = self.resolve_path(input_path_opt)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))

            # スキーマのみ取得（実データは読み込まない）
            return Success(dict(pl.scan_parquet(input_path).collect_schema()))
        except Exception as e:
            return Failure(e)
```

### 4.3 実装例: CSV ファイル読み込みプラグイン

CSV ファイルを読み込むプラグインの実装例です。

```python
"""CSV ファイル入力プラグイン"""

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Failure, Result, Success
from cryoflow_plugin_collections.libs.core import FrameData, InputPlugin


class CsvScanPlugin(InputPlugin):
    """CSV ファイルからデータを読み込む

    Options:
        input_path (str): 入力 CSV ファイルのパス
        separator (str): 区切り文字（デフォルト: ','）
        has_header (bool): ヘッダー行の有無（デフォルト: True）
    """

    def name(self) -> str:
        return 'csv_scan'

    def execute(self) -> Result[FrameData, Exception]:
        """CSV ファイルを読み込む

        Returns:
            LazyFrame を含む Result、または失敗時の Exception
        """
        try:
            input_path_opt = self.options.get('input_path')
            if input_path_opt is None:
                return Failure(ValueError("Option 'input_path' is required"))

            input_path = self.resolve_path(input_path_opt)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))

            separator = self.options.get('separator', ',')
            has_header = self.options.get('has_header', True)

            return Success(
                pl.scan_csv(
                    input_path,
                    separator=separator,
                    has_header=has_header,
                )
            )
        except Exception as e:
            return Failure(e)

    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """スキーマを取得する

        Returns:
            スキーマ dict を含む Result、または失敗時の Exception
        """
        try:
            input_path_opt = self.options.get('input_path')
            if input_path_opt is None:
                return Failure(ValueError("Option 'input_path' is required"))

            input_path = self.resolve_path(input_path_opt)
            if not input_path.exists():
                return Failure(FileNotFoundError(f'Input file not found: {input_path}'))

            separator = self.options.get('separator', ',')
            has_header = self.options.get('has_header', True)

            schema = pl.scan_csv(
                input_path,
                separator=separator,
                has_header=has_header,
            ).collect_schema()
            return Success(dict(schema))
        except Exception as e:
            return Failure(e)
```

---

## 5. TransformPlugin 実装ガイド

### 5.1 基本実装

TransformPlugin は以下の3つのメソッドを実装する必要があります。

```python
from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure
from cryoflow_plugin_collections.libs.core import TransformPlugin, FrameData

class MyTransformPlugin(TransformPlugin):
    def name(self) -> str:
        """プラグイン識別名（ログやエラーメッセージに使用される）"""
        return 'my_transform'

    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        """データ変換処理の本体"""
        try:
            # self.options から設定を取得
            column = self.options.get('column_name')
            if column is None:
                return Failure(ValueError("Option 'column_name' is required"))

            # データ変換処理
            transformed = df.with_columns(
                pl.col(column).str.to_uppercase().alias(column)
            )
            return Success(transformed)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """スキーマ検証（実データを触らずに事前チェック）"""
        try:
            column = self.options.get('column_name')
            if column is None:
                return Failure(ValueError("Option 'column_name' is required"))

            # カラム存在チェック
            if column not in schema:
                return Failure(ValueError(f"Column '{column}' not found in schema"))

            # 型チェック
            if schema[column] != pl.Utf8:
                return Failure(ValueError(
                    f"Column '{column}' must be String type, got {schema[column]}"
                ))

            # このプラグインはスキーマを変更しないのでそのまま返す
            return Success(schema)
        except Exception as e:
            return Failure(e)
```

### 5.2 実装例: カラム乗算プラグイン

実際の実装例として、数値カラムに係数を乗算するプラグインを見てみましょう。

```python
"""指定されたカラムに係数を乗算する変換プラグイン"""

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Failure, Result, Success
from cryoflow_plugin_collections.libs.core import FrameData, TransformPlugin


class ColumnMultiplierPlugin(TransformPlugin):
    """指定された数値カラムに係数を乗算する

    Options:
        column_name (str): 対象カラム名
        multiplier (float | int): 乗算する係数
    """

    def name(self) -> str:
        return 'column_multiplier'

    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        """データフレームを変換する

        Args:
            df: 入力 LazyFrame または DataFrame

        Returns:
            変換後のデータを含む Result、または失敗時の Exception
        """
        try:
            column_name = self.options.get('column_name')
            multiplier = self.options.get('multiplier')

            # オプション検証
            if column_name is None:
                return Failure(ValueError("Option 'column_name' is required"))
            if multiplier is None:
                return Failure(ValueError("Option 'multiplier' is required"))

            # データ変換（LazyFrame の計算グラフに追加）
            transformed = df.with_columns(
                (pl.col(column_name) * multiplier).alias(column_name)
            )
            return Success(transformed)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """スキーマを検証し、処理後のスキーマを返す

        Args:
            schema: 入力スキーマ（カラム名 -> DataType のマッピング）

        Returns:
            出力スキーマを含む Result、または失敗時の Exception
        """
        try:
            column_name = self.options.get('column_name')
            multiplier = self.options.get('multiplier')

            # オプション検証
            if column_name is None:
                return Failure(ValueError("Option 'column_name' is required"))
            if multiplier is None:
                return Failure(ValueError("Option 'multiplier' is required"))

            # カラム存在チェック
            if column_name not in schema:
                return Failure(
                    ValueError(f"Column '{column_name}' not found in schema")
                )

            # 型チェック（数値型のみ許可）
            dtype = schema[column_name]
            numeric_types = (
                pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
                pl.Float32, pl.Float64,
            )
            if not (isinstance(dtype, numeric_types) or type(dtype) in numeric_types):
                return Failure(
                    ValueError(
                        f"Column '{column_name}' has type {dtype}, "
                        "expected numeric type"
                    )
                )

            # このプラグインはスキーマを変更しない
            return Success(schema)
        except Exception as e:
            return Failure(e)
```

### 5.3 LazyFrame の活用

TransformPlugin では、データの実体は触らず、計算グラフのみを構築します。

```python
def execute(self, df: FrameData) -> Result[FrameData, Exception]:
    try:
        # ❌ 避けるべき: collect() を呼ぶと即座に実行される
        # materialized = df.collect()
        # filtered = materialized.filter(pl.col("value") > 100)
        # return Success(filtered.lazy())

        # ✅ 推奨: LazyFrame のメソッドチェーンで計算グラフを構築
        filtered = df.filter(pl.col("value") > 100)
        return Success(filtered)
    except Exception as e:
        return Failure(e)
```

**ポイント**:
- `collect()` を呼ばない（OutputPlugin で呼ばれる）
- メソッドチェーンで計算グラフを構築する
- Polars の最適化エンジンが全体を最適化できる

---

## 6. OutputPlugin 実装ガイド

### 6.1 基本実装

OutputPlugin は TransformPlugin と似ていますが、戻り値の型が異なります。

```python
from pathlib import Path

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure
from cryoflow_plugin_collections.libs.core import OutputPlugin, FrameData

class MyOutputPlugin(OutputPlugin):
    def name(self) -> str:
        return 'my_output'

    def execute(self, df: FrameData) -> Result[None, Exception]:
        """データを出力する（ここで初めて collect/sink が呼ばれる）"""
        try:
            # resolve_path()を使用して、相対パスを設定ファイル基準で解決
            output_path = self.resolve_path(self.options.get('output_path'))

            # ディレクトリ作成
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # LazyFrame の場合は sink_*、DataFrame の場合は write_* を使用
            if isinstance(df, pl.LazyFrame):
                df.sink_parquet(output_path)
            else:
                df.write_parquet(output_path)

            return Success(None)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """出力先の書き込み可能性を検証"""
        try:
            # resolve_path()を使用して、相対パスを設定ファイル基準で解決
            output_path = self.resolve_path(self.options.get('output_path'))

            # 親ディレクトリが作成可能かチェック
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return Failure(
                    ValueError(f"Cannot create directory {output_path.parent}: {e}")
                )

            # OutputPlugin はスキーマを変更しない
            return Success(schema)
        except Exception as e:
            return Failure(e)
```

### 6.2 実装例: Parquet 出力プラグイン

```python
"""Parquet ファイル出力プラグイン"""

from pathlib import Path

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Failure, Result, Success
from cryoflow_plugin_collections.libs.core import FrameData, OutputPlugin


class ParquetWriterPlugin(OutputPlugin):
    """データフレームを Parquet ファイルに出力する

    Options:
        output_path (str | Path): 出力先 Parquet ファイルのパス
    """

    def name(self) -> str:
        return 'parquet_writer'

    def execute(self, df: FrameData) -> Result[None, Exception]:
        """データフレームを Parquet ファイルに書き込む

        Args:
            df: 入力 LazyFrame または DataFrame

        Returns:
            成功時は None を含む Result、失敗時は Exception
        """
        try:
            output_path_opt = self.options.get('output_path')
            if output_path_opt is None:
                return Failure(ValueError("Option 'output_path' is required"))

            # resolve_path()で相対パスを設定ファイル基準で解決
            output_path = self.resolve_path(output_path_opt)

            # 親ディレクトリの作成
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # フレームの型に応じて書き込み
            if isinstance(df, pl.LazyFrame):
                # ストリーミング書き込み（メモリ効率が良い）
                df.sink_parquet(output_path)
            else:  # DataFrame
                df.write_parquet(output_path)

            return Success(None)
        except Exception as e:
            return Failure(e)

    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """出力先が書き込み可能かを検証

        Args:
            schema: 入力スキーマ（OutputPlugin は変更しない）

        Returns:
            入力スキーマをそのまま含む Result、または失敗時の Exception
        """
        try:
            output_path_opt = self.options.get('output_path')
            if output_path_opt is None:
                return Failure(ValueError("Option 'output_path' is required"))

            # resolve_path()で相対パスを設定ファイル基準で解決
            output_path = self.resolve_path(output_path_opt)

            # 親ディレクトリが作成可能かチェック
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return Failure(
                    ValueError(
                        f"Cannot create parent directory for {output_path}: {e}"
                    )
                )

            return Success(schema)
        except Exception as e:
            return Failure(e)
```

---

## 7. dry_run メソッド実装

### 7.1 目的と役割

`dry_run` メソッドは、実際のデータを処理せずに以下を検証します。

- 設定オプションの妥当性
- 必要なカラムの存在
- カラムの型
- 出力先の書き込み可能性

これにより、本実行前に問題を検出できます（`cryoflow check` コマンド）。

### 7.2 実装パターン

#### パターン1: スキーマを変更しないプラグイン

```python
from cryoflow_plugin_collections.libs.polars import DataType
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
    """フィルタリングなど、スキーマを変えない処理"""
    try:
        # オプション検証
        threshold = self.options.get('threshold')
        if threshold is None:
            return Failure(ValueError("Option 'threshold' is required"))

        # カラム存在チェック
        column = self.options.get('column_name')
        if column not in schema:
            return Failure(ValueError(f"Column '{column}' not found"))

        # 型チェック
        if not schema[column].is_numeric():
            return Failure(ValueError(f"Column '{column}' must be numeric"))

        # スキーマは変更されない
        return Success(schema)
    except Exception as e:
        return Failure(e)
```

#### パターン2: カラムを追加するプラグイン

```python
from cryoflow_plugin_collections.libs.polars import pl, DataType
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
    """新しいカラムを追加する処理"""
    try:
        new_column = self.options.get('new_column_name', 'computed_value')

        # 重複チェック
        if new_column in schema:
            return Failure(ValueError(f"Column '{new_column}' already exists"))

        # 新しいスキーマを作成
        new_schema = schema.copy()
        new_schema[new_column] = pl.Float64

        return Success(new_schema)
    except Exception as e:
        return Failure(e)
```

#### パターン3: カラムを削除するプラグイン

```python
from cryoflow_plugin_collections.libs.polars import DataType
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
    """カラムを削除する処理"""
    try:
        drop_columns = self.options.get('drop_columns', [])

        # 存在チェック
        for col in drop_columns:
            if col not in schema:
                return Failure(ValueError(f"Column '{col}' not found"))

        # 新しいスキーマを作成
        new_schema = {k: v for k, v in schema.items() if k not in drop_columns}

        return Success(new_schema)
    except Exception as e:
        return Failure(e)
```

---

## 8. エラーハンドリング

### 8.1 Result 型の使用

Cryoflow では `returns` ライブラリの `Result` 型を使用して、エラーハンドリングを統一しています。

```python
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure

# 成功時
return Success(transformed_df)

# 失敗時
return Failure(ValueError("Invalid configuration"))
```

**利点**:
- 例外の伝播を制御できる
- エラーハンドリングが型安全
- パイプライン全体で一貫したエラー処理

### 8.2 エラーメッセージのベストプラクティス

#### ✅ 良いエラーメッセージ

```python
# 具体的な情報を含む
return Failure(ValueError(
    f"Column '{column_name}' not found in schema. "
    f"Available columns: {', '.join(schema.keys())}"
))

# 期待値と実際の値を示す
return Failure(ValueError(
    f"Column '{column_name}' has type {actual_type}, "
    f"expected {expected_type}"
))

# 解決方法を提示
return Failure(ValueError(
    f"Option 'output_path' is required. "
    f"Add 'output_path = \"path/to/file.parquet\"' to plugin options."
))
```

#### ❌ 避けるべきエラーメッセージ

```python
# 情報が不足している
return Failure(ValueError("Column not found"))

# 何が問題かわからない
return Failure(ValueError("Invalid input"))

# 技術的すぎる（ユーザーが理解できない）
return Failure(ValueError("Schema validation failed at line 42"))
```

### 8.3 よくあるエラーパターン

```python
def execute(self, df: FrameData) -> Result[FrameData, Exception]:
    try:
        # 1. オプションの検証
        required_opt = self.options.get('required_option')
        if required_opt is None:
            return Failure(ValueError("Option 'required_option' is required"))

        # 2. カラムの存在チェック（Polars が例外を投げる）
        try:
            result = df.select(pl.col(required_opt))
        except pl.exceptions.ColumnNotFoundError as e:
            return Failure(ValueError(
                f"Column '{required_opt}' not found. Available: {df.columns}"
            ))

        # 3. 型チェック
        dtype = df.schema[required_opt]
        if not dtype.is_numeric():
            return Failure(ValueError(
                f"Column '{required_opt}' must be numeric, got {dtype}"
            ))

        # 4. 値の範囲チェック
        threshold = self.options.get('threshold', 0)
        if threshold < 0:
            return Failure(ValueError(
                f"Option 'threshold' must be non-negative, got {threshold}"
            ))

        # 処理の実行
        transformed = df.filter(pl.col(required_opt) > threshold)
        return Success(transformed)

    except Exception as e:
        # 予期しない例外をキャッチ
        return Failure(e)
```

---

## 9. テストの書き方

### 9.1 基本的なテスト構造

pytest を使用してプラグインをテストします。

```python
import pytest

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Success, Failure

from my_plugins.transform.my_transform import MyTransformPlugin


class TestMyTransformPlugin:
    """MyTransformPlugin のテストスイート"""

    @pytest.fixture
    def plugin(self):
        """プラグインインスタンスを作成"""
        return MyTransformPlugin(options={
            'column_name': 'test_column',
            'multiplier': 2
        })

    @pytest.fixture
    def sample_df(self):
        """テスト用データフレームを作成"""
        return pl.DataFrame({
            'test_column': [1, 2, 3],
            'other_column': ['a', 'b', 'c']
        })

    def test_name(self, plugin):
        """プラグイン名が正しいこと"""
        assert plugin.name() == 'my_transform'

    def test_execute_success(self, plugin, sample_df):
        """正常な変換が成功すること"""
        result = plugin.execute(sample_df.lazy())

        assert isinstance(result, Success)
        df = result.unwrap().collect()
        assert df['test_column'].to_list() == [2, 4, 6]

    def test_execute_missing_option(self):
        """必須オプションが不足している場合にエラーを返すこと"""
        plugin = MyTransformPlugin(options={})
        df = pl.DataFrame({'col': [1, 2, 3]}).lazy()

        result = plugin.execute(df)

        assert isinstance(result, Failure)
        assert "required" in str(result.failure()).lower()

    def test_dry_run_success(self, plugin):
        """スキーマ検証が成功すること"""
        schema = {'test_column': pl.Int64, 'other_column': pl.Utf8}

        result = plugin.dry_run(schema)

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_dry_run_column_not_found(self, plugin):
        """存在しないカラムを指定した場合にエラーを返すこと"""
        schema = {'other_column': pl.Utf8}

        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert "not found" in str(result.failure()).lower()

    def test_dry_run_invalid_type(self):
        """無効な型のカラムを指定した場合にエラーを返すこと"""
        plugin = MyTransformPlugin(options={
            'column_name': 'string_column',
            'multiplier': 2
        })
        schema = {'string_column': pl.Utf8}

        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert "numeric" in str(result.failure()).lower()
```

### 9.2 実装例

```python
"""ColumnMultiplierPlugin のテスト"""

import pytest

from cryoflow_plugin_collections.libs.polars import pl
from cryoflow_plugin_collections.libs.returns import Failure, Success
from cryoflow_plugin_collections.transform.multiplier import ColumnMultiplierPlugin


class TestColumnMultiplierPlugin:
    @pytest.fixture
    def plugin(self):
        return ColumnMultiplierPlugin(options={
            'column_name': 'value',
            'multiplier': 3
        })

    @pytest.fixture
    def sample_lazy_df(self):
        return pl.DataFrame({
            'value': [1, 2, 3, 4, 5],
            'name': ['a', 'b', 'c', 'd', 'e']
        }).lazy()

    def test_name(self, plugin):
        assert plugin.name() == 'column_multiplier'

    def test_execute_with_lazyframe(self, plugin, sample_lazy_df):
        result = plugin.execute(sample_lazy_df)

        assert isinstance(result, Success)
        df = result.unwrap().collect()
        assert df['value'].to_list() == [3, 6, 9, 12, 15]
        assert df['name'].to_list() == ['a', 'b', 'c', 'd', 'e']

    def test_execute_missing_column_name(self, sample_lazy_df):
        plugin = ColumnMultiplierPlugin(options={'multiplier': 2})
        result = plugin.execute(sample_lazy_df)

        assert isinstance(result, Failure)
        error = result.failure()
        assert "'column_name' is required" in str(error)

    def test_execute_missing_multiplier(self, sample_lazy_df):
        plugin = ColumnMultiplierPlugin(options={'column_name': 'value'})
        result = plugin.execute(sample_lazy_df)

        assert isinstance(result, Failure)
        error = result.failure()
        assert "'multiplier' is required" in str(error)

    def test_dry_run_success(self, plugin):
        schema = {'value': pl.Int64, 'name': pl.Utf8}
        result = plugin.dry_run(schema)

        assert isinstance(result, Success)
        assert result.unwrap() == schema

    def test_dry_run_column_not_found(self, plugin):
        schema = {'other': pl.Int64}
        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert "not found in schema" in str(result.failure())

    def test_dry_run_invalid_type(self):
        plugin = ColumnMultiplierPlugin(options={
            'column_name': 'name',
            'multiplier': 2
        })
        schema = {'name': pl.Utf8, 'value': pl.Int64}
        result = plugin.dry_run(schema)

        assert isinstance(result, Failure)
        assert "expected numeric type" in str(result.failure())
```

---

## 10. プラグインの配布

### 10.1 パッケージ構造

```
my-cryoflow-plugins/
├── README.md
├── LICENSE
├── pyproject.toml
├── my_cryoflow_plugins/
│   ├── __init__.py
│   ├── input/
│   │   ├── __init__.py
│   │   └── my_input.py
│   ├── transform/
│   │   ├── __init__.py
│   │   └── my_transform.py
│   └── output/
│       ├── __init__.py
│       └── my_output.py
└── tests/
    ├── test_input.py
    ├── test_transform.py
    └── test_output.py
```

### 10.2 依存関係の定義

`pyproject.toml` の設定例：

```toml
[project]
name = "my-cryoflow-plugins"
version = "0.1.0"
description = "Custom plugins for Cryoflow"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "cryoflow-plugin-collections>=0.1.0",  # プラグイン開発用ライブラリ
]

[project.optional-dependencies]
dev = [
    # テストライブラリは任意です
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### 10.3 配布方法

#### 方法1: PyPI に公開

```bash
# ビルド
python -m build

# PyPI にアップロード（要アカウント）
python -m twine upload dist/*
```

ユーザーは `pip install` でインストール：

```bash
pip install my-cryoflow-plugins
```

#### 方法2: Git リポジトリから直接インストール

```bash
pip install git+https://github.com/username/my-cryoflow-plugins.git
```

#### 方法3: ローカルディレクトリから開発インストール

```bash
cd my-cryoflow-plugins
pip install -e .
```

---

## 11. 設定ファイルでの使用

プラグインを実装したら、`config.toml` で使用できます。

### 基本的な使用例

```toml
# InputPlugin の設定
[[input_plugins]]
name = "parquet-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
[input_plugins.options]
input_path = "data/input.parquet"

# TransformPlugin の設定
[[transform_plugins]]
name = "my-transform"
module = "my_cryoflow_plugins.transform.my_transform"
enabled = true
[transform_plugins.options]
column_name = "value"
multiplier = 2

# OutputPlugin の設定
[[output_plugins]]
name = "my-output"
module = "my_cryoflow_plugins.output.my_output"
enabled = true
[output_plugins.options]
output_path = "data/output.parquet"
```

### 複数プラグインのチェーン

TransformPlugin は定義順にチェーンされ、OutputPlugin は変換済みの同一データを受け取る（fan-out）。

```toml
# InputPlugin の設定
[[input_plugins]]
name = "sales-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
[input_plugins.options]
input_path = "data/sales.parquet"

# フィルタリング
[[transform_plugins]]
name = "filter-high-value"
module = "my_plugins.transform.filter"
enabled = true
[transform_plugins.options]
column_name = "total_amount"
threshold = 1000

# カラム追加
[[transform_plugins]]
name = "add-tax"
module = "my_plugins.transform.tax_calculator"
enabled = true
[transform_plugins.options]
amount_column = "total_amount"
tax_rate = 0.1
output_column = "tax"

# 集計
[[transform_plugins]]
name = "aggregate"
module = "my_plugins.transform.aggregator"
enabled = true
[transform_plugins.options]
group_by = ["region", "category"]
agg_columns = ["total_amount", "tax"]

# 出力（複数定義可能: 同一データを各OutputPluginに渡す）
[[output_plugins]]
name = "parquet-writer"
module = "my_plugins.output.parquet_writer"
enabled = true
[output_plugins.options]
output_path = "data/processed.parquet"

[[output_plugins]]
name = "ipc-writer"
module = "my_plugins.output.ipc_writer"
enabled = true
[output_plugins.options]
output_path = "data/processed.ipc"
```

### マルチストリーム設定例

`label` を使用して、複数の入力データストリームを扱う設定例です。

```toml
# 売上データを読み込む
[[input_plugins]]
name = "sales-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
label = "sales"
[input_plugins.options]
input_path = "data/sales.parquet"

# マスターデータを読み込む
[[input_plugins]]
name = "master-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
label = "master"
[input_plugins.options]
input_path = "data/master.parquet"

# 売上データに対する変換（label = "sales"）
[[transform_plugins]]
name = "sales-filter"
module = "my_plugins.transform.filter"
enabled = true
label = "sales"
[transform_plugins.options]
column_name = "amount"
threshold = 1000

# 売上データの出力
[[output_plugins]]
name = "sales-output"
module = "cryoflow_plugin_collections.output.parquet_write"
enabled = true
label = "sales"
[output_plugins.options]
output_path = "data/filtered_sales.parquet"
```

**ラベルの対応関係**:

```
InputPlugin(label='sales')  →  TransformPlugin(label='sales')  →  OutputPlugin(label='sales')
InputPlugin(label='master') →  (変換なし)                      →  (出力なし)
```

ラベルに対応する TransformPlugin や OutputPlugin が存在しない場合、そのデータストリームはそのまま無視されます。

### ファイルシステムパスの使用

モジュールをPythonパッケージとしてインストールせず、直接ファイルパスで指定することも可能です。

```toml
[[transform_plugins]]
name = "local-plugin"
module = "./my_local_plugins/transform.py"
enabled = true
[transform_plugins.options]
some_option = "value"

[[output_plugins]]
name = "absolute-path-plugin"
module = "/home/user/plugins/my_output_plugin.py"
enabled = true
```

---

## 12. リファレンス

### 12.1 型定義

```python
# cryoflow_plugin_collections.libs から re-export されている型
from typing import Any

from cryoflow_plugin_collections.libs.polars import pl, DataType
from cryoflow_plugin_collections.libs.returns import Result
from cryoflow_plugin_collections.libs.core import FrameData

# データフレーム型（LazyFrame または DataFrame）
# FrameData = pl.LazyFrame | pl.DataFrame として定義されている

# スキーマ型（カラム名 -> データ型のマッピング）
Schema = dict[str, DataType]

# プラグインオプション型
PluginOptions = dict[str, Any]
```

### 12.2 基底クラス API

#### BasePlugin

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from cryoflow_plugin_collections.libs.polars import DataType
from cryoflow_plugin_collections.libs.returns import Result

class BasePlugin(ABC):
    def __init__(self, options: dict[str, Any], config_dir: Path) -> None:
        """プラグインの初期化

        Args:
            options: 設定ファイルから渡されるプラグイン固有のオプション
            config_dir: 設定ファイルが存在するディレクトリ（相対パス解決用）
        """
        self.options = options
        self._config_dir = config_dir

    def resolve_path(self, path: str | Path) -> Path:
        """設定ファイルのディレクトリを基準にパスを解決

        絶対パスはそのまま、相対パスは設定ファイルのディレクトリを基準に解決されます。

        Args:
            path: 解決するパス（文字列またはPathオブジェクト）

        Returns:
            解決された絶対パス

        Example:
            >>> # config.tomlが /project/config/config.toml にある場合
            >>> output_path = self.resolve_path("data/output.parquet")
            >>> # => /project/config/data/output.parquet
        """
        path = Path(path)
        if not path.is_absolute():
            path = self._config_dir / path
        return path.resolve()

    @abstractmethod
    def name(self) -> str:
        """プラグイン識別名を返す

        Returns:
            プラグイン名（ログやエラーメッセージに使用される）
        """

    @abstractmethod
    def dry_run(self, schema: dict[str, DataType]) -> Result[dict[str, DataType], Exception]:
        """スキーマ検証を行う

        Args:
            schema: 入力スキーマ

        Returns:
            Success: 処理後のスキーマ
            Failure: 検証エラー
        """
```

#### InputPlugin

```python
from cryoflow_plugin_collections.libs.core import InputPlugin, FrameData
from cryoflow_plugin_collections.libs.returns import Result
import polars as pl

class InputPlugin(BasePlugin):
    @abstractmethod
    def execute(self) -> Result[FrameData, Exception]:
        """データを読み込み FrameData として返す。

        引数なし。データソースから直接データを生成する。

        Returns:
            Success: 読み込んだデータフレーム（LazyFrame 推奨）
            Failure: 読み込みエラー

        Note:
            - 可能な限り LazyFrame として処理すること
            - collect() を呼ばないこと（OutputPlugin で呼ばれる）
        """

    @abstractmethod
    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """実データを読み込まずにスキーマを返す。

        引数なし。ファイルのメタデータのみを取得する。

        Returns:
            Success: スキーマ（カラム名 → DataType のマッピング）
            Failure: スキーマ取得エラー
        """
```

#### TransformPlugin

```python
from cryoflow_plugin_collections.libs.core import TransformPlugin, FrameData
from cryoflow_plugin_collections.libs.returns import Result

class TransformPlugin(BasePlugin):
    @abstractmethod
    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        """データフレームを変換する

        Args:
            df: 入力データフレーム（LazyFrame または DataFrame）

        Returns:
            Success: 変換後のデータフレーム
            Failure: 処理エラー

        Note:
            - 可能な限り LazyFrame として処理すること
            - collect() を呼ばないこと（OutputPlugin で呼ばれる）
        """
```

#### OutputPlugin

```python
from cryoflow_plugin_collections.libs.core import OutputPlugin, FrameData
from cryoflow_plugin_collections.libs.returns import Result

class OutputPlugin(BasePlugin):
    @abstractmethod
    def execute(self, df: FrameData) -> Result[None, Exception]:
        """データフレームを出力する

        Args:
            df: 入力データフレーム（LazyFrame または DataFrame）

        Returns:
            Success: None（出力成功）
            Failure: 出力エラー

        Note:
            - ここで collect() または sink_*() を呼ぶこと
            - リソース（ファイルハンドラなど）は with 文で管理すること
        """
```

### 組み込みプラグイン

`cryoflow-plugin-collections` パッケージに同梱されている組み込みプラグイン：

| プラグイン | モジュール |
|---|---|
| IPC (Arrow) 入力 | `cryoflow_plugin_collections.input.ipc_scan` |
| Parquet 入力 | `cryoflow_plugin_collections.input.parquet_scan` |

### 12.3 Polars メソッド参照

プラグイン開発でよく使用する Polars メソッド：

#### LazyFrame メソッド

```python
from cryoflow_plugin_collections.libs.polars import pl

# カラム選択
df.select(pl.col("column_name"))
df.select(pl.col("col1"), pl.col("col2"))

# フィルタリング
df.filter(pl.col("value") > 100)
df.filter((pl.col("a") > 10) & (pl.col("b") < 20))

# カラム追加・変更
df.with_columns(pl.col("value") * 2)
df.with_columns((pl.col("a") + pl.col("b")).alias("sum"))

# カラム削除
df.drop("column_name")

# 集計
df.group_by("category").agg(pl.col("value").sum())

# 結合
df.join(other_df, on="key")

# ソート
df.sort("column_name", descending=True)

# 実行（OutputPlugin でのみ使用）
df.collect()  # DataFrame に変換
df.sink_parquet("output.parquet")  # ストリーミング書き込み
```

#### DataFrame メソッド

```python
# LazyFrame への変換
df.lazy()

# ファイル出力
df.write_parquet("output.parquet")
df.write_csv("output.csv")
df.write_ipc("output.arrow")
```

#### 式 (Expression) の構築

```python
# カラム参照
pl.col("column_name")

# 算術演算
pl.col("a") + pl.col("b")
pl.col("value") * 2

# 文字列操作
pl.col("name").str.to_uppercase()
pl.col("text").str.contains("pattern")

# 条件分岐
pl.when(pl.col("value") > 100).then(pl.lit("high")).otherwise(pl.lit("low"))

# 集約関数
pl.col("value").sum()
pl.col("value").mean()
pl.col("value").max()
pl.col("value").count()

# エイリアス（カラム名の変更）
pl.col("old_name").alias("new_name")
```

---

## まとめ

このガイドでは、Cryoflow プラグインの開発方法を解説しました。

### 学んだこと

- ✅ プラグインの基本構造と種類（InputPlugin / TransformPlugin / OutputPlugin）
- ✅ InputPlugin の実装方法とラベル機能によるマルチストリーム処理
- ✅ TransformPlugin と OutputPlugin の実装方法
- ✅ dry_run メソッドによる事前検証
- ✅ Result 型によるエラーハンドリング
- ✅ テストの書き方
- ✅ パッケージング・配布方法

### 次のステップ

1. **簡単なプラグインを作成してみる**
   - まずは `examples/` のサンプルを参考に
   - フィルタリングやカラム追加など基本的な操作から始める

2. **既存のプラグインを読む**
   - `cryoflow-plugin-collections` のコードを参考にする
   - テストコードも併せて確認する

3. **複雑なプラグインに挑戦する**
   - 外部APIとの連携
   - 複雑な集計処理
   - カスタム出力フォーマット

4. **コミュニティに貢献する**
   - 便利なプラグインを公開する
   - バグ報告や改善提案を行う

### 参考リンク

- [Cryoflow 本体リポジトリ](https://github.com/yasunori0418/cryoflow)
- [Polars ドキュメント](https://docs.pola.rs/)
- [returns ライブラリ](https://returns.readthedocs.io/)
- [pluggy ドキュメント](https://pluggy.readthedocs.io/)

---

ご質問やフィードバックは、GitHub Issues でお待ちしています！
