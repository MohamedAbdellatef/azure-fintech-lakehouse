"""
FinTech Data Generator - Main Entry Point
==========================================

Generates synthetic payment/wallet data for testing data pipelines.

Usage:
    python main.py                    # Generate with default config
    python main.py --small            # Small dataset for testing (10K transactions)
    python main.py --medium           # Medium dataset (100K transactions)
    python main.py --full             # Full dataset (1M transactions)
    python main.py --output ./data    # Custom output directory

Author: Mohamed
Project: azure-fintech-lakehouse
"""

from generators import (
    generate_users,
    generate_merchants,
    generate_accounts,
    generate_devices,
    generate_payment_methods,
    generate_kyc_records,
    generate_transactions
)
from config import GeneratorConfig
import argparse
import os
import sys
import time
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_banner():
    """Print a nice banner"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║          🏦 FinTech Synthetic Data Generator 🏦               ║
║                   Payment & Wallet Data                       ║
╚═══════════════════════════════════════════════════════════════╝
    """)


def print_summary(config: GeneratorConfig, elapsed: float):
    """Print generation summary"""
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                    ✅ GENERATION COMPLETE                     ║
╠═══════════════════════════════════════════════════════════════╣
║  Output Directory : {config.OUTPUT_DIR:<41} ║
║  Users            : {config.NUM_USERS:>10,} records                      ║
║  Merchants        : {config.NUM_MERCHANTS:>10,} records                      ║
║  Transactions     : {config.NUM_TRANSACTIONS:>10,} records                      ║
║  Time Elapsed     : {elapsed:>10.1f} seconds                      ║
╠═══════════════════════════════════════════════════════════════╣
║  Files Generated:                                             ║
║    - users.csv                                                ║
║    - merchants.csv                                            ║
║    - accounts.csv                                             ║
║    - devices.csv                                              ║
║    - payment_methods.csv                                      ║
║    - kyc_records.csv                                          ║
║    - transactions.csv                                         ║
╚═══════════════════════════════════════════════════════════════╝
    """)


def main():
    parser = argparse.ArgumentParser(
        description='Generate synthetic FinTech payment data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --small              # Quick test (10K transactions)
  python main.py --medium             # Dev/test (100K transactions)
  python main.py --full               # Production-like (1M transactions)
  python main.py --output ./my_data   # Custom output folder
        """
    )

    parser.add_argument('--small', action='store_true',
                        help='Generate small dataset (1K users, 10K transactions)')
    parser.add_argument('--medium', action='store_true',
                        help='Generate medium dataset (10K users, 100K transactions)')
    parser.add_argument('--full', action='store_true',
                        help='Generate full dataset (50K users, 1M transactions)')
    parser.add_argument('--output', '-o', type=str, default='raw_data',
                        help='Output directory (default: raw_data)')

    args = parser.parse_args()

    # Configure based on size
    config = GeneratorConfig()
    config.OUTPUT_DIR = args.output

    if args.small:
        config.NUM_USERS = 1_000
        config.NUM_MERCHANTS = 100
        config.NUM_TRANSACTIONS = 10_000
        config.CHUNK_SIZE = 5_000
        print("📦 Mode: SMALL (1K users, 10K transactions)")
    elif args.medium:
        config.NUM_USERS = 10_000
        config.NUM_MERCHANTS = 500
        config.NUM_TRANSACTIONS = 100_000
        config.CHUNK_SIZE = 25_000
        print("📦 Mode: MEDIUM (10K users, 100K transactions)")
    elif args.full:
        config.NUM_USERS = 50_000
        config.NUM_MERCHANTS = 2_000
        config.NUM_TRANSACTIONS = 1_000_000
        config.CHUNK_SIZE = 100_000
        print("📦 Mode: FULL (50K users, 1M transactions)")
    else:
        # Default is medium
        config.NUM_USERS = 10_000
        config.NUM_MERCHANTS = 500
        config.NUM_TRANSACTIONS = 100_000
        config.CHUNK_SIZE = 25_000
        print("📦 Mode: DEFAULT/MEDIUM (10K users, 100K transactions)")

    print_banner()
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Output directory: {config.OUTPUT_DIR}\n")

    start_time = time.time()

    try:
        # Step 1: Generate Users
        users_df = generate_users(
            num_users=config.NUM_USERS,
            output_dir=config.OUTPUT_DIR
        )

        # Step 2: Generate Merchants
        merchants_df = generate_merchants(
            num_merchants=config.NUM_MERCHANTS,
            output_dir=config.OUTPUT_DIR
        )

        # Step 3: Generate Accounts (depends on users)
        accounts_df = generate_accounts(
            users_df=users_df,
            output_dir=config.OUTPUT_DIR
        )

        # Step 4: Generate Devices (depends on users)
        devices_df = generate_devices(
            users_df=users_df,
            output_dir=config.OUTPUT_DIR
        )

        # Step 5: Generate Payment Methods (depends on users)
        payment_methods_df = generate_payment_methods(
            users_df=users_df,
            output_dir=config.OUTPUT_DIR
        )

        # Step 6: Generate KYC Records (depends on users)
        kyc_df = generate_kyc_records(
            users_df=users_df,
            output_dir=config.OUTPUT_DIR
        )

        # Step 7: Generate Transactions (depends on accounts, merchants, devices)
        generate_transactions(
            accounts_df=accounts_df,
            merchants_df=merchants_df,
            devices_df=devices_df,
            num_transactions=config.NUM_TRANSACTIONS,
            chunk_size=config.CHUNK_SIZE,
            output_dir=config.OUTPUT_DIR
        )

        elapsed = time.time() - start_time
        print_summary(config, elapsed)

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
