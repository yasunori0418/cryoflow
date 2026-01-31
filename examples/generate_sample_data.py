"""cryoflow テスト用サンプルデータ生成スクリプト

Polars を使用して Parquet / IPC 形式のサンプルデータを生成する。
データ内容: 架空の販売トランザクションデータ (50件)

Usage:
    uv run python examples/generate_sample_data.py
"""

from datetime import date, timedelta
from pathlib import Path
import random

import polars as pl

random.seed(42)

OUTPUT_DIR = Path(__file__).parent / "data"

# マスタデータ定義
REGIONS = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州"]
CATEGORIES = ["電子機器", "書籍", "食品", "衣料品", "日用品"]
PRODUCTS = {
    "電子機器": ["ノートPC", "モニター", "キーボード", "マウス", "USBハブ"],
    "書籍": ["技術書", "小説", "雑誌", "辞書", "漫画"],
    "食品": ["コーヒー豆", "紅茶", "チョコレート", "ナッツ", "ドライフルーツ"],
    "衣料品": ["Tシャツ", "パーカー", "ジーンズ", "スニーカー", "帽子"],
    "日用品": ["洗剤", "歯ブラシ", "タオル", "石鹸", "シャンプー"],
}
PRICE_RANGE = {
    "電子機器": (5000, 150000),
    "書籍": (500, 5000),
    "食品": (300, 3000),
    "衣料品": (1000, 15000),
    "日用品": (100, 2000),
}
PAYMENT_METHODS = ["クレジットカード", "電子マネー", "現金", "銀行振込"]

NUM_ROWS = 50
BASE_DATE = date(2025, 1, 1)


def generate_records() -> list[dict]:
    records = []
    for i in range(1, NUM_ROWS + 1):
        category = random.choice(CATEGORIES)
        product = random.choice(PRODUCTS[category])
        low, high = PRICE_RANGE[category]
        unit_price = random.randint(low // 100, high // 100) * 100
        quantity = random.randint(1, 10)
        discount_rate = random.choice([0.0, 0.0, 0.0, 0.05, 0.10, 0.15, 0.20])
        subtotal = unit_price * quantity
        discount_amount = int(subtotal * discount_rate)
        total = subtotal - discount_amount

        records.append(
            {
                "order_id": f"ORD-{i:04d}",
                "order_date": BASE_DATE + timedelta(days=random.randint(0, 180)),
                "region": random.choice(REGIONS),
                "category": category,
                "product_name": product,
                "unit_price": unit_price,
                "quantity": quantity,
                "discount_rate": discount_rate,
                "discount_amount": discount_amount,
                "total_amount": total,
                "payment_method": random.choice(PAYMENT_METHODS),
                "is_returned": random.random() < 0.05,
            }
        )
    return records


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    records = generate_records()
    df = pl.DataFrame(records)

    # スキーマを明示的に整理
    df = df.cast(
        {
            "unit_price": pl.Int64,
            "quantity": pl.Int32,
            "discount_rate": pl.Float64,
            "discount_amount": pl.Int64,
            "total_amount": pl.Int64,
            "is_returned": pl.Boolean,
        }
    )

    parquet_path = OUTPUT_DIR / "sample_sales.parquet"
    ipc_path = OUTPUT_DIR / "sample_sales.ipc"

    df.write_parquet(parquet_path)
    print(f"Parquet: {parquet_path}")

    df.write_ipc(ipc_path)
    print(f"IPC:     {ipc_path}")

    print(f"\nRows: {df.height}, Columns: {df.width}")
    print(f"\nSchema:")
    for name, dtype in df.schema.items():
        print(f"  {name}: {dtype}")
    print(f"\nPreview (first 5 rows):")
    print(df.head(5))


if __name__ == "__main__":
    main()
