from pathlib import Path
import pandas as pd
import hashlib
import re
from faker import Faker

def redact_csv(input_path, output_path, locale='en_US'):
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    df = pd.read_csv(input_path)
    fake = Faker(locale)

    def apply_techniques(row):
        # 1. Suppression
        if 'plate' in row:
            row['plate'] = '[REDACTED]'
        
        # 2. Hashing
        if 'personal_id' in row and not pd.isna(row['personal_id']):
            salt = "turku_sme_project_2026"
            hashed_id = hashlib.sha256((str(row['personal_id']) + salt).encode()).hexdigest()
            row['personal_id'] = hashed_id[:10]
        
        # 3. Surrogate Substitution (Seeded for Consistency across multiple fields)
        if 'name' in row and not pd.isna(row['name']):
            original_name = str(row['name'])
            seed_number = int(hashlib.md5(original_name.encode()).hexdigest(), 16) % (10**8)
            Faker.seed(seed_number) 
            
            row['name'] = fake.name()
            if 'email' in row and not pd.isna(row['email']):
                row['email'] = fake.email()
            if 'phone' in row and not pd.isna(row['phone']):
                row['phone'] = fake.phone_number()
            if 'company' in row and not pd.isna(row['company']):
                row['company'] = fake.company()
            if 'iban' in row and not pd.isna(row['iban']):
                row['iban'] = fake.iban()
        
        # 4. Generalization
        if 'address' in row:
            address = row['address']
            if pd.isna(address): 
                row['address'] = "No Address Provided"
            else:
                if locale == 'fi_FI':
                    city_match = re.search(r'\d{5}\s+(.*)', str(address))
                    row['address'] = city_match.group(1).strip() if city_match else "Unknown City"
                else:
                    state_match = re.search(r'\b([A-Z]{2})\b \d{5}', str(address))
                    row['address'] = state_match.group(1) if state_match else "Unknown State"
        
        return row

    anonymized_df = df.apply(apply_techniques, axis=1)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    anonymized_df.to_csv(output_path, index=False)
    
    print("\nRedacted CSV saved to:")
    print(output_path)

if __name__ == "__main__":
    input_path = input("Enter original CSV file path: ").strip().strip('"')
    output_path = input("Enter output CSV file path: ").strip().strip('"')
    locale_choice = input("Enter locale (e.g., 'en_US' or 'fi_FI'): ").strip()
    
    redact_csv(input_path, output_path, locale_choice)