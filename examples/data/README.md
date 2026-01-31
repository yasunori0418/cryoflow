# サンプルデータ

cryoflow の動作確認・テスト用サンプルデータ。

## ファイル一覧

| ファイル | 形式 | 行数 | サイズ | 説明 |
|---------|------|------|--------|------|
| `sample_sales.parquet` | Parquet | 50 | ~6 KB | 販売トランザクションデータ |
| `sample_sales.ipc` | Arrow IPC | 50 | ~9 KB | 販売トランザクションデータ (IPC版) |
| `sensor_readings.parquet` | Parquet | 100,000 | ~1.7 MB | IoT センサー計測データ (大規模) |

## 生成スクリプト

各データファイルは専用の生成スクリプトで作成されています。乱数シードが固定されているため、再実行しても同一データが生成されます。

```bash
# 販売データ (sample_sales.parquet / sample_sales.ipc)
uv run python examples/generate_sample_data.py

# センサーデータ (sensor_readings.parquet)
uv run python examples/generate_sensor_data.py
```

---

## sample_sales (販売トランザクションデータ)

架空の EC サイトにおける販売トランザクションデータ。`sample_sales.parquet` と `sample_sales.ipc` は同一データを異なる形式で保存したもの。

### 概要

- **期間**: 2025-01-01 〜 2025-06-30
- **地域**: 日本国内 8 地域
- **カテゴリ**: 5 種類 (電子機器、書籍、食品、衣料品、日用品)
- **レコード数**: 50 件

### スキーマ

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

---

## sensor_readings (IoT センサー計測データ)

架空の工場に設置された IoT センサー群から収集された計測データ。主キーは存在せず、タイムスタンプの重複や順不同のレコードを含む。`pl.scan_parquet()` による LazyFrame 読み込みを想定した大規模データ。

### 概要

- **期間**: 2025-01-01 〜 2025-06-30
- **施設**: 5 拠点 (FAC-A 〜 FAC-E)
- **センサー種別**: 5 種類 (temperature, humidity, pressure, vibration, voltage)
- **センサー数**: 67 台 (種別ごとに 8〜20 台)
- **レコード数**: 100,000 件
- **主キー**: なし (順不同、タイムスタンプ重複あり)

### スキーマ

| カラム名 | 型 | 説明 |
|---------|-----|------|
| `timestamp` | Datetime(μs) | 計測日時 (マイクロ秒精度、順不同) |
| `facility_id` | String | 施設ID (`FAC-A` 〜 `FAC-E`) |
| `sensor_type` | String | センサー種別 (temperature, humidity, pressure, vibration, voltage) |
| `sensor_id` | String | センサーID (種別プレフィックス + 連番) |
| `value` | Float64 | 計測値 (センサー種別ごとに現実的な分布) |
| `unit` | String | 計測単位 (°C, %, hPa, mm/s, V) |
| `status` | String | ステータス (normal ~67%, warning ~17%, error ~17%) |
| `is_anomaly` | Boolean | 異常フラグ (error時90%, warning時40%, normal時1%の確率で `true`) |
| `battery_level` | Float64 | バッテリー残量 (0.0 〜 100.0%) |

### 計測値の分布

| センサー種別 | 分布 | 代表値 |
|-------------|------|--------|
| temperature | 正規分布 (μ=25.0, σ=5.0) | 約 10〜40 °C |
| humidity | 正規分布 (μ=55.0, σ=15.0)、0〜100 にクランプ | 約 10〜100 % |
| pressure | 正規分布 (μ=1013.25, σ=5.0) | 約 998〜1028 hPa |
| vibration | 指数分布 (λ=1/1.5) の絶対値 | 0〜約 10 mm/s |
| voltage | 正規分布 (μ=220.0, σ=3.0) | 約 211〜229 V |

---

## cryoflow での使用例

`examples/config.toml` の `input_path` を変更して使用します。

```toml
# 販売データ (Parquet)
input_path = "examples/data/sample_sales.parquet"

# 販売データ (IPC)
input_path = "examples/data/sample_sales.ipc"

# センサーデータ (大規模 Parquet)
input_path = "examples/data/sensor_readings.parquet"
```
