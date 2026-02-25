"""
Transactions Generator
The main beast - generates millions of transactions with fraud patterns
"""
from config import config
import pandas as pd
import numpy as np
from faker import Faker
import random
import uuid
from datetime import datetime, timedelta
import os
import shutil
from generators.io_utils import normalize_output_format


def inject_fraud_patterns(transactions: list, fraud_rate: float = 0.03) -> list:
    """
    Mark some transactions as fraudulent with specific patterns
    This creates labeled data for fraud detection model

    Fraud patterns:
    1. velocity - many transactions in short time
    2. amount - unusually large amounts
    3. time - transactions at unusual hours (2-5 AM)
    4. new_device - first transaction from new device with high amount
    """
    num_fraud = int(len(transactions) * fraud_rate)
    fraud_indices = random.sample(
        range(len(transactions)), min(num_fraud, len(transactions)))

    patterns = ['velocity', 'amount', 'time', 'new_device']

    for idx in fraud_indices:
        pattern = random.choice(patterns)
        transactions[idx]['is_flagged'] = True
        transactions[idx]['fraud_pattern'] = pattern

        if pattern == 'amount':
            # Unusually high amount
            transactions[idx]['amount'] = round(
                random.uniform(50000, 200000), 2)
        elif pattern == 'time':
            # Transaction at suspicious hour (2-5 AM)
            original_ts = transactions[idx]['transaction_timestamp']
            if isinstance(original_ts, datetime):
                suspicious_ts = original_ts.replace(hour=random.randint(2, 5))
                transactions[idx]['transaction_timestamp'] = suspicious_ts

    return transactions


def generate_transactions(
    accounts_df: pd.DataFrame,
    merchants_df: pd.DataFrame,
    devices_df: pd.DataFrame,
    payment_methods_df: pd.DataFrame,
    num_transactions: int = None,
    chunk_size: int = None,
    output_dir: str = None
) -> None:
    """
    Generate transaction data in chunks to manage memory

    Args:
        accounts_df: Accounts data (for sender_account_id)
        merchants_df: Merchants data (for receiver in merchant payments)
        devices_df: Devices data (for device_id)
        payment_methods_df: Payment methods data (for payment_method_id)
        num_transactions: Total transactions to generate
        chunk_size: Records per chunk
        output_dir: Output directory
    """
    total = num_transactions or config.NUM_TRANSACTIONS
    chunk_sz = chunk_size or config.CHUNK_SIZE
    out_dir = output_dir or config.OUTPUT_DIR
    output_format = normalize_output_format(config.OUTPUT_FORMAT)

    fake = Faker()
    Faker.seed(config.RANDOM_SEED + 4)
    np.random.seed(config.RANDOM_SEED + 4)
    random.seed(config.RANDOM_SEED + 4)

    print(f"💳 Generating {total:,} Transactions in chunks of {chunk_sz:,}...")

    # Pre-load IDs for fast random selection
    account_ids = accounts_df['account_id'].tolist()
    merchant_ids = merchants_df['merchant_id'].tolist()
    device_ids = devices_df['device_id'].tolist()

    # Build user->device mapping for realistic device selection
    user_devices = devices_df.groupby(
        'user_id')['device_id'].apply(list).to_dict()
    account_users = accounts_df.set_index('account_id')['user_id'].to_dict()
    account_currencies = accounts_df.set_index('account_id')['currency'].to_dict()
    user_payment_methods = payment_methods_df.groupby(
        'user_id')['payment_method_id'].apply(list).to_dict()
    all_payment_method_ids = payment_methods_df['payment_method_id'].tolist()

    if not all_payment_method_ids:
        raise ValueError("payment_methods_df is empty; cannot assign payment_method_id")

    # File setup
    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, "transactions.csv")
    parquet_dir = os.path.join(out_dir, "transactions_parquet")

    if output_format == "csv":
        if os.path.exists(filepath):
            os.remove(filepath)
        header_written = False
    else:
        if os.path.exists(parquet_dir):
            shutil.rmtree(parquet_dir)
        os.makedirs(parquet_dir, exist_ok=True)
        header_written = None
    total_generated = 0

    # Generate in chunks
    num_chunks = (total + chunk_sz - 1) // chunk_sz

    for chunk_num in range(num_chunks):
        current_chunk_size = min(chunk_sz, total - total_generated)
        transactions = []

        for _ in range(current_chunk_size):
            # Pick sender account
            sender_acc = random.choice(account_ids)
            sender_user = account_users.get(sender_acc)

            # Transaction type
            txn_type = random.choices(
                config.TRANSACTION_TYPES,
                weights=config.TRANSACTION_TYPE_WEIGHTS
            )[0]

            # Payment method linked to sender user for downstream adoption analysis
            if sender_user and sender_user in user_payment_methods:
                payment_method_id = random.choice(user_payment_methods[sender_user])
            else:
                payment_method_id = random.choice(all_payment_method_ids)

            # Receiver depends on type
            if txn_type == 'P2P_Transfer':
                receiver = random.choice(account_ids)
                if len(account_ids) > 1:
                    while receiver == sender_acc:
                        receiver = random.choice(account_ids)
                receiver_type = 'account'
            elif txn_type == 'Merchant_Payment':
                receiver = random.choice(merchant_ids)
                receiver_type = 'merchant'
            else:
                receiver = None
                receiver_type = 'self'

            # Amount with intentional noise (some negative - invalid)
            if random.random() < config.NEGATIVE_AMOUNT_RATE:
                amount = round(random.uniform(-100, -1), 2)  # Invalid negative
            else:
                # Realistic amount distribution (most are small)
                amount = round(np.random.exponential(500) + 10, 2)
                # Cap at 50K for normal transactions
                amount = min(amount, 50000)

            # Currency from sender's account (consistent with account setup)
            currency = account_currencies.get(sender_acc, 'AED')
            fee = round(abs(amount) * random.uniform(0.01, 0.03), 2)

            # Timestamps
            txn_ts = fake.date_time_between(start_date='-1y', end_date='now')

            # Intentional noise: some invalid timestamps
            if random.random() < config.INVALID_TIMESTAMP_RATE:
                # Invalid: completed before transaction
                completed_ts = txn_ts - timedelta(hours=random.randint(1, 24))
            else:
                completed_ts = txn_ts + \
                    timedelta(seconds=random.randint(1, 60))

            # Device - prefer user's own devices
            if sender_user and sender_user in user_devices:
                device_id = random.choice(user_devices[sender_user])
            else:
                device_id = random.choice(device_ids)

            # Location (Egypt/KSA/UAE coordinates roughly)
            # North Africa/Middle East
            lat = round(random.uniform(22.0, 32.0), 6)
            lon = round(random.uniform(29.0, 56.0), 6)

            # Risk score (will be recalculated in Silver layer)
            risk_score = round(np.random.exponential(0.1), 3)
            risk_score = min(risk_score, 1.0)

            transactions.append({
                "transaction_id": str(uuid.uuid4()),
                "sender_account_id": sender_acc,
                "receiver_id": receiver,
                "receiver_type": receiver_type,
                "transaction_type": txn_type,
                "payment_method_id": payment_method_id,
                "amount": amount,
                "currency": currency,
                "fee_amount": fee,
                "status": random.choices(
                    config.TRANSACTION_STATUSES,
                    weights=config.STATUS_WEIGHTS
                )[0],
                "device_id": device_id,
                "ip_address": fake.ipv4(),
                "latitude": lat,
                "longitude": lon,
                "transaction_timestamp": txn_ts,
                "completed_timestamp": completed_ts,
                "risk_score": risk_score,
                "is_flagged": False,
                "fraud_pattern": None,
                "created_at": txn_ts
            })

        # Inject fraud patterns
        transactions = inject_fraud_patterns(transactions, config.FRAUD_RATE)

        # Add duplicates (intentional noise)
        num_duplicates = int(len(transactions) * config.DUPLICATE_RATE)
        if num_duplicates > 0:
            duplicates = random.choices(transactions, k=num_duplicates)
            transactions.extend(duplicates)

        # Convert to DataFrame and save
        df_chunk = pd.DataFrame(transactions)
        if output_format == "csv":
            df_chunk.to_csv(filepath, mode='a',
                            header=not header_written, index=False)
            header_written = True
        else:
            part_path = os.path.join(parquet_dir, f"part-{chunk_num + 1:05d}.parquet")
            df_chunk.to_parquet(part_path, index=False)

        total_generated += current_chunk_size
        print(
            f"   → Chunk {chunk_num + 1}/{num_chunks} complete ({total_generated:,} transactions)")

    output_target = filepath if output_format == "csv" else parquet_dir
    print(f"   ✅ Generated {total_generated:,} transactions → {output_target}")


if __name__ == "__main__":
    from generators.users import generate_users
    from generators.merchants import generate_merchants
    from generators.accounts import generate_accounts
    from generators.devices import generate_devices
    from generators.payment_methods import generate_payment_methods

    # Test with small sample
    out = "test_data"
    users = generate_users(num_users=100, output_dir=out)
    merchants = generate_merchants(num_merchants=20, output_dir=out)
    accounts = generate_accounts(users, output_dir=out)
    devices = generate_devices(users, output_dir=out)
    payment_methods = generate_payment_methods(users, output_dir=out)

    generate_transactions(
        accounts, merchants, devices, payment_methods,
        num_transactions=1000,
        chunk_size=500,
        output_dir=out
    )

    # Load and check
    if normalize_output_format(config.OUTPUT_FORMAT) == "csv":
        df = pd.read_csv(f"{out}/transactions.csv")
    else:
        df = pd.read_parquet(f"{out}/transactions_parquet/part-00001.parquet")
    print(f"\nSample:\n{df.head()}")
    print(f"\nFraud transactions: {df['is_flagged'].sum()}")
    print(f"Negative amounts: {(df['amount'] < 0).sum()}")
