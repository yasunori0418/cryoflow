# 実装計画

プロジェクトを4つのフェーズに分割し、段階的に実装します。

## Phase 1: コア・フレームワーク構築 (CLI & Config)

**目標**: 設定ファイルを読み込み、Typerでコマンドが起動することを確認する。

1. **プロジェクトセットアップ**: Poetry/Rye 等で環境構築。
2. **Config実装**:
* `xdg-base-dirs` でパス取得。
* `config.toml` を作成し、Pydantic モデルにマッピング。


3. **Typer実装**:
* `cryoflow run` コマンドの実装。
* 設定ファイルの内容を表示するだけのモック実装。



## Phase 2: プラグイン機構の実装 (Pluggy & ABC)

**目標**: 外部ファイルに定義されたクラスをロードし、メソッドを呼び出せるようにする。

1. **HookSpec定義**: `pluggy` の仕様定義。
2. **Plugin Loader**:
* 設定ファイルの `module` パス文字列から `importlib` で動的インポート。
* クラスをインスタンス化し、`PluginManager` に登録。


3. **ABC実装**: `TransformPlugin`, `OutputPlugin` の基底クラス作成。
4. **テスト用プラグイン作成**: 何もしない（Identity）プラグインを作成し、ロードテスト。

## Phase 3: データ処理パイプライン実装 (Polars & Returns)

**目標**: 実際にParquetを読み込み、処理して保存できるようにする。

1. **LazyFrame統合**:
* コアロジックで `pl.scan_parquet` 等の実装。


2. **Pipeline Runner**:
* プラグインリストをループ（または `returns` のパイプライン機能）で繋ぐ。
* `execute` メソッドを順次実行。
* `Union[LazyFrame, DataFrame]` の型ハンドリング。


3. **Output実装**:
* 結果を評価 (`collect` / `sink_parquet`) するロジックの実装。



## Phase 4: Dry-Run と堅牢化

**目標**: 実データを流さずにスキーマ検証を行い、エラーハンドリングを完成させる。

1. **Dry-Run実装**:
* `cryoflow check` (または `run --dry-run`) コマンドの実装。
* 各プラグインの `dry_run` メソッドを連鎖させ、最終的な出力スキーマを表示。


2. **エラーハンドリング強化**:
* `returns` の `safe` デコレータ等を用いて、予期せぬ例外を `Failure` に変換。


3. **ロギング**: 処理ステップごとのログ出力を整備。

---

### 次のアクション

この仕様で進める場合、**Phase 1 & 2** の部分（Typerのガワ + `importlib`と`pluggy`でクラスベースのプラグインを読み込む最小構成）のコードを作成しましょうか？
そこが最も複雑な部分（「どうやって設定ファイルからクラスをロードするか」）になります。
