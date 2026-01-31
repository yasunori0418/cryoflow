# 進捗管理

## 全体ステータス

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | コア・フレームワーク構築 (CLI & Config) | ✅ 完了 |
| Phase 2 | プラグイン機構の実装 (Pluggy & ABC) | ⬜ 未着手 |
| Phase 3 | データ処理パイプライン実装 (Polars & Returns) | ⬜ 未着手 |
| Phase 4 | Dry-Run と堅牢化 | ⬜ 未着手 |

---

## Phase 1: コア・フレームワーク構築 ✅

### 実装済みファイル

| ファイル | 操作 | 状態 |
|---------|------|------|
| `packages/cryoflow-core/pyproject.toml` | 編集 | ✅ pydantic, xdg-base-dirs 依存追加 |
| `packages/cryoflow-core/cryoflow_core/__init__.py` | 編集 | ✅ docstring追加 |
| `packages/cryoflow-core/cryoflow_core/config.py` | 新規 | ✅ Pydanticモデル + 設定ローダー |
| `packages/cryoflow-core/cryoflow_core/cli.py` | 新規 | ✅ Typer CLIアプリ (run コマンド) |
| `pyproject.toml` (ルート) | 編集 | ✅ `[project.scripts]` エントリポイント追加 |
| `examples/config.toml` | 新規 | ✅ サンプル設定ファイル |

### 検証結果

| コマンド | 結果 |
|---------|------|
| `uv sync` | ✅ 依存インストール成功 |
| `uv run cryoflow --help` | ✅ ヘルプ表示、`run` コマンド表示 |
| `uv run cryoflow run --help` | ✅ `--config` / `-c` オプション表示 |
| `uv run cryoflow run -c examples/config.toml` | ✅ 設定内容の正常表示 |
| `uv run cryoflow run` (デフォルトパス未存在) | ✅ エラーメッセージ + exit code 1 |
| `uv run cryoflow run -c nonexistent.toml` | ✅ Typer組込みエラー + exit code 2 |

### 仕様書との差分

- `GlobalConfig` → `CryoflowConfig` にリネーム（より明確な名前）
- `input_path` の型を `FilePath` → `Path` に変更（ファイル存在チェックを設定ロード時に強制しないため）

---

## Phase 2: プラグイン機構の実装 ⬜

### 予定ファイル

| ファイル | 操作 | 状態 | 内容 |
|---------|------|------|------|
| `packages/cryoflow-core/pyproject.toml` | 編集 | ⬜ | pluggy, returns 依存追加 |
| `packages/cryoflow-core/cryoflow_core/plugin.py` | 新規 | ⬜ | ABC基底クラス (BasePlugin, TransformPlugin, OutputPlugin) |
| `packages/cryoflow-core/cryoflow_core/hookspecs.py` | 新規 | ⬜ | pluggy HookSpec定義 |
| `packages/cryoflow-core/cryoflow_core/loader.py` | 新規 | ⬜ | importlib動的ロード + PluginManager |
| `packages/cryoflow-sample-plugin/pyproject.toml` | 編集 | ⬜ | cryoflow-core, polars 依存追加 |
| `packages/cryoflow-sample-plugin/cryoflow_sample_plugin/transform.py` | 新規 | ⬜ | Identityプラグイン |

---

## Phase 3: データ処理パイプライン実装 ⬜

### 予定ファイル

| ファイル | 操作 | 状態 | 内容 |
|---------|------|------|------|
| `packages/cryoflow-core/cryoflow_core/pipeline.py` | 新規 | ⬜ | パイプラインランナー (scan + transform chain + output) |
| `packages/cryoflow-core/cryoflow_core/cli.py` | 編集 | ⬜ | モック → パイプライン実行に切り替え |

---

## Phase 4: Dry-Run と堅牢化 ⬜

### 予定ファイル

| ファイル | 操作 | 状態 | 内容 |
|---------|------|------|------|
| `packages/cryoflow-core/cryoflow_core/cli.py` | 編集 | ⬜ | `check` コマンド追加 |

---

## プロジェクト構造 (現在)

```
cryoflow/
├── pyproject.toml                  # ルートパッケージ (エントリポイント定義)
├── uv.lock
├── cryoflow/
│   └── __init__.py
├── packages/
│   ├── cryoflow-core/
│   │   ├── pyproject.toml          # typer, pydantic, xdg-base-dirs
│   │   └── cryoflow_core/
│   │       ├── __init__.py
│   │       ├── cli.py              # Typer CLIアプリ
│   │       └── config.py           # Pydanticモデル + 設定ローダー
│   └── cryoflow-sample-plugin/
│       ├── pyproject.toml
│       └── cryoflow_sample_plugin/
│           └── __init__.py
├── examples/
│   └── config.toml                 # サンプル設定ファイル
├── docs/
│   ├── spec.md                     # 仕様書
│   ├── implements_step_plan.md     # 実装計画
│   └── progress.md                 # 進捗管理 (本ファイル)
└── dev/
    ├── flake.nix
    └── flake.lock
```
