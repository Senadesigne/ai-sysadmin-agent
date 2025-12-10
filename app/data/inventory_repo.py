import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload
from app.data.models import Base, Device, Component

class InventoryRepository:
    def __init__(self, db_path: str = "inventory.db"):
        # Ensure the database is created in the project root or specified path
        # If db_path is just a filename, it will be in the current working directory
        # We might want to make it absolute relative to the app root in a real scenario
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url, echo=False)

    def initialize_db(self):
        """Creates the database tables if they do not exist."""
        Base.metadata.create_all(self.engine)

    def add_device(self, 
                   hostname: str, 
                   device_type: str, 
                   model: str, 
                   serial_number: str, 
                   location: str, 
                   components_data: list[dict],
                   ip_address: str = None,
                   os_family: str = 'linux',
                   auth_method: str = 'ssh_key',
                   ssh_user: str = None,
                   ssh_port: int = 22) -> Device:
        """
        Adds a new device and its components to the database.
        
        Args:
            components_data: List of dicts, e.g. [{'component_type': 'CPU', 'specs': 'Intel Xeon', 'quantity': 2}]
        """
        with Session(self.engine) as session:
            # Check if device already exists (optional, based on simple unique constraints)
            # For now, we assume the caller handles or we let DB raise integrity error
            
            new_device = Device(
                hostname=hostname,
                device_type=device_type,
                model=model,
                serial_number=serial_number,
                location=location,
                ip_address=ip_address,
                os_family=os_family,
                auth_method=auth_method,
                ssh_user=ssh_user,
                ssh_port=ssh_port
            )

            for comp in components_data:
                new_component = Component(
                    component_type=comp['component_type'],
                    specs=comp['specs'],
                    quantity=comp.get('quantity', 1)
                )
                new_device.components.append(new_component)

            session.add(new_device)
            session.commit()
            
            # Eager load components so they are available after session close
            stmt = select(Device).options(selectinload(Device.components)).where(Device.id == new_device.id)
            return session.scalars(stmt).one()

    def get_all_devices(self) -> list[Device]:
        """Returns all devices."""
        with Session(self.engine) as session:
            stmt = select(Device)
            return list(session.scalars(stmt).all())

    def get_device_by_hostname(self, hostname: str) -> Device | None:
        """Finds a device by hostname."""
        with Session(self.engine) as session:
            stmt = select(Device).where(Device.hostname == hostname)
            return session.scalars(stmt).first()

    def bulk_import_from_csv(self, csv_path: str) -> int:
        """
        Imports devices from a CSV file.
        Dynamically stores extra columns in 'extra_specs'.
        """
        import pandas as pd
        import json
        
        try:
            df = pd.read_csv(csv_path)
            # Normalize column names to lowercase/stripped
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            
            # Known fields map
            # Known fields map
            known_fields = ['hostname', 'ip_address', 'model', 'serial_number', 'location', 'device_type', 'os_family', 'auth_method', 'ssh_user', 'ssh_port']
            
            count = 0
            with Session(self.engine) as session:
                for _, row in df.iterrows():
                    hostname = row.get('hostname')
                    if not hostname or pd.isna(hostname):
                        continue 
                        
                    # Check existing
                    if session.scalars(select(Device).where(Device.hostname == hostname)).first():
                        continue
                    
                    # Collect extra specs
                    extra_data = {}
                    for col in df.columns:
                        if col not in known_fields and not pd.isna(row.get(col)):
                            extra_data[col] = str(row.get(col))
                            
                    new_device = Device(
                        hostname=hostname,
                        ip_address=row.get('ip_address') if not pd.isna(row.get('ip_address')) else None,
                        model=row.get('model'),
                        serial_number=str(row.get('serial_number')),
                        location=row.get('location'),
                        device_type=row.get('device_type', 'Server'),
                        os_family=row.get('os_family', 'linux'),
                        auth_method=row.get('auth_method', 'ssh_key'),
                        ssh_user=row.get('ssh_user'),
                        ssh_port=int(row.get('ssh_port', 22)) if not pd.isna(row.get('ssh_port')) else 22,
                        extra_specs=json.dumps(extra_data) if extra_data else None
                    )
                    session.add(new_device)
                    count += 1
                
                session.commit()
            return count
        except Exception as e:
            print(f"Error importing CSV: {e}")
            raise e
