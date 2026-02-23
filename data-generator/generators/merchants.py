"""
Merchants Generator
Generates synthetic merchant/business data
Regional Arabic business names for MENA market authenticity
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

# ═══════════════════════════════════════════════════════════════════════════
# MENA REGION BUSINESS NAMES - Authentic Arabic-style business names
# ═══════════════════════════════════════════════════════════════════════════

# Arabic business name prefixes (transliterated)
ARABIC_BUSINESS_PREFIXES = [
    "Al", "El", "Abu", "Dar", "Beit", "Souq", "Markaz"
]

# Arabic business name roots
ARABIC_BUSINESS_NAMES = [
    # Egyptian style
    "Misr", "Nile", "Pharaoh", "Cairo", "Alexandria", "Giza", "Luxor",
    "Cleopatra", "Sphinx", "Delta", "Sinai", "Aswan",
    # Saudi/Gulf style
    "Riyadh", "Jeddah", "Najd", "Hejaz", "Qassim", "Madinah",
    "Taif", "Dammam", "Khobar", "Jubail",
    # UAE style
    "Dubai", "Emirates", "Burj", "Palm", "Marina", "Creek",
    "Sharjah", "Ajman", "Fujairah", "Ras Al Khaimah",
    # General Arabic
    "Salam", "Noor", "Baraka", "Amal", "Hayat", "Majd",
    "Safwa", "Raha", "Watan", "Itqan", "Jawda", "Thiqah"
]

# Business type suffixes
ARABIC_BUSINESS_SUFFIXES = [
    "Trading", "Group", "Enterprises", "Solutions", "Services",
    "Tech", "Digital", "Express", "Plus", "Pro", "Hub",
    "House", "Center", "Store", "Shop", "Mart", "Zone",
    "Est.", "Co.", "LLC", "WLL"  # Common in Gulf
]

# Family/Owner names for businesses
OWNER_NAMES = [
    "Al-Rashid", "Al-Salem", "Al-Zahrani", "Al-Otaibi", "Al-Ghamdi",
    "Elsayed", "Ibrahim", "Mahmoud", "Hassan", "Mohamed",
    "Al-Maktoum", "Al-Nahyan", "Al-Falasi", "Al-Ketbi",
    "Abdullah", "Khalid", "Ahmed", "Nasser", "Faisal"
]

# Cities per country for more realism
CITIES_BY_COUNTRY = {
    'EG': ['Cairo', 'Alexandria', 'Giza', 'Shubra El Kheima', 'Port Said',
           'Suez', 'Mansoura', 'Tanta', 'Aswan', 'Ismailia', 'Zagazig', 'Luxor'],
    'SA': ['Riyadh', 'Jeddah', 'Makkah', 'Madinah', 'Dammam', 'Khobar',
           'Taif', 'Tabuk', 'Buraidah', 'Khamis Mushait', 'Abha', 'Jubail'],
    'AE': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Al Ain',
           'Ras Al Khaimah', 'Fujairah', 'Umm Al Quwain'],
    'KW': ['Kuwait City', 'Hawalli', 'Salmiya', 'Farwaniya', 'Ahmadi'],
    'QA': ['Doha', 'Al Wakrah', 'Al Khor', 'Lusail', 'Mesaieed']
}


def generate_merchant_name():
    """Generate an authentic MENA-style business name"""
    style = random.choice(['prefix', 'owner', 'location', 'modern'])

    if style == 'prefix':
        # e.g., "Al Noor Trading", "Dar Al Salam Services"
        prefix = random.choice(ARABIC_BUSINESS_PREFIXES)
        name = random.choice(ARABIC_BUSINESS_NAMES)
        suffix = random.choice(ARABIC_BUSINESS_SUFFIXES)
        return f"{prefix} {name} {suffix}"

    elif style == 'owner':
        # e.g., "Al-Rashid Group", "Mohamed Enterprises"
        owner = random.choice(OWNER_NAMES)
        suffix = random.choice(
            ['Group', 'Enterprises', 'Trading', 'Co.', 'Est.', 'LLC'])
        return f"{owner} {suffix}"

    elif style == 'location':
        # e.g., "Dubai Digital Hub", "Cairo Express"
        location = random.choice(ARABIC_BUSINESS_NAMES)
        suffix = random.choice(ARABIC_BUSINESS_SUFFIXES)
        return f"{location} {suffix}"

    else:  # modern
        # e.g., "PayNow MENA", "QuickPay Gulf"
        modern_prefixes = ['Pay', 'Quick',
                           'Easy', 'Fast', 'Smart', 'Digi', 'E-']
        modern_names = ['Pay', 'Cash', 'Money',
                        'Transfer', 'Send', 'Wallet', 'Coin']
        regions = ['MENA', 'Gulf', 'Arabia', 'Middle East', '']
        return f"{random.choice(modern_prefixes)}{random.choice(modern_names)} {random.choice(regions)}".strip()


def generate_merchants(num_merchants: int = None, output_dir: str = None) -> pd.DataFrame:
    """
    Generate synthetic merchant data with authentic MENA region business names

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

    print(f"🏪 Generating {n:,} Merchants (MENA region names)...")

    merchants = []

    for i in range(n):
        country = random.choices(
            ['EG', 'SA', 'AE'], weights=[0.4, 0.35, 0.25])[0]

        # Use country-specific cities
        city = random.choice(CITIES_BY_COUNTRY.get(country, ['Unknown']))

        reg_date = fake.date_time_between(start_date='-5y', end_date='-6m')

        # Risk score - most merchants are low risk
        risk_score = np.clip(np.random.exponential(0.15), 0, 1)

        merchants.append({
            "merchant_id": str(uuid.uuid4()),
            "merchant_name": generate_merchant_name(),  # Use Arabic business names
            "merchant_category": random.choice(config.MERCHANT_CATEGORIES),
            "business_type": random.choices(
                ['individual', 'company', 'enterprise'],
                weights=[0.30, 0.55, 0.15]
            )[0],
            "country": country,
            "city": city,  # Country-specific cities
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
