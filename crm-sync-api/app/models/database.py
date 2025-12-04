from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config.settings import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Mantenimiento(Base):
    __tablename__ = "mantenimientos"
    __table_args__ = {"schema": "monitoreo_equipos"}
    ods_name = Column(Text, primary_key=True, nullable=False)
    maintenance_type = Column(Text)
    device_id = Column(Text)
    device_name = Column(Text)
    device_brand = Column(Text)
    device_model = Column(Text)
    device_type = Column(Text)
    datetime_ods_create = Column(DateTime)
    serial = Column(Text)
    report_id = Column(Text)
    datetime_maintenance_end = Column(DateTime)
    maintenance_remarks = Column(Text)
    report_status = Column(Text)
    nit = Column(Text)
    customer_name = Column(Text)
    
    def to_dict(self):
        return {
            'ods_name': self.ods_name,
            'maintenance_type': self.maintenance_type,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_brand': self.device_brand,
            'device_model': self.device_model,
            'device_type': self.device_type,
            'datetime_ods_create': self.datetime_ods_create.isoformat() if self.datetime_ods_create else None,
            'serial': self.serial,
            'report_id': self.report_id,
            'datetime_maintenance_end': self.datetime_maintenance_end.isoformat() if self.datetime_maintenance_end else None,
            'maintenance_remarks': self.maintenance_remarks,
            'report_status': self.report_status,
            'nit': self.nit,
            'customer_name': self.customer_name
        }

def init_db():
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()