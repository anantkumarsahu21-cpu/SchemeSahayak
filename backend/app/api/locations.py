from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_db
from app.models.location import State, District

router = APIRouter(prefix="/locations", tags=["Locations"])

class DistrictResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class StateResponse(BaseModel):
    id: int
    code: str
    name: str
    type: str
    districts: List[DistrictResponse] = []
    model_config = ConfigDict(from_attributes=True)

@router.get("/states", response_model=List[StateResponse])
def list_states(db: Session = Depends(get_db)) -> Any:
    return db.query(State).order_by(State.name).all()

@router.get("/districts/{state_code_or_id}", response_model=List[DistrictResponse])
def get_districts_by_state(state_code_or_id: str, db: Session = Depends(get_db)) -> Any:
    if state_code_or_id.isdigit():
        state = db.query(State).filter(State.id == int(state_code_or_id)).first()
    else:
        state = db.query(State).filter(State.code == state_code_or_id.upper()).first()

    if not state:
        raise HTTPException(status_code=404, detail="State not found")

    return db.query(District).filter(District.state_id == state.id).order_by(District.name).all()
