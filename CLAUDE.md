# CLAUDE.md

cryoflow プロジェクトにおける Claude Code への指示書。

## プロジェクト概要

Polars LazyFrame を中核とした、プラグイン駆動型の列指向データ処理CLIツール。
Apache Arrow (IPC/Parquet) 形式のデータを入力とし、ユーザー定義のプラグインチェーンを経てデータの加工・検証・出力を行う。

## 技術スタック

- **データ処理**: Polars (LazyFrame主軸)
- **CLI**: Typer
- **プラグイン機構**: pluggy + importlib (動的ロード)
- **設定管理**: Pydantic + TOML
- **パス解決**: xdg-base-dirs (XDG準拠)
- **エラーハンドリング**: returns (Result Monad / 鉄道指向プログラミング)
- **プラグインインターフェース**: ABC (標準ライブラリ)

## アーキテクチャ原則

### データフロー

Config Load -> Plugin Discovery -> Pipeline Construction -> Execution / Output

1. `XDG_CONFIG_HOME/cryoflow/config.toml` を Pydantic で検証して読み込み
2. `importlib` で指定モジュールをロードし `pluggy` に登録
3. `pl.scan_*` で LazyFrame 化し、TransformPlugin フックで計算グラフを構築
4. OutputPlugin フックで `collect()` / `sink_*()` を実行

### エラーハンドリング規約

- `try-except` はライブラリ境界（Polars呼び出し等）の最下層のみ
- プラグイン間データは `Result[FrameData, Exception]` でラップ
- パイプライン制御は `flow` / `bind` で連鎖させ、`Failure` で即中断
- 予期せぬ例外は `returns` の `safe` デコレータで `Failure` に変換

### プラグイン設計

- クラスベース: ABC による基底クラス (`BasePlugin`, `TransformPlugin`, `OutputPlugin`)
- 全プラグインに `dry_run` メソッドを強制（スキーマ検証用）
- pluggy の hookspec でプラグイン登録を管理

### 型定義

- `FrameData = Union[pl.LazyFrame, pl.DataFrame]`
- プラグインの execute は `Result[FrameData, Exception]` を返す
- OutputPlugin の execute は `Result[None, Exception]` を返す

## 実装フェーズ

現在の実装計画は4フェーズで構成:

1. **Phase 1**: コア・フレームワーク構築 (CLI & Config)
2. **Phase 2**: プラグイン機構の実装 (Pluggy & ABC)
3. **Phase 3**: データ処理パイプライン実装 (Polars & Returns)
4. **Phase 4**: Dry-Run と堅牢化

詳細は `docs/implements_step_plan.md` を参照。

## Git規約

- コミットメッセージは英語で記述する

## ドキュメント

- `docs/spec.md`: 仕様書（インターフェース設計、データモデル、Hook仕様を含む）
- `docs/implements_step_plan.md`: 実装計画
