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

    print(f"💳 Generating Payment Methods (1-3 per user)...")

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
                "updated_at": datetime.now()
            })

        if (idx + 1) % 10000 == 0:
            print(f"   → {idx + 1:,} users processed...")

    df = pd.DataFrame(payment_methods)

    filepath = save_dataframe(
        df=df,
        out_dir=out_dir,
        base_name="payment_methods",
        output_format=config.OUTPUT_FORMAT
    )
    print(f"   ✅ Generated {len(df):,} payment methods → {filepath}")

    return df


if __name__ == "__main__":
    from generators.users import generate_users
    users = generate_users(num_users=100, output_dir="test_data")
    payment_methods = generate_payment_methods(users, output_dir="test_data")
    print(f"\nSample:\n{payment_methods.head()}")
