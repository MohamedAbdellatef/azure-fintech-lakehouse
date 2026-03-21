"""
Accounts Generator
Generates wallet/account data for each user
"""
from config import config
import pandas as pd
import numpy as np
from faker import Faker
import random
import uuid
from datetime import datetime
from generators.io_utils import save_dataframe


def _sample_indices(df: pd.DataFrame, rate: float, seed_offset: int, eligible_idx=None) -> pd.Index:
    idx = df.index if eligible_idx is None else pd.Index(eligible_idx)
    if rate <= 0 or len(idx) == 0:
        return pd.Index([])

    sample_size = max(1, int(len(idx) * rate))
    sample_size = min(sample_size, len(idx))
    return df.loc[idx].sample(n=sample_size, random_state=config.RANDOM_SEED + seed_offset).index


def generate_accounts(users_df: pd.DataFrame, output_dir: str = None) -> pd.DataFrame:
    """
    Generate account/wallet data - each user gets 1-2 accounts

    Args:
        users_df: DataFrame with user data (need user_id and country)
        output_dir: Output directory

    Returns:
        DataFrame with account data
    """
    out_dir = output_dir or config.OUTPUT_DIR

    fake = Faker()
    Faker.seed(config.RANDOM_SEED + 2)
    random.seed(config.RANDOM_SEED + 2)

    print(f"Generating Accounts (1-2 per user)...")

    accounts = []

    for idx, user in users_df.iterrows():
        user_id = user['user_id']
        country = user.get('country', 'EG')
        currency = config.CURRENCY_MAP.get(country, 'USD')
        reg_date = user.get('registration_date', datetime.now())

        # Everyone gets a main wallet
        accounts.append({
            "account_id": str(uuid.uuid4()),
            "user_id": user_id,
            "account_type": "Wallet",
            "currency": currency,
            "balance": round(random.uniform(0, 25000), 2),
            "daily_limit": random.choice([5000, 10000, 25000, 50000]),
            "monthly_limit": random.choice([50000, 100000, 250000]),
            "status": "active",
            "created_at": reg_date,
            "updated_at": fake.date_time_between(start_date=reg_date, end_date='now')
        })

        # 25% of users have a secondary savings account
        if random.random() < 0.25:
            accounts.append({
                "account_id": str(uuid.uuid4()),
                "user_id": user_id,
                "account_type": "Savings",
                "currency": currency,
                "balance": round(random.uniform(1000, 100000), 2),
                "daily_limit": random.choice([10000, 25000, 50000]),
                "monthly_limit": random.choice([100000, 250000, 500000]),
                "status": random.choices(["active", "frozen"], weights=[0.92, 0.08])[0],
                "created_at": reg_date,
                "updated_at": fake.date_time_between(start_date=reg_date, end_date='now')
            })

        # Progress
        if (idx + 1) % 10000 == 0:
            print(f"   -> {idx + 1:,} users processed...")

    df = pd.DataFrame(accounts)

    null_account_idx = _sample_indices(df, config.NULL_ACCOUNT_ID_RATE, 210)
    df.loc[null_account_idx, "account_id"] = None

    duplicate_idx = _sample_indices(
        df,
        config.DUPLICATE_ACCOUNT_ID_RATE,
        211,
        eligible_idx=df.index.difference(null_account_idx),
    )
    duplicate_donor_idx = _sample_indices(
        df,
        config.DUPLICATE_ACCOUNT_ID_RATE,
        212,
        eligible_idx=df.index.difference(duplicate_idx).difference(null_account_idx),
    )
    if len(duplicate_idx) > 0 and len(duplicate_donor_idx) > 0:
        donor_ids = df.loc[duplicate_donor_idx, "account_id"].tolist()
        if len(donor_ids) < len(duplicate_idx):
            donor_ids = (donor_ids * ((len(duplicate_idx) // len(donor_ids)) + 1))[:len(duplicate_idx)]
        df.loc[duplicate_idx, "account_id"] = donor_ids[:len(duplicate_idx)]

    orphan_user_idx = _sample_indices(df, config.ORPHAN_ACCOUNT_USER_RATE, 213)
    df.loc[orphan_user_idx, "user_id"] = [str(uuid.uuid4()) for _ in range(len(orphan_user_idx))]

    negative_balance_idx = _sample_indices(df, config.NEGATIVE_BALANCE_RATE, 214)
    df.loc[negative_balance_idx, "balance"] = -df.loc[negative_balance_idx, "balance"].abs()

    invalid_currency_idx = _sample_indices(df, config.INVALID_ACCOUNT_CURRENCY_RATE, 215)
    df.loc[invalid_currency_idx, "currency"] = "USD"

    invalid_status_idx = _sample_indices(df, config.INVALID_ACCOUNT_STATUS_RATE, 216)
    df.loc[invalid_status_idx, "status"] = "suspended"

    invalid_type_idx = _sample_indices(df, config.INVALID_ACCOUNT_TYPE_RATE, 217)
    df.loc[invalid_type_idx, "account_type"] = "Checking"

    filepath = save_dataframe(
        df=df,
        out_dir=out_dir,
        base_name="accounts",
        output_format=config.OUTPUT_FORMAT
    )
    print(f"   OK Generated {len(df):,} accounts -> {filepath}")

    return df


if __name__ == "__main__":
    # Test with mock users
    from generators.users import generate_users
    users = generate_users(num_users=100, output_dir="test_data")
    accounts = generate_accounts(users, output_dir="test_data")
    print(f"\nSample:\n{accounts.head()}")
