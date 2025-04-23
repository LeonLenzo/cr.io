from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Freezer(Base):
    __tablename__ = "freezers"

    name = Column(String, primary_key=True)
    racks = relationship("Rack", back_populates="freezer", cascade="all, delete-orphan")

class Rack(Base):
    __tablename__ = "racks"

    id = Column(String, primary_key=True)
    freezer_name = Column(String, ForeignKey("freezers.name", ondelete="CASCADE"), nullable=False)
    rows = Column(Integer)
    columns = Column(Integer)

    freezer = relationship("Freezer", back_populates="racks")
    boxes = relationship("Box", back_populates="rack", cascade="all, delete-orphan")

class Box(Base):
    __tablename__ = "boxes"

    # Composite primary key
    id = Column(String, primary_key=True)
    rack_id = Column(String, ForeignKey("racks.id", ondelete="CASCADE"), primary_key=True)
    freezer_name = Column(String, ForeignKey("freezers.name", ondelete="CASCADE"), primary_key=True)
    
    box_name = Column(String)
    assigned_user = Column(String)
    rows = Column(Integer)
    columns = Column(Integer)

    rack = relationship("Rack", back_populates="boxes")
    samples = relationship("Sample", back_populates="box_ref", cascade="all, delete-orphan")

class Sample(Base):
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sample_name = Column(String)
    sample_type = Column(String)
    well = Column(String)
    owner = Column(String)
    date_added = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    species = Column(String)
    resistance = Column(String)
    regulation = Column(String)

    # Add these fields to match your queries
    freezer = Column(String, nullable=False)
    rack = Column(String, nullable=False)
    box = Column(String, nullable=False)
    
    # Keep the relationship to Box
    box_id = Column(String, nullable=False)
    rack_id = Column(String, nullable=False)
    freezer_name = Column(String, nullable=False)
    
    __table_args__ = (
        ForeignKeyConstraint(
            ['box_id', 'rack_id', 'freezer_name'],
            ['boxes.id', 'boxes.rack_id', 'boxes.freezer_name'],
            ondelete="CASCADE"
        ),
    )
    
    box_ref = relationship("Box", back_populates="samples")