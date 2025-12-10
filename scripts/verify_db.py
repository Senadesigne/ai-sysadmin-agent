import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.data.inventory_repo import InventoryRepository
from sqlalchemy import text

def main():
    print("Verifying Database...")
    repo = InventoryRepository()
    
    try:
        devices = repo.get_all_devices()
        print(f"Total Devices in DB: {len(devices)}")
        
        for d in devices:
            print(f" - {d.hostname} ({d.ip_address}) [{d.model}]")
            
        print("Verification Successful.")
    except Exception as e:
        print(f"Verification Failed: {e}")

if __name__ == "__main__":
    main()
