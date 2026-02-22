# CLIツール "cryoflow" 仕様書

## 1. 概要

Polars LazyFrame を中核とした、プラグイン駆動型の列指向データ処理CLIツール。
Apache Arrow (IPC/Parquet) 形式のデータを入力とし、ユーザー定義のプラグインチェーンを経てデータの加工・検証・出力を行う。

## 2. アーキテクチャ構成

### 2.1 技術スタック

| カテゴリ | ライブラリ/技術 | 用途 |
| --- | --- | --- |
| **Core** | **Polars** | データ処理エンジン (LazyFrame主軸) |
| **CLI** | **Typer** | CLIインターフェース、コマンド定義 |
| **Plugin** | **pluggy** + **importlib** | プラグイン機構、フック管理、動的ロード |
| **Config** | **Pydantic** + **TOML** | 設定定義、バリデーション |
| **Path** | **xdg-base-dirs** | XDG準拠のコンフィグパス解決 |
| **Error** | **returns** | Result Monadによる鉄道指向プログラミング的エラーハンドリング |
| **Base** | **ABC** (Standard Lib) | プラグインインターフェース定義 |

### 2.2 データフロー

1. **Config Load**: `XDG_CONFIG_HOME/cryoflow/config.toml` を読み込み、Pydantic で検証。
2. **Plugin Discovery**: 設定ファイルに基づき、`importlib` で指定モジュールをロードし、`pluggy` に登録。
3. **Pipeline Construction**:
* Source (Parquet/IPC) を `pl.scan_*` で LazyFrame 化。
* `TransformPlugin` フックを順次実行し、計算グラフ (LazyFrame) を構築。


4. **Execution / Output**:
* `OutputPlugin` フックを実行。ここで初めて `collect()` または `sink_*()` が呼ばれ、処理が実行される。



---

## 3. インターフェース設計

### 3.1 データモデル (Pydantic)

```python
from typing import Any

from pydantic import BaseModel, Field

class PluginConfig(BaseModel):
    name: str
    module: str  # importlibで読み込むパス
    enabled: bool = True
    label: str = 'default'  # マルチストリームルーティング用ラベル
    options: dict[str, Any] = Field(default_factory=dict) # プラグイン固有設定

class CryoflowConfig(BaseModel):
    input_plugins: list[PluginConfig]
    transform_plugins: list[PluginConfig]
    output_plugins: list[PluginConfig]
```

> **実装時の変更点**:
> - `GlobalConfig` → `CryoflowConfig` にリネーム（より明確な名前）
> - Python 3.14 ビルトイン型（`list`, `dict`）を使用（`typing.List`, `typing.Dict` は非推奨）
> - `input_path` は v0.2.0 で削除。データソースは `InputPlugin` エントリとして宣言するように変更
> - `label` を v0.2.0 で `PluginConfig` に追加。ラベルベースのマルチストリームルーティングに使用

### 3.2 プラグイン基底クラス (ABC)

`pluggy` は関数ベースのフックも扱えますが、ABCによる契約と `dry_run` の強制のため、クラスベースのプラグイン設計とします。

```python
from abc import ABC, abstractmethod
from typing import Any

import polars as pl
from returns.result import Result

# データ型エイリアス
FrameData = pl.LazyFrame | pl.DataFrame

class BasePlugin(ABC):
    """全てのプラグインの基底クラス"""
    def __init__(self, options: dict[str, Any]):
        self.options = options

    @abstractmethod
    def name(self) -> str:
        """プラグイン識別名"""
        pass

    @abstractmethod
    def dry_run(self, schema: dict[str, pl.DataType]) -> Result[dict[str, pl.DataType], Exception]:
        """スキーマのみを受け取り、処理後の予想スキーマを返す（またはエラー）"""
        pass

class TransformPlugin(BasePlugin):
    """データ変換プラグイン"""
    @abstractmethod
    def execute(self, df: FrameData) -> Result[FrameData, Exception]:
        pass

class OutputPlugin(BasePlugin):
    """出力プラグイン"""
    @abstractmethod
    def execute(self, df: FrameData) -> Result[None, Exception]:
        pass
```

### 3.3 Hook 仕様 (pluggy hookspec)

```python
import pluggy

hookspec = pluggy.HookspecMarker("cryoflow")

class CryoflowSpecs:
    @hookspec
    def register_input_plugins(self) -> list[InputPlugin]:
        """入力プラグインのインスタンスを返す"""

    @hookspec
    def register_transform_plugins(self) -> list[TransformPlugin]:
        """変換プラグインのインスタンスを返す"""

    @hookspec
    def register_output_plugins(self) -> list[OutputPlugin]:
        """出力プラグインのインスタンスを返す"""
```

### 3.4 パス解決の挙動

cryoflowの設定ファイルで指定される全てのファイルパスは、**カレントディレクトリではなく、設定ファイルが存在するディレクトリを基準として解決されます**。これにより、設定ファイルの移植性が向上し、プロジェクトディレクトリ全体を移動してもパス参照が壊れません。

#### 解決ルール

1. **絶対パス**: そのまま使用（`.resolve()`で正規化後）
2. **相対パス**: `config.toml`が存在するディレクトリを基準に解決

#### 設定ファイルのパス

**プラグインオプションのパス** (`input_plugins.options`、`output_plugins.options` など):
- プラグイン実装側で`BasePlugin.resolve_path()`を使用して解決する必要がある
- 例（InputPlugin）:
  ```toml
  [[input_plugins]]
  name = "parquet-scan"
  module = "cryoflow_plugin_collections.input.parquet_scan"
  [input_plugins.options]
  input_path = "data/input.parquet"
  # プラグイン内で: self.resolve_path(self.options['input_path'])
  # 解決結果: /project/config/data/input.parquet
  ```
- 例（OutputPlugin）:
  ```toml
  [[output_plugins]]
  name = "parquet-writer"
  module = "cryoflow_plugin_collections.output.parquet_writer"
  [output_plugins.options]
  output_path = "data/output.parquet"
  # プラグイン内で: self.resolve_path(self.options['output_path'])
  # 解決結果: /project/config/data/output.parquet
  ```

#### プラグイン実装

プラグインはコンストラクタで`config_dir`パラメータを受け取ります。これは設定ファイルのディレクトリに自動設定されます:

```python
class BasePlugin(ABC):
    def __init__(self, options: dict[str, Any], config_dir: Path | None = None) -> None:
        self.options = options
        self._config_dir = config_dir or Path.cwd()

    def resolve_path(self, path: str | Path) -> Path:
        """設定ファイルのディレクトリを基準にパスを解決する"""
        path = Path(path)
        if not path.is_absolute():
            path = self._config_dir / path
        return path.resolve()
```

プラグインでの使用例:
```python
class ParquetWriterPlugin(OutputPlugin):
    def execute(self, df: FrameData) -> Result[None, Exception]:
        output_path_opt = self.options.get('output_path')
        # 設定ファイルディレクトリを基準に相対パスを解決
        output_path = self.resolve_path(output_path_opt)
        # ... output_pathに書き込み
```

#### メリット

- **移植性**: 設定ファイルとデータを一つのユニットとして移動可能
- **一貫性**: 全てのパスが同じ解決ルールに従う
- **予測可能性**: パス解決がカレントディレクトリに依存しない

---

## 4. エラーハンドリング指針 (returns)

* 例外(`try-except`)の使用は、最下層のライブラリ境界（Polarsの呼び出し等）に限定する。
* プラグイン間のデータの受け渡しは `Result[FrameData, Exception]` でラップする。
* パイプライン制御部では `flow` や `bind` を使用し、一つでも `Failure` が返れば即座に処理を中断し、CLIのエラー出力へ回す。

```python
# イメージ
result = (
    load_data(path)
    .bind(plugin_a.execute)
    .bind(plugin_b.execute)
    .bind(output_plugin.execute)
)

if isinstance(result, Failure):
    console.print(f"[red]Error:[/red] {result.failure()}")
    raise typer.Exit(code=1)

```

---

## 5. プラグイン実装のベストプラクティス

### 5.1 エラーハンドリング

プラグインの`execute()`と`dry_run()`メソッドでは、以下のパターンを推奨します。

**パターン1: try-exceptで明示的にFailureを返す（推奨）**

```python
from returns.result import Failure, Success

def execute(self, df: FrameData) -> Result[FrameData, Exception]:
    try:
        column_name = self.options['column_name']
        if column_name not in df.columns:
            return Failure(ValueError(f"Column '{column_name}' not found"))
        # ... 処理 ...
        return Success(transformed_df)
    except Exception as e:
        return Failure(e)
```

**パターン2: @safeデコレータで自動変換**

```python
from returns.result import safe

@safe
def execute(self, df: FrameData) -> FrameData:
    column_name = self.options['column_name']
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found")
    # ... 処理 ...
    return transformed_df
```

いずれの場合も、**エラーメッセージには具体的な情報**（カラム名、期待値、実際値）を含めることが重要です。

### 5.2 dry_runメソッドの実装

`dry_run`メソッドは、実際のデータを処理せずにスキーマのみを検査して、処理後の予想スキーマを返します。

```python
def dry_run(self, schema: dict[str, pl.DataType]) -> Result[dict[str, pl.DataType], Exception]:
    """スキーマを検証し、処理後の予想スキーマを返す"""
    column_name = self.options['column_name']

    # カラム存在チェック
    if column_name not in schema:
        return Failure(ValueError(f"Column '{column_name}' not found in schema"))

    # 型チェック
    dtype = schema[column_name]
    if not dtype.is_numeric():
        return Failure(ValueError(
            f"Column '{column_name}' has type {dtype}, expected numeric type"
        ))

    # スキーマは変更されないため、そのまま返す
    return Success(schema)
```

### 5.3 リソース管理

- Polarsの`scan_*`/`sink_*`メソッドは自動的にファイルハンドラをクローズします
- カスタムOutputPluginを実装する場合、`with`文でファイルハンドラを管理してください

```python
class CustomOutputPlugin(OutputPlugin):
    def execute(self, df: FrameData) -> Result[None, Exception]:
        try:
            output_path = self.options['output_path']
            with open(output_path, 'w') as f:
                # ファイル処理
                pass
            return Success(None)
        except Exception as e:
            return Failure(e)
```

---

## 6. CLIコマンド

### 6.1 run コマンド

データ処理パイプラインを実行します。

```bash
cryoflow run [-c CONFIG] [-v]
```

**オプション**:
- `-c, --config CONFIG`: 設定ファイルのパス（指定されない場合はXDG準拠のデフォルトパスを使用）
- `-v, --verbose`: 詳細ログを出力（DEBUG レベルのログが表示される）

**出力例**:

```
Config loaded: /home/user/.config/cryoflow/config.toml
  input_plugins:     1 plugin(s)
  transform_plugins: 1 plugin(s)
  output_plugins:    1 plugin(s)
    - input_plugin (my.input) [enabled]
    - transform_plugin (my.transform) [enabled]
    - output_plugin (my.output) [enabled]
Loaded 3 plugin(s) successfully.

Executing pipeline...
INFO: Executing 1 transformation plugin(s)...
INFO:   [1/1] transform_plugin
[SUCCESS] Pipeline completed successfully
```

### 6.2 check コマンド

パイプライン設定とスキーマを検証します。実際のデータは処理されません。

```bash
cryoflow check [-c CONFIG] [-v]
```

**オプション**:
- `-c, --config CONFIG`: 設定ファイルのパス
- `-v, --verbose`: 詳細ログを出力

**出力例**:

```
[CHECK] Config loaded: /home/user/.config/cryoflow/config.toml
[CHECK] Loaded 2 plugin(s) successfully.

[CHECK] Running dry-run validation...

[SUCCESS] Validation completed successfully

Output schema:
  order_id: Int64
  customer_id: Int64
  total_amount: Float64
  order_date: Date
```

**用途**:

- 設定ファイルの構文チェック
- プラグインのロード可否確認
- スキーマ検証（変換後のカラム型を確認）
- 本実行前のプリフライト確認
