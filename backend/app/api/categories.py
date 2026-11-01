from typing import List, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_db
from app.models.category import Category

router = APIRouter(prefix="/categories", tags=["Categories"])

class CategoryResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    icon: str
    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)) -> Any:
    return db.query(Category).all()
