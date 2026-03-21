"""
Payment Methods Generator
Generates linked cards/bank accounts for users
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


def generate_payment_methods(users_df: pd.DataFrame, output_dir: str = None) -> pd.DataFrame:
    """
    Generate payment methods (cards, bank accounts) for users
    Each user has 1-3 payment methods

    Args:
        users_df: DataFrame with user data
        output_dir: Output directory

    Returns:
        DataFrame with payment method data
    """
    out_dir = output_dir or config.OUTPUT_DIR

    fake = Faker()
    Faker.seed(config.RANDOM_SEED + 5)
    random.seed(config.RANDOM_SEED + 5)

    print(f"Generating Payment Methods (1-3 per user)...")

    payment_methods = []

    # Card providers by region
    providers_by_country = {
        'SA': ['mada', 'visa', 'mastercard'],
        'AE': ['visa', 'mastercard', 'amex'],
        'EG': ['visa', 'mastercard', 'meeza'],
        'KW': ['knet', 'visa', 'mastercard'],
        'QA': ['visa', 'mastercard']
    }

    method_types = ['debit_card', 'credit_card',
                    'bank_account', 'wallet_balance']
    method_weights = [0.35, 0.25, 0.25, 0.15]

    for idx, user in users_df.iterrows():
        user_id = user['user_id']
        country = user.get('country', 'EG')
        reg_date = user.get('registration_date', datetime.now())

        # Each user has 1-3 payment methods
        num_methods = random.choices([1, 2, 3], weights=[0.45, 0.40, 0.15])[0]

        for m in range(num_methods):
            method_type = random.choices(
                method_types, weights=method_weights)[0]

            # Provider based on country and type
            if method_type in ['debit_card', 'credit_card']:
                available_providers = providers_by_country.get(
                    country, ['visa', 'mastercard'])
                provider = random.choice(available_providers)
                last_four = str(random.randint(1000, 9999))
                expiry = fake.date_between(start_date='+1y', end_date='+5y')
            elif method_type == 'bank_account':
                provider = f"Bank_{country}_{random.randint(1, 10)}"
                last_four = str(random.randint(1000, 9999))
                expiry = None
            else:  # wallet_balance
                provider = "internal_wallet"
                last_four = None
                expiry = None

            added_date = fake.date_time_between(
                start_date=reg_date, end_date='now')

            # Some payment methods are not verified (intentional noise)
            is_verified = random.choices(
                [True, False], weights=[0.88, 0.12])[0]

            payment_methods.append({
                "payment_method_id": str(uuid.uuid4()),
                "user_id": user_id,
                "method_type": method_type,
                "provider": provider,
                "last_four_digits": last_four,
                "expiry_date": expiry,
                "is_default": (m == 0),  # First method is default
                "is_verified": is_verified,
                "is_active": random.choices([True, False], weights=[0.95, 0.05])[0],
                "added_at": added_date,
                "created_at": added_date,
                "updated_at": fake.date_time_between(start_date=added_date, end_date='now')
            })

        if (idx + 1) % 10000 == 0:
            print(f"   -> {idx + 1:,} users processed...")

    df = pd.DataFrame(payment_methods)

    null_payment_method_idx = _sample_indices(df, config.NULL_PAYMENT_METHOD_ID_RATE, 510)
    df.loc[null_payment_method_idx, "payment_method_id"] = None

    orphan_user_idx = _sample_indices(df, config.ORPHAN_PAYMENT_METHOD_USER_RATE, 511)
    df.loc[orphan_user_idx, "user_id"] = [str(uuid.uuid4()) for _ in range(len(orphan_user_idx))]

    bad_last_four_idx = _sample_indices(
        df,
        config.BAD_LAST_FOUR_DIGITS_RATE,
        512,
        eligible_idx=df.index[df["last_four_digits"].notna()],
    )
    df.loc[bad_last_four_idx, "last_four_digits"] = "12A"

    invalid_expiry_idx = _sample_indices(
        df,
        config.INVALID_EXPIRY_DATE_RATE,
        513,
        eligible_idx=df.index[
            df["method_type"].isin(["debit_card", "credit_card"]) & df["expiry_date"].notna()
        ],
    )
    for idx in invalid_expiry_idx:
        expiry_date = pd.to_datetime(df.at[idx, "expiry_date"])
        invalid_expiry = expiry_date - pd.Timedelta(days=random.randint(365 * 3, 365 * 7))
        df.at[idx, "expiry_date"] = invalid_expiry.date()

    multi_default_users = df.groupby("user_id").size().loc[lambda s: s > 1].index
    multi_default_user_sample = _sample_indices(
        pd.DataFrame(index=multi_default_users),
        config.MULTI_DEFAULT_PAYMENT_RATE,
        514,
    )
    for user_id in multi_default_user_sample.tolist():
        user_rows = df.index[df["user_id"] == user_id]
        if len(user_rows) > 1:
            df.loc[user_rows[1], "is_default"] = True

    invalid_method_type_idx = _sample_indices(df, config.INVALID_PAYMENT_METHOD_TYPE_RATE, 515)
    df.loc[invalid_method_type_idx, "method_type"] = "crypto_wallet"

    filepath = save_dataframe(
        df=df,
        out_dir=out_dir,
        base_name="payment_methods",
        output_format=config.OUTPUT_FORMAT
    )
    print(f"   OK Generated {len(df):,} payment methods -> {filepath}")

    return df


if __name__ == "__main__":
    from generators.users import generate_users
    users = generate_users(num_users=100, output_dir="test_data")
    payment_methods = generate_payment_methods(users, output_dir="test_data")
    print(f"\nSample:\n{payment_methods.head()}")
