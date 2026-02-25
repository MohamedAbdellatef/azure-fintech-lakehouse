"""
FinTech Data Generator - Main Entry Point
==========================================

Generates synthetic payment/wallet data for testing data pipelines.

Usage:
    python main.py                    # Generate with default config
    python main.py --small            # Small dataset for testing
    python main.py --medium           # Medium dataset
    python main.py --full             # Full dataset
    python main.py --output ./data    # Custom output directory
    python main.py --format parquet   # Output parquet files

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
    generate_transactions,
)
from config import GeneratorConfig, config as shared_config
import argparse
import sys
import time
from datetime import datetime


def print_banner():
    """Print startup banner."""
    print("\n=== FinTech Synthetic Data Generator ===")


def print_summary(config: GeneratorConfig, elapsed: float):
    """Print generation summary."""
    ext = "csv" if config.OUTPUT_FORMAT == "csv" else "parquet"
    transactions_output = (
        "transactions.csv"
        if ext == "csv"
        else "transactions_parquet/part-*.parquet"
    )

    print("\n=== GENERATION COMPLETE ===")
    print(f"Output Directory : {config.OUTPUT_DIR}")
    print(f"Output Format    : {config.OUTPUT_FORMAT.upper()}")
    print(f"Users            : {config.NUM_USERS:,} records")
    print(f"Merchants        : {config.NUM_MERCHANTS:,} records")
    print(f"Transactions     : {config.NUM_TRANSACTIONS:,} records")
    print(f"Time Elapsed     : {elapsed:.1f} seconds")
    print("Files Generated:")
    print(f"  - users.{ext}")
    print(f"  - merchants.{ext}")
    print(f"  - accounts.{ext}")
    print(f"  - devices.{ext}")
    print(f"  - payment_methods.{ext}")
    print(f"  - kyc_records.{ext}")
    print(f"  - {transactions_output}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic FinTech payment data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --small
  python main.py --medium
  python main.py --full
  python main.py --output ./my_data
  python main.py --format parquet
        """,
    )

    parser.add_argument(
        "--small",
        action="store_true",
        help="Generate small dataset (1K users, 10K transactions)",
    )
    parser.add_argument(
        "--medium",
        action="store_true",
        help="Generate medium dataset (10K users, 100K transactions)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate full dataset (50K users, 1M transactions)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="raw_data",
        help="Output directory (default: raw_data)",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="csv",
        choices=["csv", "parquet"],
        help="Output file format (default: csv)",
    )

    args = parser.parse_args()

    # Configure based on size.
    config = shared_config
    config.OUTPUT_DIR = args.output
    config.OUTPUT_FORMAT = args.format.lower()

    if args.small:
        config.NUM_USERS = 1_000
        config.NUM_MERCHANTS = 100
        config.NUM_TRANSACTIONS = 10_000
        config.CHUNK_SIZE = 5_000
        print("Mode: SMALL (1K users, 10K transactions)")
    elif args.medium:
        config.NUM_USERS = 10_000
        config.NUM_MERCHANTS = 500
        config.NUM_TRANSACTIONS = 100_000
        config.CHUNK_SIZE = 25_000
        print("Mode: MEDIUM (10K users, 100K transactions)")
    elif args.full:
        config.NUM_USERS = 50_000
        config.NUM_MERCHANTS = 2_000
        config.NUM_TRANSACTIONS = 1_000_000
        config.CHUNK_SIZE = 100_000
        print("Mode: FULL (50K users, 1M transactions)")
    else:
        config.NUM_USERS = 10_000
        config.NUM_MERCHANTS = 500
        config.NUM_TRANSACTIONS = 100_000
        config.CHUNK_SIZE = 25_000
        print("Mode: DEFAULT/MEDIUM (10K users, 100K transactions)")

    print_banner()
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output directory: {config.OUTPUT_DIR}")
    print(f"Output format: {config.OUTPUT_FORMAT}")

    start_time = time.time()

    try:
        users_df = generate_users(
            num_users=config.NUM_USERS,
            output_dir=config.OUTPUT_DIR,
        )

        merchants_df = generate_merchants(
            num_merchants=config.NUM_MERCHANTS,
            output_dir=config.OUTPUT_DIR,
        )

        accounts_df = generate_accounts(
            users_df=users_df,
            output_dir=config.OUTPUT_DIR,
        )

        devices_df = generate_devices(
            users_df=users_df,
            output_dir=config.OUTPUT_DIR,
        )

        payment_methods_df = generate_payment_methods(
            users_df=users_df,
            output_dir=config.OUTPUT_DIR,
        )

        generate_kyc_records(
            users_df=users_df,
            output_dir=config.OUTPUT_DIR,
        )

        generate_transactions(
            accounts_df=accounts_df,
            merchants_df=merchants_df,
            devices_df=devices_df,
            payment_methods_df=payment_methods_df,
            num_transactions=config.NUM_TRANSACTIONS,
            chunk_size=config.CHUNK_SIZE,
            output_dir=config.OUTPUT_DIR,
        )

        elapsed = time.time() - start_time
        print_summary(config, elapsed)
        return 0

    except Exception as exc:
        print(f"\nERROR: {exc}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
