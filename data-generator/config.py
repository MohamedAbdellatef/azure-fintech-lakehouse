"""
Configuration for FinTech Data Generator
All settings in one place - easy to adjust
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class GeneratorConfig:
    """Main configuration for data generation"""

    # ===========================================
    # Volume Settings (adjust based on your needs)
    # ===========================================
    NUM_USERS: int = 50_000          # 50K users
    NUM_MERCHANTS: int = 2_000        # 2K merchants
    NUM_TRANSACTIONS: int = 1_000_000  # 1M transactions
    CHUNK_SIZE: int = 100_000         # Process in chunks for RAM

    # ===========================================
    # Output Settings
    # ===========================================
    OUTPUT_DIR: str = "raw_data"
    OUTPUT_FORMAT: str = "csv"  # "csv" or "parquet"

    # ===========================================
    # Data Quality Noise Rates
    # These create realistic "dirty" data for DQ testing
    # ===========================================
    NULL_EMAIL_RATE: float = 0.05      # 5% missing emails
    NULL_PHONE_RATE: float = 0.03      # 3% missing phones
    DUPLICATE_RATE: float = 0.01       # 1% duplicate transactions
    NEGATIVE_AMOUNT_RATE: float = 0.02  # 2% negative amounts (invalid)
    INVALID_TIMESTAMP_RATE: float = 0.01  # 1% invalid timestamps

    # ===========================================
    # Fraud Pattern Rates
    # ===========================================
    FRAUD_RATE: float = 0.03           # 3% fraudulent transactions

    # ===========================================
    # Geographic Distribution (UAE/KSA/Egypt focus)
    # ===========================================
    COUNTRIES: List[str] = field(default_factory=lambda: [
                                 'EG', 'SA', 'AE', 'KW', 'QA'])
    COUNTRY_WEIGHTS: List[float] = field(
        default_factory=lambda: [0.40, 0.30, 0.20, 0.05, 0.05])

    # Currency by country
    CURRENCY_MAP: Dict[str, str] = field(default_factory=lambda: {
        'EG': 'EGP',
        'SA': 'SAR',
        'AE': 'AED',
        'KW': 'KWD',
        'QA': 'QAR'
    })

    # ===========================================
    # Business Rules
    # ===========================================
    TRANSACTION_TYPES: List[str] = field(default_factory=lambda: [
        'P2P_Transfer',      # Person to person
        'Merchant_Payment',  # Pay at store/online
        'Deposit',           # Add money to wallet
        'Withdrawal',        # Cash out
        'Bill_Payment'       # Utilities, phone, etc.
    ])
    TRANSACTION_TYPE_WEIGHTS: List[float] = field(
        default_factory=lambda: [0.25, 0.35, 0.20, 0.10, 0.10])

    TRANSACTION_STATUSES: List[str] = field(
        default_factory=lambda: ['Success', 'Failed', 'Pending', 'Reversed'])
    STATUS_WEIGHTS: List[float] = field(
        default_factory=lambda: [0.85, 0.08, 0.05, 0.02])

    KYC_STATUSES: List[str] = field(default_factory=lambda: [
                                    'verified', 'pending', 'rejected'])
    KYC_WEIGHTS: List[float] = field(
        default_factory=lambda: [0.80, 0.15, 0.05])

    MERCHANT_CATEGORIES: List[str] = field(default_factory=lambda: [
        'Retail', 'Food & Beverage', 'Utilities', 'Travel',
        'E-commerce', 'Gaming', 'Healthcare', 'Education'
    ])

    DEVICE_TYPES: List[str] = field(default_factory=lambda: [
                                    'ios', 'android', 'web'])
    DEVICE_WEIGHTS: List[float] = field(
        default_factory=lambda: [0.35, 0.55, 0.10])

    # ===========================================
    # Seed for reproducibility
    # ===========================================
    RANDOM_SEED: int = 42


# Default config instance
config = GeneratorConfig()
