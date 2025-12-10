from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), unique=True)
    device_type: Mapped[str] = mapped_column(String(50))  # e.g., 'Server', 'Switch'
    model: Mapped[str] = mapped_column(String(100))
    serial_number: Mapped[str] = mapped_column(String(100), unique=True)
    location: Mapped[str] = mapped_column(String(100))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    # Stores flexible JSON data for extra columns (CPU, RAM, Role, etc.)
    extra_specs: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Connection Details
    os_family: Mapped[str] = mapped_column(String(50), default='linux') # linux, windows, network_ios
    auth_method: Mapped[str] = mapped_column(String(50), default='ssh_key') # ssh_key, password
    ssh_user: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22)

    # One-to-many relationship with components
    components: Mapped[List["Component"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Device(hostname='{self.hostname}', model='{self.model}')>"

class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    component_type: Mapped[str] = mapped_column(String(50))  # e.g., 'CPU', 'RAM'
    specs: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    device: Mapped["Device"] = relationship(back_populates="components")

    def __repr__(self) -> str:
        return f"<Component(type='{self.component_type}', specs='{self.specs}')>"
