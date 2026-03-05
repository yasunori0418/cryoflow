# CLAUDE.md

## プロジェクト概要

Polars LazyFrame を中核とした、プラグイン駆動型の列指向データ処理CLIツール。
技術スタック: Polars / Typer / pluggy+importlib / Pydantic+TOML / xdg-base-dirs / returns / ABC

## アーキテクチャ原則

### データフロー

Config Load -> Plugin Discovery -> Pipeline Construction -> Execution / Output

1. `XDG_CONFIG_HOME/cryoflow/config.toml` や指定された設定ファイルを`Pydantic`で検証して読み込み
2. `importlib` で指定モジュールをロードし `pluggy` に登録
3. InputPlugin フックによって読み込んだデータをLazyFrameやDataFrameとして扱う
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

## コーディング規約

- `pyright` による静的型解析 + `ruff` によるフォーマット/リントを必ず通す
- ドキュメント・テストコード・プロダクトコード全てで型アノテーションは必須（`Any` 型は原則禁止）

## Git規約・ドキュメント規約

- コミットメッセージは英語 + Conventional Commits 形式
- ドキュメントは日本語版（`{filename}_ja.md`）が主軸、英語版（`{filename}.md`）は追従して更新
- 詳細は `CONTRIBUTING_ja.md` を参照
