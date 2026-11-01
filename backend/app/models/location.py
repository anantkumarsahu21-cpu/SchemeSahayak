from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class State(Base):
    __tablename__ = "states"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(100), unique=True, index=True, nullable=False)
    type = Column(String(20), default="STATE")  # STATE or UT

    districts = relationship("District", back_populates="state", cascade="all, delete-orphan")
    schemes = relationship("Scheme", back_populates="state")

class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)
    state_id = Column(Integer, ForeignKey("states.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False, index=True)

    state = relationship("State", back_populates="districts")
    schemes = relationship("Scheme", back_populates="district")
