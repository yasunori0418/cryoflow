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
from pydantic import BaseModel, Field, FilePath
from typing import List, Dict, Any, Optional

class PluginConfig(BaseModel):
    name: str
    module: str  # importlibで読み込むパス
    enabled: bool = True
    options: Dict[str, Any] = Field(default_factory=dict) # プラグイン固有設定

class GlobalConfig(BaseModel):
    input_path: FilePath
    output_target: str
    plugins: List[PluginConfig]

```

### 3.2 プラグイン基底クラス (ABC)

`pluggy` は関数ベースのフックも扱えますが、ABCによる契約と `dry_run` の強制のため、クラスベースのプラグイン設計とします。

```python
from abc import ABC, abstractmethod
from typing import Union
import polars as pl
from returns.result import Result

# データ型エイリアス
FrameData = Union[pl.LazyFrame, pl.DataFrame]

class BasePlugin(ABC):
    """全てのプラグインの基底クラス"""
    def __init__(self, options: Dict[str, Any]):
        self.options = options

    @abstractmethod
    def name(self) -> str:
        """プラグイン識別名"""
        pass

    @abstractmethod
    def dry_run(self, schema: Dict[str, pl.DataType]) -> Result[Dict[str, pl.DataType], Exception]:
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

class cryoflowSpecs:
    @hookspec
    def register_transform_plugins(self) -> List[TransformPlugin]:
        """変換プラグインのインスタンスを返す"""

    @hookspec
    def register_output_plugins(self) -> List[OutputPlugin]:
        """出力プラグインのインスタンスを返す"""

```

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
