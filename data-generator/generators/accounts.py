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
