"""cryoflow テスト用大規模サンプルデータ生成スクリプト

Polars を使用して 10万行規模の Parquet ファイルを生成する。
データ内容: 架空の工場における IoT センサー計測データ。
主キーは存在せず、順不同で重複タイムスタンプを含む。

Usage:
    uv run python examples/generate_sensor_data.py
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

OUTPUT_DIR = Path(__file__).parent / 'data'
NUM_ROWS = 100_000

# 乱数シード固定
RNG = np.random.default_rng(seed=12345)

# マスタ定義
FACILITY_IDS = [f'FAC-{c}' for c in 'ABCDE']
SENSOR_TYPES = ['temperature', 'humidity', 'pressure', 'vibration', 'voltage']
SENSOR_IDS = {
    'temperature': [f'TEMP-{i:03d}' for i in range(1, 21)],
    'humidity': [f'HUM-{i:03d}' for i in range(1, 16)],
    'pressure': [f'PRESS-{i:03d}' for i in range(1, 11)],
    'vibration': [f'VIB-{i:03d}' for i in range(1, 9)],
    'voltage': [f'VOLT-{i:03d}' for i in range(1, 13)],
}
UNIT_MAP = {
    'temperature': '°C',
    'humidity': '%',
    'pressure': 'hPa',
    'vibration': 'mm/s',
    'voltage': 'V',
}
STATUS_CHOICES = ['normal', 'normal', 'normal', 'normal', 'warning', 'error']


def generate_values(sensor_type: str, n: int) -> np.ndarray:
    """センサー種別ごとに現実的な計測値を生成する。"""
    match sensor_type:
        case 'temperature':
            return RNG.normal(loc=25.0, scale=5.0, size=n).round(2)
        case 'humidity':
            return np.clip(RNG.normal(loc=55.0, scale=15.0, size=n), 0, 100).round(1)
        case 'pressure':
            return RNG.normal(loc=1013.25, scale=5.0, size=n).round(2)
        case 'vibration':
            return np.abs(RNG.exponential(scale=1.5, size=n)).round(3)
        case 'voltage':
            return RNG.normal(loc=220.0, scale=3.0, size=n).round(2)
        case _:
            return RNG.standard_normal(size=n).round(2)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 各行のセンサー種別を先に決定
    sensor_types = RNG.choice(SENSOR_TYPES, size=NUM_ROWS)

    # センサー種別ごとのセンサーIDを選択
    sensor_ids = [RNG.choice(SENSOR_IDS[st]) for st in sensor_types]

    # 施設IDをランダム選択
    facility_ids = RNG.choice(FACILITY_IDS, size=NUM_ROWS)

    # タイムスタンプ: 2025-01-01 ~ 2025-06-30 の範囲でランダム (順不同)
    start_ts = datetime(2025, 1, 1).timestamp()
    end_ts = datetime(2025, 6, 30, 23, 59, 59).timestamp()
    timestamps = RNG.uniform(start_ts, end_ts, size=NUM_ROWS)
    timestamps_dt = [datetime.fromtimestamp(t) for t in timestamps]

    # センサー種別ごとの計測値を一括生成してからマッピング
    type_counts = {st: int((sensor_types == st).sum()) for st in SENSOR_TYPES}
    value_pools: dict[str, np.ndarray] = {}
    value_indices: dict[str, int] = {}
    for st in SENSOR_TYPES:
        value_pools[st] = generate_values(st, type_counts[st])
        value_indices[st] = 0

    values = np.empty(NUM_ROWS, dtype=np.float64)
    units = []
    for i, st in enumerate(sensor_types):
        idx = value_indices[st]
        values[i] = value_pools[st][idx]
        value_indices[st] = idx + 1
        units.append(UNIT_MAP[st])

    # ステータス
    statuses = RNG.choice(STATUS_CHOICES, size=NUM_ROWS)

    # 異常フラグ: warning/error の場合に True になりやすいがノイズもある
    is_anomaly = []
    for s in statuses:
        if s == 'error':
            is_anomaly.append(RNG.random() < 0.9)
        elif s == 'warning':
            is_anomaly.append(RNG.random() < 0.4)
        else:
            is_anomaly.append(RNG.random() < 0.01)

    # バッテリー残量 (0.0 ~ 100.0)
    battery_levels = np.clip(RNG.normal(loc=72.0, scale=20.0, size=NUM_ROWS), 0, 100).round(1)

    df = pl.DataFrame(
        {
            'timestamp': timestamps_dt,
            'facility_id': facility_ids.tolist(),
            'sensor_type': sensor_types.tolist(),
            'sensor_id': sensor_ids,
            'value': values.tolist(),
            'unit': units,
            'status': statuses.tolist(),
            'is_anomaly': is_anomaly,
            'battery_level': battery_levels.tolist(),
        }
    ).cast(
        {
            'timestamp': pl.Datetime('us'),
            'value': pl.Float64,
            'battery_level': pl.Float64,
            'is_anomaly': pl.Boolean,
        }
    )

    # 意図的に順序をシャッフル (乱数シードで再現可能)
    shuffle_idx = RNG.permutation(NUM_ROWS)
    df = df.with_row_index('__idx').filter(pl.col('__idx').is_in(shuffle_idx.tolist())).sort('__idx').drop('__idx')
    # polars の permutation 相当: sample で全行シャッフル
    df = df.sample(fraction=1.0, seed=12345, shuffle=True)

    output_path = OUTPUT_DIR / 'sensor_readings.parquet'
    df.write_parquet(output_path, compression='snappy')

    print(f'Parquet: {output_path}')
    print(f'Size:    {output_path.stat().st_size / (1024 * 1024):.2f} MB')
    print(f'Rows:    {df.height}')
    print(f'Columns: {df.width}')
    print('\nSchema:')
    for name, dtype in df.schema.items():
        print(f'  {name}: {dtype}')
    print('\nPreview (first 10 rows):')
    print(df.head(10))
    print('\nSensor type distribution:')
    print(df.group_by('sensor_type').len().sort('sensor_type'))
    print('\nStatus distribution:')
    print(df.group_by('status').len().sort('status'))


if __name__ == '__main__':
    main()
