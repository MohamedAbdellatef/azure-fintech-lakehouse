"""
Merchants Generator
Generates synthetic merchant/business data
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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_merchants(num_merchants: int = None, output_dir: str = None) -> pd.DataFrame:
    """
    Generate synthetic merchant data

    Args:
        num_merchants: Number of merchants to generate
        output_dir: Output directory

    Returns:
        DataFrame with merchant data
    """
    n = num_merchants or config.NUM_MERCHANTS
    out_dir = output_dir or config.OUTPUT_DIR

    fake = Faker()
    Faker.seed(config.RANDOM_SEED + 1)  # Different seed for variety
    np.random.seed(config.RANDOM_SEED + 1)
    random.seed(config.RANDOM_SEED + 1)

    print(f"🏪 Generating {n:,} Merchants...")

    merchants = []

    for i in range(n):
        country = random.choices(
            ['EG', 'SA', 'AE'], weights=[0.4, 0.35, 0.25])[0]
        reg_date = fake.date_time_between(start_date='-5y', end_date='-6m')

        # Risk score - most merchants are low risk
        risk_score = np.clip(np.random.exponential(0.15), 0, 1)

        merchants.append({
            "merchant_id": str(uuid.uuid4()),
            "merchant_name": fake.company(),
            "merchant_category": random.choice(config.MERCHANT_CATEGORIES),
            "business_type": random.choices(
                ['individual', 'company', 'enterprise'],
                weights=[0.30, 0.55, 0.15]
            )[0],
            "country": country,
            "city": fake.city(),
            "registration_date": reg_date.date(),
            "is_verified": random.choices([True, False], weights=[0.88, 0.12])[0],
            "is_active": random.choices([True, False], weights=[0.90, 0.10])[0],
            "risk_score": round(risk_score, 3),
            "monthly_limit": random.choice([50000, 100000, 250000, 500000, 1000000]),
            "fee_percentage": round(random.uniform(1.5, 3.5), 2),
            "created_at": reg_date,
            "updated_at": datetime.now()
        })

    df = pd.DataFrame(merchants)

    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, "merchants.csv")
    df.to_csv(filepath, index=False)
    print(f"   ✅ Saved to {filepath}")

    return df


if __name__ == "__main__":
    df = generate_merchants(num_merchants=50, output_dir="test_data")
    print(f"\nSample:\n{df.head()}")
