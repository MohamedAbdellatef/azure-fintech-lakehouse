"""
Users Generator
Generates synthetic user profiles for FinTech platform
Mixed demographics: Arabic + Expats (Indian, Western, Filipino) for UAE/KSA market reality
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

# ═══════════════════════════════════════════════════════════════════════════
# MENA MARKET DEMOGRAPHICS - Realistic mix for UAE/KSA/Egypt
# UAE: 12% Emirati, 30% Indian, 12% Pakistani, 10% Filipino, 8% Western, 28% Other Arab
# KSA: 60% Saudi, 40% Expats | Egypt: 95% Egyptian, 5% Other
# ═══════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# ARABIC NAMES (Egyptian, Saudi, Emirati, Gulf)
# ─────────────────────────────────────────────────────────────────────────────
ARABIC_FIRST_NAMES_MALE = [
    # Egyptian popular names
    "Ahmed", "Mohamed", "Mahmoud", "Omar", "Youssef", "Hassan", "Hussein",
    "Mostafa", "Karim", "Tarek", "Amr", "Khaled", "Sherif", "Hossam", "Essam",
    # Saudi/Gulf popular names
    "Abdullah", "Abdulrahman", "Faisal", "Sultan", "Turki", "Saud", "Nasser",
    "Fahad", "Saleh", "Bandar", "Mishal", "Waleed", "Majed", "Rashed",
    # UAE/Gulf names
    "Rashid", "Saeed", "Hamad", "Zayed", "Khalifa", "Mansoor", "Saif",
    # Common across region
    "Ali", "Ibrahim", "Younis", "Adam", "Hamza", "Bilal", "Fares"
]

ARABIC_FIRST_NAMES_FEMALE = [
    # Egyptian popular names
    "Fatma", "Nour", "Sara", "Mariam", "Hana", "Yasmin", "Dina", "Rania",
    "Aya", "Salma", "Layla", "Heba", "Eman", "Mona", "Nagwa", "Dalia",
    # Saudi/Gulf popular names
    "Noura", "Reem", "Lama", "Dana", "Ghada", "Abeer", "Maha", "Hessa",
    "Lulwa", "Munira", "Haifa", "Alanoud", "Mashael",
    # UAE/Gulf names
    "Aisha", "Shamsa", "Latifa", "Maitha", "Shamma", "Meera",
    # Common across region
    "Amira", "Malak", "Jana", "Lina", "Zeina", "Farah", "Rawia"
]

ARABIC_LAST_NAMES = [
    # Egyptian family names
    "Elsayed", "Ibrahim", "Mohamed", "Ahmed", "Hassan", "Hussein", "Mahmoud",
    "Ali", "Mostafa", "Elsharawy", "Elmasry", "Elgohary", "Elbanna", "Elshamy",
    "Abdelrahman", "Abdelfattah", "Abdelaziz", "Naguib", "Saad", "Farouk",
    # Saudi family names
    "Al-Saud", "Al-Rashid", "Al-Qahtani", "Al-Ghamdi", "Al-Zahrani", "Al-Otaibi",
    "Al-Harbi", "Al-Shehri", "Al-Dossari", "Al-Mutairi", "Al-Anazi", "Al-Subaie",
    # UAE/Gulf family names
    "Al-Maktoum", "Al-Nahyan", "Al-Falasi", "Al-Ketbi", "Al-Nuaimi", "Al-Shamsi",
    "Al-Mazrouei", "Al-Suwaidi", "Al-Hashimi", "Al-Mansouri", "Al-Kaabi",
    # Kuwaiti/Qatari names
    "Al-Sabah", "Al-Thani", "Al-Khalifa", "Al-Jaber", "Al-Kharafi"
]

# ─────────────────────────────────────────────────────────────────────────────
# INDIAN/SOUTH ASIAN NAMES (Large expat community in UAE/KSA)
# ─────────────────────────────────────────────────────────────────────────────
INDIAN_FIRST_NAMES_MALE = [
    "Raj", "Amit", "Rahul", "Vikram", "Suresh", "Anil", "Deepak", "Sanjay",
    "Ravi", "Vijay", "Anand", "Manoj", "Rajesh", "Pradeep", "Ashok", "Nikhil",
    "Arjun", "Rohit", "Karan", "Pranav", "Aditya", "Vivek", "Sachin", "Gaurav"
]

INDIAN_FIRST_NAMES_FEMALE = [
    "Priya", "Anjali", "Sunita", "Pooja", "Neha", "Divya", "Sneha", "Kavita",
    "Meera", "Lakshmi", "Ananya", "Shweta", "Nisha", "Rekha", "Swati", "Aarti",
    "Ritu", "Pallavi", "Shruti", "Deepa", "Geeta", "Radha", "Shalini", "Manisha"
]

INDIAN_LAST_NAMES = [
    "Sharma", "Patel", "Kumar", "Singh", "Gupta", "Reddy", "Nair", "Menon",
    "Verma", "Joshi", "Rao", "Iyer", "Pillai", "Desai", "Shah", "Mehta",
    "Kapoor", "Malhotra", "Chopra", "Agarwal", "Bhatia", "Khanna", "Sinha", "Das"
]

# ─────────────────────────────────────────────────────────────────────────────
# PAKISTANI NAMES (Significant expat community)
# ─────────────────────────────────────────────────────────────────────────────
PAKISTANI_FIRST_NAMES_MALE = [
    "Imran", "Bilal", "Usman", "Zain", "Hamza", "Ali", "Hassan", "Farhan",
    "Saad", "Asad", "Waqar", "Shahid", "Kamran", "Faizan", "Adnan", "Junaid"
]

PAKISTANI_FIRST_NAMES_FEMALE = [
    "Ayesha", "Fatima", "Sana", "Hina", "Mahira", "Zara", "Maryam", "Nadia",
    "Sadia", "Rabia", "Bushra", "Samina", "Farah", "Noor", "Amna", "Sidra"
]

PAKISTANI_LAST_NAMES = [
    "Khan", "Malik", "Chaudhry", "Butt", "Iqbal", "Hussain", "Raza", "Qureshi",
    "Mirza", "Javed", "Baig", "Sheikh", "Siddiqui", "Akhtar", "Nadeem", "Abbasi"
]

# ─────────────────────────────────────────────────────────────────────────────
# FILIPINO NAMES (Large service/retail workforce in UAE)
# ─────────────────────────────────────────────────────────────────────────────
FILIPINO_FIRST_NAMES_MALE = [
    "Jose", "Juan", "Mark", "John Paul", "Jerome", "Kevin", "Bryan", "Ryan",
    "Carlo", "Miguel", "Rafael", "Angelo", "Christian", "Patrick", "Dennis", "Leo"
]

FILIPINO_FIRST_NAMES_FEMALE = [
    "Maria", "Ana", "Grace", "Joy", "Rose", "Cherry", "Michelle", "Nicole",
    "Jennifer", "Jasmine", "Princess", "Angel", "Divine", "Joanne", "Maricel", "Rowena"
]

FILIPINO_LAST_NAMES = [
    "Santos", "Reyes", "Cruz", "Garcia", "Mendoza", "Torres", "Flores", "Gonzales",
    "Ramos", "Bautista", "Villanueva", "Aquino", "Castillo", "Rivera", "Del Rosario", "Dela Cruz"
]

# ─────────────────────────────────────────────────────────────────────────────
# WESTERN NAMES (Business/Professional expats)
# ─────────────────────────────────────────────────────────────────────────────
WESTERN_FIRST_NAMES_MALE = [
    "James", "John", "Michael", "David", "Robert", "William", "Richard", "Thomas",
    "Daniel", "Matthew", "Christopher", "Andrew", "Steven", "Paul", "Mark", "Brian"
]

WESTERN_FIRST_NAMES_FEMALE = [
    "Emma", "Sarah", "Emily", "Jessica", "Jennifer", "Amanda", "Ashley", "Stephanie",
    "Nicole", "Elizabeth", "Rachel", "Lauren", "Megan", "Samantha", "Katherine", "Rebecca"
]

WESTERN_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson",
    "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin", "Thompson", "White"
]

# ─────────────────────────────────────────────────────────────────────────────
# ETHNICITY DISTRIBUTION BY COUNTRY (Realistic market demographics)
# ─────────────────────────────────────────────────────────────────────────────
ETHNICITY_WEIGHTS = {
    # UAE: Very diverse expat population
    'AE': {'arabic': 0.15, 'indian': 0.30, 'pakistani': 0.15, 'filipino': 0.12, 'western': 0.08, 'other_arab': 0.20},
    # KSA: Majority Saudi, growing expat workforce (Vision 2030)
    'SA': {'arabic': 0.55, 'indian': 0.15, 'pakistani': 0.12, 'filipino': 0.08, 'western': 0.05, 'other_arab': 0.05},
    # Egypt: Predominantly Egyptian
    'EG': {'arabic': 0.92, 'indian': 0.02, 'pakistani': 0.01, 'filipino': 0.01, 'western': 0.02, 'other_arab': 0.02},
    # Kuwait: Large expat population
    'KW': {'arabic': 0.30, 'indian': 0.28, 'pakistani': 0.12, 'filipino': 0.12, 'western': 0.05, 'other_arab': 0.13},
    # Qatar: Very high expat ratio
    'QA': {'arabic': 0.12, 'indian': 0.25, 'pakistani': 0.12, 'filipino': 0.15, 'western': 0.10, 'other_arab': 0.26}
}

# Email domains popular in MENA region
MENA_EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "outlook.sa", "hotmail.ae", "yahoo.ae",
    "etisalat.ae", "stc.com.sa", "mobily.com.sa"
]

# Cities per country for more realism
CITIES_BY_COUNTRY = {
    'EG': ['Cairo', 'Alexandria', 'Giza', 'Shubra El Kheima', 'Port Said',
           'Suez', 'Mansoura', 'Tanta', 'Aswan', 'Ismailia', 'Zagazig', 'Luxor',
           '6th of October City', 'New Cairo', 'Hurghada', 'Sharm El Sheikh'],
    'SA': ['Riyadh', 'Jeddah', 'Makkah', 'Madinah', 'Dammam', 'Khobar',
           'Taif', 'Tabuk', 'Buraidah', 'Khamis Mushait', 'Abha', 'Jubail',
           'Yanbu', 'Al Hofuf', 'Najran', 'Hail'],
    'AE': ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Al Ain',
           'Ras Al Khaimah', 'Fujairah', 'Umm Al Quwain'],
    'KW': ['Kuwait City', 'Hawalli', 'Salmiya', 'Farwaniya', 'Ahmadi',
           'Jahra', 'Mangaf', 'Fintas'],
    'QA': ['Doha', 'Al Wakrah', 'Al Khor', 'Lusail', 'Mesaieed',
           'The Pearl', 'West Bay', 'Al Rayyan']
}


def get_name_by_ethnicity(ethnicity: str, gender: str) -> tuple:
    """
    Get first and last name based on ethnicity and gender.
    Returns (first_name, last_name) tuple.
    """
    if ethnicity in ['arabic', 'other_arab']:
        if gender == 'M':
            first_name = random.choice(ARABIC_FIRST_NAMES_MALE)
        else:
            first_name = random.choice(ARABIC_FIRST_NAMES_FEMALE)
        last_name = random.choice(ARABIC_LAST_NAMES)

    elif ethnicity == 'indian':
        if gender == 'M':
            first_name = random.choice(INDIAN_FIRST_NAMES_MALE)
        else:
            first_name = random.choice(INDIAN_FIRST_NAMES_FEMALE)
        last_name = random.choice(INDIAN_LAST_NAMES)

    elif ethnicity == 'pakistani':
        if gender == 'M':
            first_name = random.choice(PAKISTANI_FIRST_NAMES_MALE)
        else:
            first_name = random.choice(PAKISTANI_FIRST_NAMES_FEMALE)
        last_name = random.choice(PAKISTANI_LAST_NAMES)

    elif ethnicity == 'filipino':
        if gender == 'M':
            first_name = random.choice(FILIPINO_FIRST_NAMES_MALE)
        else:
            first_name = random.choice(FILIPINO_FIRST_NAMES_FEMALE)
        last_name = random.choice(FILIPINO_LAST_NAMES)

    else:  # western
        if gender == 'M':
            first_name = random.choice(WESTERN_FIRST_NAMES_MALE)
        else:
            first_name = random.choice(WESTERN_FIRST_NAMES_FEMALE)
        last_name = random.choice(WESTERN_LAST_NAMES)

    return first_name, last_name


def generate_users(num_users: int = None, output_dir: str = None) -> pd.DataFrame:
    """
    Generate synthetic user data with realistic MENA demographics.
    Includes Arabic, Indian, Pakistani, Filipino, and Western names based on country.

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

    print(f"📧 Generating {n:,} Users (Mixed MENA demographics)...")

    users = []

    for i in range(n):
        # Select country based on weights
        country = random.choices(
            config.COUNTRIES, weights=config.COUNTRY_WEIGHTS)[0]
        currency = config.CURRENCY_MAP.get(country, 'USD')

        # Select gender
        gender = random.choice(['M', 'F'])

        # Select ethnicity based on country demographics
        country_demo = ETHNICITY_WEIGHTS.get(country, ETHNICITY_WEIGHTS['EG'])
        ethnicities = list(country_demo.keys())
        weights = list(country_demo.values())
        ethnicity = random.choices(ethnicities, weights=weights)[0]

        # Get appropriate name based on ethnicity and gender
        first_name, last_name = get_name_by_ethnicity(ethnicity, gender)

        # Generate region-appropriate email (or null for noise)
        if random.random() > config.NULL_EMAIL_RATE:
            # Create email from Arabic name (transliterated)
            email_first = first_name.lower().replace("-", "")
            email_last = last_name.lower().replace("-", "").replace("al-", "al")
            email_domain = random.choice(MENA_EMAIL_DOMAINS)
            # Variations: firstname.lastname, firstnamelastname, firstname123
            email_style = random.choice(['dot', 'concat', 'number'])
            if email_style == 'dot':
                email = f"{email_first}.{email_last}@{email_domain}"
            elif email_style == 'concat':
                email = f"{email_first}{email_last}@{email_domain}"
            else:
                email = f"{email_first}{random.randint(1, 999)}@{email_domain}"
        else:
            email = None

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
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone_number": phone,
            "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=65),
            "gender": gender,
            "country": country,
            "city": random.choice(CITIES_BY_COUNTRY.get(country, ['Unknown'])),
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
