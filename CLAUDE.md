# CLAUDE.md

## プロジェクト概要

Polars LazyFrame を中核とした、プラグイン駆動型の列指向データ処理CLIツール。
ユーザー定義のプラグインチェーンを経てデータの入力・加工・検証・出力を行う。

## 技術スタック

- **データ処理**: Polars (LazyFrame主軸)
- **CLI**: Typer
- **プラグイン機構**: pluggy + importlib (動的ロード)
- **設定管理**: Pydantic + TOML
- **パス解決**: xdg-base-dirs (XDG準拠) / pathlib.Path (標準ライブラリ)
- **エラーハンドリング**: returns (Result Monad / 鉄道指向プログラミング)
- **プラグインインターフェース**: ABC (標準ライブラリ)

## アーキテクチャ原則

### データフロー

Config Load -> Plugin Discovery -> Pipeline Construction -> Execution / Output

1. `XDG_CONFIG_HOME/cryoflow/config.toml` や指定された設定ファイルを`Pydantic`で検証して読み込み
2. `importlib` で指定モジュールをロードし `pluggy` に登録
3. InputPlugin フックによって読み込んだデータをLazyFrameやDataFrmaeとして扱う
4. TransformPlugin フックで計算グラフを構築
5. OutputPlugin フックで `collect()` / `sink_*()` を実行

### エラーハンドリング規約

- 可能な限り`returns`のResult型を使い、メソッドチェーンしながら処理を一連化していく
- 予期せぬ例外は `returns` の `safe` デコレータで `Failure` に変換

### プラグイン設計

- クラスベース: ABC による基底クラス (`BasePlugin`, `InputPlugin`, `TransformPlugin`, `OutputPlugin`)
- 全プラグインに `dry_run` メソッドを強制（スキーマ検証用）
- pluggy の hookspec でプラグイン登録を管理

### 型定義

- `FrameData = Union[pl.LazyFrame, pl.DataFrame]`
- プラグインの execute は `Result[FrameData, Exception]` を返す
- OutputPlugin の execute は `Result[None, Exception]` を返す

## Git規約

- コミットメッセージは英語で記述する

## ドキュメント

- `docs/spec.md`: 仕様書（インターフェース設計、データモデル、Hook仕様を含む）
- `docs/implements_step_plan.md`: 実装計画

日本語版のドキュメント: `{filename}_ja.md`
英語版のドキュメント: `{filename}.md`
主軸となるドキュメントは日本語版。
英語版は日本語版変更後に追従する形で更新。

## コーディング規約

- `pyright`の静的な型解析を有効活用
- コードフォーマットは`ruff`の規約を守ること
- ドキュメント・テストコード・プロダクトコードの全てにおいて、pythonの型アノテーションは必須である。
    - テストの関係などではない限り、`Any`型は使わないこと
