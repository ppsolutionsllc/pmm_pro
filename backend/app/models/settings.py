from sqlalchemy import Column, Integer, Float

from app.models.base import Base

class DensitySettings(Base):
    __tablename__ = "density_settings"
    id = Column(Integer, primary_key=True, index=True)
    density_factor_ab = Column(Float, nullable=False)
    density_factor_dp = Column(Float, nullable=False)
