from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.treatment import Treatment
from app.repositories.treatment_repository import TreatmentRepository
from app.schemas.treatment import TreatmentCreate, TreatmentResponse

logger = get_logger("coverwise.api.treatments")

router = APIRouter(prefix="/treatments", tags=["Treatments Catalog"])

# Initial benchmark catalog seeded automatically if table is empty
DEFAULT_TREATMENTS = [
    {
        "name": "Cataract Surgery",
        "category": "Ophthalmology",
        "description": "Day-care phacoemulsification with intraocular lens (IOL) implantation.",
        "typical_cost_min": 30000.0,
        "typical_cost_max": 75000.0,
    },
    {
        "name": "Total Knee Replacement",
        "category": "Orthopedics",
        "description": "Unilateral or bilateral total knee arthroplasty with prosthetic implant.",
        "typical_cost_min": 180000.0,
        "typical_cost_max": 350000.0,
    },
    {
        "name": "Coronary Angioplasty / Stenting",
        "category": "Cardiology",
        "description": "Percutaneous transluminal coronary angioplasty (PTCA) with drug-eluting stent.",
        "typical_cost_min": 120000.0,
        "typical_cost_max": 280000.0,
    },
    {
        "name": "Appendectomy",
        "category": "General Surgery",
        "description": "Laparoscopic or open surgical removal of the vermiform appendix.",
        "typical_cost_min": 45000.0,
        "typical_cost_max": 95000.0,
    },
    {
        "name": "Hernia Repair",
        "category": "General Surgery",
        "description": "Laparoscopic mesh repair of inguinal or umbilical hernia.",
        "typical_cost_min": 50000.0,
        "typical_cost_max": 110000.0,
    },
    {
        "name": "Rhinoplasty / Cosmetic Correction",
        "category": "Cosmetics",
        "description": "Elective cosmetic nasal reshaping procedure.",
        "typical_cost_min": 80000.0,
        "typical_cost_max": 200000.0,
    },
]


def seed_treatments_if_empty(db: Session) -> None:
    """Ensure standard benchmark catalog treatments exist on startup or first query."""
    repo = TreatmentRepository(db)
    if repo.count() == 0:
        logger.info("Treatments catalog empty. Seeding initial benchmark procedures...")
        for item in DEFAULT_TREATMENTS:
            repo.create(
                name=item["name"],
                category=item["category"],
                description=item["description"],
                typical_cost_min=item["typical_cost_min"],
                typical_cost_max=item["typical_cost_max"],
            )
        logger.info(f"Seeded {len(DEFAULT_TREATMENTS)} initial benchmark treatments.")


@router.get("", response_model=List[TreatmentResponse])
def list_treatments(
    q: Optional[str] = Query(None, description="Search by treatment name or description"),
    category: Optional[str] = Query(None, description="Filter by clinical category"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    db: Session = Depends(get_db),
) -> List[TreatmentResponse]:
    """Retrieve catalog of medical procedures with typical cost benchmarks."""
    seed_treatments_if_empty(db)
    repo = TreatmentRepository(db)
    return repo.list(q=q, category=category, skip=skip, limit=limit)


@router.get("/{treatment_id}", response_model=TreatmentResponse)
def get_treatment(
    treatment_id: int,
    db: Session = Depends(get_db),
) -> TreatmentResponse:
    """Retrieve a specific medical treatment catalog record by ID."""
    repo = TreatmentRepository(db)
    treatment = repo.get_by_id(treatment_id)
    if not treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment with ID {treatment_id} not found.",
        )
    return treatment


@router.post("", response_model=TreatmentResponse, status_code=status.HTTP_201_CREATED)
def create_treatment(
    payload: TreatmentCreate,
    db: Session = Depends(get_db),
) -> TreatmentResponse:
    """Add a new medical procedure and its benchmark costs to the catalog."""
    repo = TreatmentRepository(db)
    existing = repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A treatment named '{payload.name}' already exists in the catalog.",
        )

    treatment = repo.create(
        name=payload.name,
        category=payload.category,
        description=payload.description,
        typical_cost_min=payload.typical_cost_min,
        typical_cost_max=payload.typical_cost_max,
    )
    logger.info(f"Created treatment '{treatment.name}' (ID {treatment.id})")
    return treatment
