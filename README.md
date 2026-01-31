# cryoflow

Polars LazyFrame を中核とした、プラグイン駆動型の列指向データ処理CLIツール。

Apache Arrow (IPC/Parquet) 形式のデータを入力とし、ユーザー定義のプラグインチェーンを経てデータの加工・検証・出力を行います。

## 技術スタック

| カテゴリ | ライブラリ/技術 | 用途 |
| --- | --- | --- |
| Core | Polars | データ処理エンジン (LazyFrame主軸) |
| CLI | Typer | CLIインターフェース、コマンド定義 |
| Plugin | pluggy + importlib | プラグイン機構、フック管理、動的ロード |
| Config | Pydantic + TOML | 設定定義、バリデーション |
| Path | xdg-base-dirs | XDG準拠のコンフィグパス解決 |
| Error | returns | Result Monadによるエラーハンドリング |
| Base | ABC (Standard Lib) | プラグインインターフェース定義 |

## データフロー

1. **Config Load**: `XDG_CONFIG_HOME/cryoflow/config.toml` を読み込み、Pydantic で検証
2. **Plugin Discovery**: 設定ファイルに基づき、`importlib` で指定モジュールをロードし、`pluggy` に登録
3. **Pipeline Construction**: Source (Parquet/IPC) を `pl.scan_*` で LazyFrame 化し、`TransformPlugin` フックを順次実行して計算グラフを構築
4. **Execution / Output**: `OutputPlugin` フックを実行。ここで初めて `collect()` または `sink_*()` が呼ばれ、処理が実行される

## プラグインシステム

ABC による基底クラスを継承してプラグインを作成します。

- **TransformPlugin**: データ変換を行うプラグイン。`execute(df) -> Result[FrameData, Exception]` を実装
- **OutputPlugin**: データ出力を行うプラグイン。`execute(df) -> Result[None, Exception]` を実装

全てのプラグインは `dry_run` メソッドを持ち、実データを流さずにスキーマ検証が可能です。

## エラーハンドリング

`returns` ライブラリの `Result` 型を使用した鉄道指向プログラミングを採用しています。

- プラグイン間のデータ受け渡しは `Result[FrameData, Exception]` でラップ
- パイプライン制御では `flow` / `bind` を使用し、`Failure` 発生時に即座に処理を中断

## ドキュメント

- [仕様書](docs/spec.md)
- [実装計画](docs/implements_step_plan.md)
