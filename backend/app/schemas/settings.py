from pydantic import BaseModel, Field, ConfigDict

class DensitySettingsBase(BaseModel):
    density_factor_ab: float = Field(..., gt=0)
    density_factor_dp: float = Field(..., gt=0)


class DensitySettingsUpdateIn(DensitySettingsBase):
    comment: str | None = None


class DensitySettingsOut(DensitySettingsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class FuelCoeffHistoryOut(BaseModel):
    id: int
    fuel_type: str
    density_kg_per_l: float
    changed_by: int | None = None
    changed_at: str | None = None
    comment: str | None = None
