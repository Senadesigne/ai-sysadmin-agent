import sys
import os

# Add the project root to the python path so imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.data.inventory_repo import InventoryRepository

def test_db_setup():
    print("Inicijalizacija InventoryRepository...")
    # Initialize repo (creates inventory.db in root by default)
    repo = InventoryRepository()
    
    print("Kreiranje tablica (initialize_db)...")
    repo.initialize_db()
    
    print("Dodavanje testnog uređaja...")
    try:
        device = repo.add_device(
            hostname="Test-Server-01",
            device_type="Server",
            model="HPE ProLiant Gen10",
            serial_number="TEST-SN-12345",
            location="Room A",
            components_data=[
                {'component_type': 'CPU', 'specs': 'Intel Xeon Gold', 'quantity': 2},
                {'component_type': 'RAM', 'specs': '64GB DDR4', 'quantity': 4}
            ],
            ip_address="192.168.1.10"
        )
        print(f"Uređaj dodan: ID={device.id}, Hostname={device.hostname}")
        print("Komponente:")
        for c in device.components:
            print(f" - {c.component_type}: {c.specs} (Qty: {c.quantity})")
            
        print("\nUSPJEH: Baza kreirana i uređaj dodan.")
        
    except Exception as e:
        print(f"\nGREŠKA prilikom dodavanja uređaja: {e}")

if __name__ == "__main__":
    test_db_setup()
