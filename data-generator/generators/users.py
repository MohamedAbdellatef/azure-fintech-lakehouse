"""
Users Generator
Generates synthetic user profiles for FinTech platform
"""
from config import config
import pandas as pd
import numpy as np
from faker import Faker
import random
import uuid
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_users(num_users: int = None, output_dir: str = None) -> pd.DataFrame:
    """
    Generate synthetic user data

    Args:
        num_users: Number of users to generate (default from config)
        output_dir: Output directory (default from config)

    Returns:
        DataFrame with user data
    """
    n = num_users or config.NUM_USERS
    out_dir = output_dir or config.OUTPUT_DIR

    fake = Faker()
    Faker.seed(config.RANDOM_SEED)
    np.random.seed(config.RANDOM_SEED)
    random.seed(config.RANDOM_SEED)

    print(f"📧 Generating {n:,} Users...")

    users = []

    for i in range(n):
        # Select country based on weights
        country = random.choices(
            config.COUNTRIES, weights=config.COUNTRY_WEIGHTS)[0]
        currency = config.CURRENCY_MAP.get(country, 'USD')

        # Intentional noise: some missing emails
        email = fake.email() if random.random() > config.NULL_EMAIL_RATE else None

        # Intentional noise: messy phone numbers (different formats)
        if random.random() > config.NULL_PHONE_RATE:
            phone_formats = [
                # Egypt
                f"+20{random.randint(10, 12)}{fake.random_number(digits=8, fix_len=True)}",
                # KSA
                f"+966{random.randint(50, 59)}{fake.random_number(digits=7, fix_len=True)}",
                # UAE
                f"+971{random.randint(50, 56)}{fake.random_number(digits=7, fix_len=True)}",
                fake.phone_number()  # Random format
            ]
            phone = random.choice(phone_formats)
        else:
            phone = None

        # Registration date
        reg_date = fake.date_time_between(start_date='-3y', end_date='now')

        users.append({
            "user_id": str(uuid.uuid4()),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email,
            "phone_number": phone,
            "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=65),
            "gender": random.choice(['M', 'F']),
            "country": country,
            "city": fake.city(),
            "preferred_currency": currency,
            "kyc_status": random.choices(config.KYC_STATUSES, weights=config.KYC_WEIGHTS)[0],
            "user_tier": random.choices(
                ['basic', 'silver', 'gold', 'platinum'],
                weights=[0.60, 0.25, 0.10, 0.05]
            )[0],
            "is_active": random.choices([True, False], weights=[0.92, 0.08])[0],
            "registration_date": reg_date,
            "created_at": reg_date,
            "updated_at": datetime.now()
        })

        # Progress indicator
        if (i + 1) % 10000 == 0:
            print(f"   → {i + 1:,} users generated...")

    df = pd.DataFrame(users)

    # Save to file
    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, "users.csv")
    df.to_csv(filepath, index=False)
    print(f"   ✅ Saved to {filepath}")

    return df


if __name__ == "__main__":
    # Test with small sample
    df = generate_users(num_users=100, output_dir="test_data")
    print(f"\nSample:\n{df.head()}")
    print(f"\nNull counts:\n{df.isnull().sum()}")
