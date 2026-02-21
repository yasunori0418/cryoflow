# InputPlugin ガイド

## 目次

- [1. はじめに](#1-はじめに)
- [2. InputPlugin とは](#2-inputplugin-とは)
  - [2.1 他のプラグインとの違い](#21-他のプラグインとの違い)
  - [2.2 ラベル機能とマルチストリーム処理](#22-ラベル機能とマルチストリーム処理)
- [3. インターフェース](#3-インターフェース)
  - [3.1 execute メソッド](#31-execute-メソッド)
  - [3.2 dry_run メソッド](#32-dry_run-メソッド)
- [4. 組み込みプラグイン](#4-組み込みプラグイン)
  - [4.1 IpcScanPlugin](#41-ipcscanplugin)
  - [4.2 ParquetScanPlugin](#42-parquetscanplugin)
- [5. カスタム InputPlugin の実装](#5-カスタム-inputplugin-の実装)
  - [5.1 基本実装](#51-基本実装)
  - [5.2 実装例: CSV ファイル読み込みプラグイン](#52-実装例-csv-ファイル読み込みプラグイン)
- [6. 設定ファイルでの使用](#6-設定ファイルでの使用)
  - [6.1 基本的な設定例](#61-基本的な設定例)
  - [6.2 マルチストリーム設定例](#62-マルチストリーム設定例)
- [7. テストの書き方](#7-テストの書き方)
- [8. リファレンス](#8-リファレンス)

---

## 1. はじめに

このガイドでは、Cryoflow の `InputPlugin` について解説します。

以前のバージョンでは、入力データのパスは設定ファイルの `input_path` キーで直接指定していました。現在は `InputPlugin` がこの役割を担い、**データの読み込み方法をプラグインとして差し替え可能**な設計になっています。

---

## 2. InputPlugin とは

`InputPlugin` は、データの読み込みを担当するプラグインです。ファイル読み込みやデータベースクエリなど、**データソースの種類に応じて交換可能**です。

パイプラインでの位置づけ:

```
InputPlugin → TransformPlugin(s) → OutputPlugin(s)
    ↓
データを生成 (FrameData)
    ↓
変換・加工
    ↓
出力
```

### 2.1 他のプラグインとの違い

| プラグイン種別 | execute の引数 | execute の戻り値 | 役割 |
|---|---|---|---|
| **InputPlugin** | なし | `Result[FrameData, Exception]` | データを生成・読み込む |
| TransformPlugin | `df: FrameData` | `Result[FrameData, Exception]` | データを変換する |
| OutputPlugin | `df: FrameData` | `Result[None, Exception]` | データを出力する |

InputPlugin の `execute` はデータフレームを**引数として受け取らず**、データソースからデータを生成して返します。

また、`dry_run` の戻り値も異なります:

| プラグイン種別 | dry_run の引数 | dry_run の戻り値 |
|---|---|---|
| **InputPlugin** | なし | `Result[dict[str, pl.DataType], Exception]` |
| TransformPlugin | `schema: dict[str, pl.DataType]` | `Result[dict[str, pl.DataType], Exception]` |
| OutputPlugin | `schema: dict[str, pl.DataType]` | `Result[dict[str, pl.DataType], Exception]` |

InputPlugin の `dry_run` は、実データを読み込まずにスキーマのみを返します。

### 2.2 ラベル機能とマルチストリーム処理

すべてのプラグインは `label` を持ちます（デフォルト値: `'default'`）。

`label` は、**複数の入力データストリームを識別**するために使用されます。同じラベルを持つプラグイン同士が連携します:

```
InputPlugin(label='sales')  →  data_map['sales']  →  TransformPlugin(label='sales')
InputPlugin(label='master') →  data_map['master'] →  TransformPlugin(label='master')
```

単一データストリームの場合は、`label` を省略するか `'default'` を指定します。

---

## 3. インターフェース

```python
from abc import abstractmethod
import polars as pl
from returns.result import Result
from cryoflow_plugin_collections.libs.core import InputPlugin, FrameData

class InputPlugin(BasePlugin):
    @abstractmethod
    def execute(self) -> Result[FrameData, Exception]:
        """データを読み込み、FrameData として返す"""

    @abstractmethod
    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """実データを読み込まずにスキーマを返す"""
```

### 3.1 execute メソッド

`execute` は引数なしで呼び出され、データソースからデータを読み込みます。

**戻り値**:
- `Success(LazyFrame)` または `Success(DataFrame)`: 読み込み成功
- `Failure(Exception)`: 読み込み失敗

**注意**:
- 可能な限り `pl.scan_*` などの遅延評価 API を使い `LazyFrame` を返すことを推奨します
- `collect()` の呼び出しは OutputPlugin に任せることが理想的です

### 3.2 dry_run メソッド

`dry_run` は実データを読み込まずに、出力されるスキーマ（カラム名とデータ型のマッピング）を返します。

**戻り値**:
- `Success(dict[str, pl.DataType])`: スキーマの取得成功
- `Failure(Exception)`: スキーマの取得失敗

**用途**: `cryoflow check` コマンドで事前検証する際に使用されます。

---

## 4. 組み込みプラグイン

`cryoflow-plugin-collections` パッケージには、以下の InputPlugin が同梱されています。

### 4.1 IpcScanPlugin

Apache Arrow IPC 形式のファイルを読み込むプラグインです。

**モジュール**: `cryoflow_plugin_collections.input.ipc_scan`

**オプション**:

| オプション | 型 | 必須 | 説明 |
|---|---|---|---|
| `input_path` | `str` | はい | 入力 IPC ファイルのパス |

**設定例**:

```toml
[[input_plugins]]
name = "ipc-input"
module = "cryoflow_plugin_collections.input.ipc_scan"
enabled = true
[input_plugins.options]
input_path = "data/input.arrow"
```

### 4.2 ParquetScanPlugin

Parquet 形式のファイルを読み込むプラグインです。

**モジュール**: `cryoflow_plugin_collections.input.parquet_scan`

**オプション**:

| オプション | 型 | 必須 | 説明 |
|---|---|---|---|
| `input_path` | `str` | はい | 入力 Parquet ファイルのパス |

**設定例**:

```toml
[[input_plugins]]
name = "parquet-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
[input_plugins.options]
input_path = "data/input.parquet"
```

---

## 5. カスタム InputPlugin の実装

### 5.1 基本実装

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

### 5.2 実装例: CSV ファイル読み込みプラグイン

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

## 6. 設定ファイルでの使用

`config.toml` では `[[input_plugins]]` セクションで設定します。

### 6.1 基本的な設定例

```toml
# 組み込みの Parquet 読み込みプラグインを使用する例
[[input_plugins]]
name = "parquet-input"
module = "cryoflow_plugin_collections.input.parquet_scan"
enabled = true
[input_plugins.options]
input_path = "data/input.parquet"

[[transform_plugins]]
name = "my-transform"
module = "my_plugins.transform.my_transform"
enabled = true
[transform_plugins.options]
column_name = "value"

[[output_plugins]]
name = "parquet-output"
module = "cryoflow_plugin_collections.output.parquet_write"
enabled = true
[output_plugins.options]
output_path = "data/output.parquet"
```

### 6.2 マルチストリーム設定例

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

---

## 7. テストの書き方

InputPlugin のテストでは、以下の点を確認します:

- `execute()` が正しく `Success(LazyFrame)` を返すこと
- `dry_run()` が正しくスキーマを返すこと
- 必須オプション不足時に `Failure` を返すこと
- ファイルが存在しない場合に `Failure` を返すこと

```python
from pathlib import Path
import pytest
import polars as pl
from returns.result import Success, Failure

from my_plugins.input.csv_scan import CsvScanPlugin


class TestCsvScanPlugin:
    """CsvScanPlugin のテストスイート"""

    @pytest.fixture
    def sample_csv(self, tmp_path: Path) -> Path:
        """テスト用 CSV ファイルを作成"""
        csv_path = tmp_path / 'test.csv'
        csv_path.write_text("id,value\n1,100\n2,200\n3,300\n")
        return csv_path

    @pytest.fixture
    def plugin(self, sample_csv: Path) -> CsvScanPlugin:
        """プラグインインスタンスを作成"""
        return CsvScanPlugin(
            options={'input_path': str(sample_csv)},
            config_dir=sample_csv.parent,
        )

    def test_name(self, plugin: CsvScanPlugin):
        """プラグイン名が正しいこと"""
        assert plugin.name() == 'csv_scan'

    def test_execute_success(self, plugin: CsvScanPlugin):
        """正常な読み込みが成功すること"""
        result = plugin.execute()

        assert isinstance(result, Success)
        df = result.unwrap().collect()
        assert df.shape == (3, 2)
        assert df['id'].to_list() == [1, 2, 3]
        assert df['value'].to_list() == [100, 200, 300]

    def test_execute_returns_lazyframe(self, plugin: CsvScanPlugin):
        """execute が LazyFrame を返すこと"""
        result = plugin.execute()

        assert isinstance(result, Success)
        assert isinstance(result.unwrap(), pl.LazyFrame)

    def test_execute_missing_input_path(self, sample_csv: Path):
        """必須オプション input_path がない場合に Failure を返すこと"""
        plugin = CsvScanPlugin(
            options={},
            config_dir=sample_csv.parent,
        )
        result = plugin.execute()

        assert isinstance(result, Failure)
        assert "'input_path' is required" in str(result.failure())

    def test_execute_file_not_found(self, tmp_path: Path):
        """存在しないファイルを指定した場合に Failure を返すこと"""
        plugin = CsvScanPlugin(
            options={'input_path': 'nonexistent.csv'},
            config_dir=tmp_path,
        )
        result = plugin.execute()

        assert isinstance(result, Failure)
        assert isinstance(result.failure(), FileNotFoundError)

    def test_dry_run_success(self, plugin: CsvScanPlugin):
        """dry_run が正しいスキーマを返すこと"""
        result = plugin.dry_run()

        assert isinstance(result, Success)
        schema = result.unwrap()
        assert 'id' in schema
        assert 'value' in schema

    def test_dry_run_missing_input_path(self, sample_csv: Path):
        """必須オプション input_path がない場合に Failure を返すこと"""
        plugin = CsvScanPlugin(
            options={},
            config_dir=sample_csv.parent,
        )
        result = plugin.dry_run()

        assert isinstance(result, Failure)
        assert "'input_path' is required" in str(result.failure())
```

---

## 8. リファレンス

### InputPlugin クラス API

```python
class InputPlugin(BasePlugin):
    def execute(self) -> Result[FrameData, Exception]:
        """データを読み込み FrameData として返す。

        引数なし。データソースから直接データを生成する。

        Returns:
            Success: 読み込んだデータフレーム（LazyFrame 推奨）
            Failure: 読み込みエラー
        """

    def dry_run(self) -> Result[dict[str, pl.DataType], Exception]:
        """実データを読み込まずにスキーマを返す。

        引数なし。ファイルのメタデータのみを取得する。

        Returns:
            Success: スキーマ（カラム名 → DataType のマッピング）
            Failure: スキーマ取得エラー
        """
```

### BasePlugin から継承されるメソッド

```python
def resolve_path(self, path: str | Path) -> Path:
    """設定ファイルのディレクトリを基準にパスを解決。

    絶対パスはそのまま返す。
    相対パスは設定ファイルのディレクトリ (self._config_dir) を基準に解決する。

    Example:
        >>> # config.toml が /project/config/config.toml にある場合
        >>> plugin.resolve_path("data/input.parquet")
        PosixPath('/project/config/data/input.parquet')
    """
```

### インポートパス

```python
# 基底クラスと型定義
from cryoflow_plugin_collections.libs.core import InputPlugin, FrameData

# Polars
from cryoflow_plugin_collections.libs.polars import pl

# Result 型
from cryoflow_plugin_collections.libs.returns import Result, Success, Failure
```

### 組み込みプラグインのモジュールパス

| プラグイン | モジュール |
|---|---|
| IPC (Arrow) 入力 | `cryoflow_plugin_collections.input.ipc_scan` |
| Parquet 入力 | `cryoflow_plugin_collections.input.parquet_scan` |

---

### 関連ドキュメント

- [プラグイン開発ガイド](plugin_development_ja.md): TransformPlugin / OutputPlugin の実装方法
- [仕様書](spec_ja.md): システム全体のアーキテクチャと設計
