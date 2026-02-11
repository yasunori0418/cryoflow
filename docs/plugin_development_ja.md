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
- [4. TransformPlugin 実装ガイド](#4-transformplugin-実装ガイド)
  - [4.1 基本実装](#41-基本実装)
  - [4.2 実装例: カラム乗算プラグイン](#42-実装例-カラム乗算プラグイン)
  - [4.3 LazyFrame の活用](#43-lazyframe-の活用)
- [5. OutputPlugin 実装ガイド](#5-outputplugin-実装ガイド)
  - [5.1 基本実装](#51-基本実装)
  - [5.2 実装例: Parquet 出力プラグイン](#52-実装例-parquet-出力プラグイン)
- [6. dry_run メソッド実装](#6-dry_run-メソッド実装)
  - [6.1 目的と役割](#61-目的と役割)
  - [6.2 実装パターン](#62-実装パターン)
- [7. エラーハンドリング](#7-エラーハンドリング)
  - [7.1 Result 型の使用](#71-result-型の使用)
  - [7.2 エラーメッセージのベストプラクティス](#72-エラーメッセージのベストプラクティス)
  - [7.3 よくあるエラーパターン](#73-よくあるエラーパターン)
- [8. テストの書き方](#8-テストの書き方)
  - [8.1 基本的なテスト構造](#81-基本的なテスト構造)
  - [8.2 実装例](#82-実装例)
- [9. プラグインの配布](#9-プラグインの配布)
  - [9.1 パッケージ構造](#91-パッケージ構造)
  - [9.2 依存関係の定義](#92-依存関係の定義)
  - [9.3 配布方法](#93-配布方法)
- [10. 設定ファイルでの使用](#10-設定ファイルでの使用)
- [11. リファレンス](#11-リファレンス)
  - [11.1 型定義](#111-型定義)
  - [11.2 基底クラス API](#112-基底クラス-api)
  - [11.3 Polars メソッド参照](#113-polars-メソッド参照)

---

## 1. はじめに

Cryoflow は、Polars LazyFrame を中核としたプラグイン駆動型の列指向データ処理CLIツールです。このガイドでは、Cryoflow 用のカスタムプラグインを開発する方法を解説します。

### 対象読者

- Python の基礎知識がある方
- Polars に触れたことがある、または学習意欲のある方
- データ処理のワークフローを自動化したい方

### このガイドで学べること

- プラグインの基本構造と種類
- TransformPlugin と OutputPlugin の実装方法
- エラーハンドリングとテストのベストプラクティス
- プラグインのパッケージング・配布方法

---

## 2. プラグイン基礎

### 2.1 プラグインの種類

Cryoflow には2種類のプラグインがあります。

#### TransformPlugin（変換プラグイン）

- **役割**: データフレームを受け取り、変換したデータフレームを返す
- **用途**: フィルタリング、カラム追加、集計、結合など
- **特徴**: LazyFrame の計算グラフを構築する（実際の計算は OutputPlugin で実行される）

#### OutputPlugin（出力プラグイン）

- **役割**: データフレームを受け取り、ファイルやデータベースなどに出力する
- **用途**: Parquet/CSV/IPC 出力、データベース書き込み、API送信など
- **特徴**: `collect()` や `sink_*()` を呼び出し、実際にデータ処理を実行する

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
    def __init__(self, options: dict[str, Any]) -> None:
        self.options = options

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
5. execute メソッドの実行 (cryoflow run)
   ↓
6. 結果の出力
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
│   ├── transform/
│   │   ├── __init__.py
│   │   └── my_transform.py    # TransformPlugin 実装
│   └── output/
│       ├── __init__.py
│       └── my_output.py        # OutputPlugin 実装
└── tests/
    ├── test_transform.py
    └── test_output.py
```

---

## 4. TransformPlugin 実装ガイド

### 4.1 基本実装

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

### 4.2 実装例: カラム乗算プラグイン

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

### 4.3 LazyFrame の活用

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

## 5. OutputPlugin 実装ガイド

### 5.1 基本実装

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
            output_path = Path(self.options.get('output_path'))

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
            output_path = Path(self.options.get('output_path'))

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

### 5.2 実装例: Parquet 出力プラグイン

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

            output_path = Path(output_path_opt)

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

            output_path = Path(output_path_opt)

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

## 6. dry_run メソッド実装

### 6.1 目的と役割

`dry_run` メソッドは、実際のデータを処理せずに以下を検証します。

- 設定オプションの妥当性
- 必要なカラムの存在
- カラムの型
- 出力先の書き込み可能性

これにより、本実行前に問題を検出できます（`cryoflow check` コマンド）。

### 6.2 実装パターン

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

## 7. エラーハンドリング

### 7.1 Result 型の使用

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

### 7.2 エラーメッセージのベストプラクティス

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

### 7.3 よくあるエラーパターン

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

## 8. テストの書き方

### 8.1 基本的なテスト構造

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

### 8.2 実装例

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

## 9. プラグインの配布

### 9.1 パッケージ構造

```
my-cryoflow-plugins/
├── README.md
├── LICENSE
├── pyproject.toml
├── my_cryoflow_plugins/
│   ├── __init__.py
│   ├── transform/
│   │   ├── __init__.py
│   │   └── my_transform.py
│   └── output/
│       ├── __init__.py
│       └── my_output.py
└── tests/
    ├── test_transform.py
    └── test_output.py
```

### 9.2 依存関係の定義

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

### 9.3 配布方法

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

## 10. 設定ファイルでの使用

プラグインを実装したら、`config.toml` で使用できます。

### 基本的な使用例

```toml
input_path = "data/input.parquet"
output_target = "data/output.parquet"

# TransformPlugin の設定
[[plugins]]
name = "my-transform"
module = "my_cryoflow_plugins.transform.my_transform"
enabled = true
[plugins.options]
column_name = "value"
multiplier = 2

# OutputPlugin の設定
[[plugins]]
name = "my-output"
module = "my_cryoflow_plugins.output.my_output"
enabled = true
[plugins.options]
output_path = "data/output.parquet"
```

### 複数プラグインのチェーン

```toml
input_path = "data/sales.parquet"
output_target = "data/processed.parquet"

# フィルタリング
[[plugins]]
name = "filter-high-value"
module = "my_plugins.transform.filter"
enabled = true
[plugins.options]
column_name = "total_amount"
threshold = 1000

# カラム追加
[[plugins]]
name = "add-tax"
module = "my_plugins.transform.tax_calculator"
enabled = true
[plugins.options]
amount_column = "total_amount"
tax_rate = 0.1
output_column = "tax"

# 集計
[[plugins]]
name = "aggregate"
module = "my_plugins.transform.aggregator"
enabled = true
[plugins.options]
group_by = ["region", "category"]
agg_columns = ["total_amount", "tax"]

# 出力
[[plugins]]
name = "parquet-writer"
module = "my_plugins.output.parquet_writer"
enabled = true
[plugins.options]
output_path = "data/processed.parquet"
```

### ファイルシステムパスの使用

モジュールをPythonパッケージとしてインストールせず、直接ファイルパスで指定することも可能です。

```toml
[[plugins]]
name = "local-plugin"
module = "./my_local_plugins/transform.py"
enabled = true
[plugins.options]
some_option = "value"

[[plugins]]
name = "absolute-path-plugin"
module = "/home/user/plugins/my_plugin.py"
enabled = true
```

---

## 11. リファレンス

### 11.1 型定義

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

### 11.2 基底クラス API

#### BasePlugin

```python
from abc import ABC, abstractmethod
from typing import Any

from cryoflow_plugin_collections.libs.polars import DataType
from cryoflow_plugin_collections.libs.returns import Result

class BasePlugin(ABC):
    def __init__(self, options: dict[str, Any]) -> None:
        """
        Args:
            options: 設定ファイルから渡されるプラグイン固有のオプション
        """
        self.options = options

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

### 11.3 Polars メソッド参照

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

- ✅ プラグインの基本構造と種類
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
