"""
Devices Generator
Generates device/session data for fraud detection scenarios
"""
from config import config
import pandas as pd
import numpy as np
from faker import Faker
import random
import uuid
import hashlib
from datetime import datetime
from generators.io_utils import save_dataframe


def _sample_indices(df: pd.DataFrame, rate: float, seed_offset: int, eligible_idx=None) -> pd.Index:
    idx = df.index if eligible_idx is None else pd.Index(eligible_idx)
    if rate <= 0 or len(idx) == 0:
        return pd.Index([])

    sample_size = max(1, int(len(idx) * rate))
    sample_size = min(sample_size, len(idx))
    return df.loc[idx].sample(n=sample_size, random_state=config.RANDOM_SEED + seed_offset).index


def generate_device_fingerprint() -> str:
    """Generate a realistic device fingerprint hash"""
    components = [
        str(uuid.uuid4()),
        str(random.randint(1000, 9999)),
        random.choice(['iPhone', 'Samsung', 'Huawei',
                      'Xiaomi', 'Chrome', 'Safari'])
    ]
    return hashlib.md5(''.join(components).encode()).hexdigest()[:24]


def generate_devices(users_df: pd.DataFrame, output_dir: str = None) -> pd.DataFrame:
    """
    Generate device data - each user has 1-3 devices
    Important for fraud detection (new device = risk signal)

    Args:
        users_df: DataFrame with user data
        output_dir: Output directory

    Returns:
        DataFrame with device data
    """
    out_dir = output_dir or config.OUTPUT_DIR

    fake = Faker()
    Faker.seed(config.RANDOM_SEED + 3)
    random.seed(config.RANDOM_SEED + 3)

    print(f"Generating Devices (1-3 per user)...")

    devices = []

    ios_models = ['iPhone 12', 'iPhone 13',
                  'iPhone 14', 'iPhone 15', 'iPhone SE']
    android_models = ['Samsung Galaxy S21', 'Samsung Galaxy S22',
                      'Huawei P40', 'Xiaomi Mi 11', 'OnePlus 9']

    for idx, user in users_df.iterrows():
        user_id = user['user_id']
        reg_date = user.get('registration_date', datetime.now())

        # Each user has 1-3 devices
        num_devices = random.choices([1, 2, 3], weights=[0.50, 0.35, 0.15])[0]

        for d in range(num_devices):
            device_type = random.choices(
                config.DEVICE_TYPES,
                weights=config.DEVICE_WEIGHTS
            )[0]

            if device_type == 'ios':
                model = random.choice(ios_models)
                os_version = f"iOS {random.randint(14, 17)}.{random.randint(0, 5)}"
            elif device_type == 'android':
                model = random.choice(android_models)
                os_version = f"Android {random.randint(11, 14)}"
            else:  # web
                browser = random.choice(
                    ['Chrome', 'Safari', 'Firefox', 'Edge'])
                browser_versions = {
                    'Chrome': f"Chrome {random.randint(110, 124)}",
                    'Safari': f"Safari {random.randint(16, 18)}.{random.randint(0, 5)}",
                    'Firefox': f"Firefox {random.randint(110, 125)}",
                    'Edge': f"Edge {random.randint(110, 124)}"
                }
                model = browser
                os_version = browser_versions[browser]

            first_seen = fake.date_time_between(
                start_date=reg_date, end_date='now')

            devices.append({
                "device_id": str(uuid.uuid4()),
                "user_id": user_id,
                "device_type": device_type,
                "device_model": model,
                "os_version": os_version,
                "app_version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 20)}",
                "device_fingerprint": generate_device_fingerprint(),
                "is_trusted": random.choices([True, False], weights=[0.85, 0.15])[0],
                "first_seen_at": first_seen,
                "last_seen_at": fake.date_time_between(start_date=first_seen, end_date='now'),
                "created_at": first_seen
            })

        if (idx + 1) % 10000 == 0:
            print(f"   -> {idx + 1:,} users processed...")

    df = pd.DataFrame(devices)

    null_device_idx = _sample_indices(df, config.NULL_DEVICE_ID_RATE, 310)
    df.loc[null_device_idx, "device_id"] = None

    invalid_type_idx = _sample_indices(df, config.INVALID_DEVICE_TYPE_RATE, 311)
    df.loc[invalid_type_idx, "device_type"] = "tablet"

    orphan_user_idx = _sample_indices(df, config.ORPHAN_DEVICE_USER_RATE, 312)
    df.loc[orphan_user_idx, "user_id"] = [str(uuid.uuid4()) for _ in range(len(orphan_user_idx))]

    invalid_time_idx = _sample_indices(df, config.INVALID_DEVICE_TIME_ORDER_RATE, 313)
    for idx in invalid_time_idx:
        first_seen = pd.to_datetime(df.at[idx, "first_seen_at"])
        df.at[idx, "last_seen_at"] = first_seen - pd.Timedelta(hours=1)

    filepath = save_dataframe(
        df=df,
        out_dir=out_dir,
        base_name="devices",
        output_format=config.OUTPUT_FORMAT
    )
    print(f"   OK Generated {len(df):,} devices -> {filepath}")

    return df


if __name__ == "__main__":
    from generators.users import generate_users
    users = generate_users(num_users=100, output_dir="test_data")
    devices = generate_devices(users, output_dir="test_data")
    print(f"\nSample:\n{devices.head()}")
