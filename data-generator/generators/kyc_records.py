"""
KYC Records Generator
Generates Know Your Customer verification records
"""
from config import config
import pandas as pd
import numpy as np
from faker import Faker
import random
import uuid
import hashlib
from datetime import datetime, timedelta
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def hash_document_number(doc_num: str) -> str:
    """Hash document number for privacy (realistic practice)"""
    return hashlib.sha256(doc_num.encode()).hexdigest()[:32]


def generate_kyc_records(users_df: pd.DataFrame, output_dir: str = None) -> pd.DataFrame:
    """
    Generate KYC (Know Your Customer) verification records
    Each user has 1 KYC record with their verification status

    Args:
        users_df: DataFrame with user data
        output_dir: Output directory

    Returns:
        DataFrame with KYC data
    """
    out_dir = output_dir or config.OUTPUT_DIR

    fake = Faker()
    Faker.seed(config.RANDOM_SEED + 6)
    random.seed(config.RANDOM_SEED + 6)

    print(f"📋 Generating KYC Records...")

    kyc_records = []

    # Document types by country
    doc_types_by_country = {
        'SA': ['national_id', 'iqama', 'passport'],  # Iqama for residents
        'AE': ['emirates_id', 'passport', 'visa'],
        'EG': ['national_id', 'passport'],
        'KW': ['civil_id', 'passport'],
        'QA': ['qatar_id', 'passport']
    }

    rejection_reasons = [
        'document_expired',
        'document_unclear',
        'face_mismatch',
        'information_mismatch',
        'suspected_fraud',
        'incomplete_documents'
    ]

    for idx, user in users_df.iterrows():
        user_id = user['user_id']
        country = user.get('country', 'EG')
        kyc_status = user.get('kyc_status', 'pending')
        reg_date = user.get('registration_date', datetime.now())

        # Document type based on country
        available_doc_types = doc_types_by_country.get(
            country, ['national_id', 'passport'])
        doc_type = random.choice(available_doc_types)

        # Generate fake document number (then hash it)
        if doc_type == 'national_id':
            doc_number = str(random.randint(
                10000000000000, 99999999999999))  # 14 digits
        elif doc_type == 'passport':
            doc_number = fake.bothify(
                text='??#######').upper()  # 2 letters + 7 digits
        elif doc_type == 'iqama':
            doc_number = str(random.randint(
                1000000000, 9999999999))  # 10 digits
        elif doc_type == 'emirates_id':
            doc_number = f"784-{random.randint(1950, 2005)}-{random.randint(1000000, 9999999)}-{random.randint(1, 9)}"
        else:
            doc_number = str(random.randint(100000000, 999999999))

        # Timestamps based on status
        submitted_at = fake.date_time_between(
            start_date=reg_date, end_date='now')

        if kyc_status == 'verified':
            verified_at = fake.date_time_between(
                start_date=submitted_at, end_date='now')
            rejection_reason = None
            verified_by = random.choices(
                ['system_auto', 'manual_review'], weights=[0.75, 0.25])[0]
            attempts = random.choices([1, 2, 3], weights=[0.80, 0.15, 0.05])[0]
        elif kyc_status == 'rejected':
            verified_at = fake.date_time_between(
                start_date=submitted_at, end_date='now')
            rejection_reason = random.choice(rejection_reasons)
            verified_by = 'manual_review'
            attempts = random.choices([1, 2, 3, 4], weights=[
                                      0.40, 0.30, 0.20, 0.10])[0]
        else:  # pending
            verified_at = None
            rejection_reason = None
            verified_by = None
            attempts = 1

        # Some document numbers might be NULL (intentional noise)
        if random.random() < 0.02:
            doc_number_hashed = None
        else:
            doc_number_hashed = hash_document_number(doc_number)

        kyc_records.append({
            "kyc_id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_type": doc_type,
            "document_number_hash": doc_number_hashed,
            "document_country": country,
            "verification_status": kyc_status,
            "rejection_reason": rejection_reason,
            "verification_attempts": attempts,
            "submitted_at": submitted_at,
            "verified_at": verified_at,
            "verified_by": verified_by,
            "risk_flags": random.choices([None, 'high_risk_country', 'pep_match', 'sanctions_check'],
                                         weights=[0.92, 0.04, 0.02, 0.02])[0],
            "created_at": submitted_at,
            "updated_at": verified_at or submitted_at
        })

        if (idx + 1) % 10000 == 0:
            print(f"   → {idx + 1:,} users processed...")

    df = pd.DataFrame(kyc_records)

    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, "kyc_records.csv")
    df.to_csv(filepath, index=False)
    print(f"   ✅ Generated {len(df):,} KYC records → {filepath}")

    return df


if __name__ == "__main__":
    from users import generate_users
    users = generate_users(num_users=100, output_dir="test_data")
    kyc = generate_kyc_records(users, output_dir="test_data")
    print(f"\nSample:\n{kyc.head()}")
    print(
        f"\nStatus distribution:\n{kyc['verification_status'].value_counts()}")
