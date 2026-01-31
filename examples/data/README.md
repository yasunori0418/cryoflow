# サンプルデータ

cryoflow の動作確認・テスト用サンプルデータ。

## ファイル一覧

| ファイル | 形式 | 説明 |
|---------|------|------|
| `sample_sales.parquet` | Apache Parquet | 販売トランザクションデータ (Parquet) |
| `sample_sales.ipc` | Apache Arrow IPC | 販売トランザクションデータ (IPC/Feather) |

両ファイルは同一データを異なる形式で保存したものです。

## データ概要

架空の EC サイトにおける販売トランザクションデータ。50件のレコードを含みます。

- **期間**: 2025-01-01 〜 2025-06-30
- **地域**: 日本国内 8 地域
- **カテゴリ**: 5 種類 (電子機器、書籍、食品、衣料品、日用品)
- **レコード数**: 50 件

## スキーマ

| カラム名 | 型 | 説明 |
|---------|-----|------|
| `order_id` | String | 注文ID (`ORD-0001` 形式) |
| `order_date` | Date | 注文日 |
| `region` | String | 地域 (北海道, 東北, 関東, 中部, 近畿, 中国, 四国, 九州) |
| `category` | String | 商品カテゴリ |
| `product_name` | String | 商品名 |
| `unit_price` | Int64 | 単価 (円) |
| `quantity` | Int32 | 数量 |
| `discount_rate` | Float64 | 割引率 (0.0 〜 0.20) |
| `discount_amount` | Int64 | 割引額 (円) |
| `total_amount` | Int64 | 合計金額 (円)。`unit_price * quantity - discount_amount` |
| `payment_method` | String | 支払方法 (クレジットカード, 電子マネー, 現金, 銀行振込) |
| `is_returned` | Boolean | 返品フラグ (約5%の確率で `true`) |

## 再生成

データは `examples/generate_sample_data.py` で生成されています。乱数シードが固定 (`seed=42`) のため、再実行しても同一データが生成されます。

```bash
uv run python examples/generate_sample_data.py
```

## cryoflow での使用例

`examples/config.toml` の `input_path` を変更して使用します。

```toml
# Parquet 形式
input_path = "examples/data/sample_sales.parquet"

# IPC 形式
input_path = "examples/data/sample_sales.ipc"
```
