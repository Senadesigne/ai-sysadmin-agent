import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.data.inventory_repo import InventoryRepository

def main():
    print("Initialize Database...")
    repo = InventoryRepository()
    
    # 1. Create Tables
    repo.initialize_db()
    print("Tables created successfully.")
    
    # 2. Import CSV
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'sample_inventory.csv')
    csv_path = os.path.abspath(csv_path)
    
    if os.path.exists(csv_path):
        print(f"Importing inventory from {csv_path}...")
        try:
            count = repo.bulk_import_from_csv(csv_path)
            print(f"Successfully imported {count} devices.")
        except Exception as e:
            print(f"Failed to import CSV: {e}")
    else:
        print(f"CSV file not found at {csv_path}")

if __name__ == "__main__":
    main()
