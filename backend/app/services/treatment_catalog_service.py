import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.treatment_cost import TreatmentCost

logger = logging.getLogger("coverwise.services.treatment_catalog")

DATASET_FILE = Path(__file__).resolve().parent.parent / "data" / "treatment_costs.json"


class TreatmentCatalogService:
    """Service for querying and managing synthetic benchmark treatment cost datasets."""

    def __init__(self, data_path: Optional[Path] = None) -> None:
        self.data_path = data_path or DATASET_FILE
        self._cache: Optional[Dict[str, Any]] = None

    def _load_data(self) -> Dict[str, Any]:
        if self._cache is None:
            if not self.data_path.exists():
                logger.warning(f"Treatment costs dataset not found at {self.data_path}")
                return {"metadata": {}, "treatments": []}
            with open(self.data_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
        return self._cache

    def list_benchmark_treatments(self) -> List[Dict[str, Any]]:
        """Return all benchmark treatment definitions."""
        data = self._load_data()
        return data.get("treatments", [])

    def find_treatment(self, query: str) -> Optional[Dict[str, Any]]:
        """Fuzzy/alias search for a treatment in the benchmark catalog."""
        if not query or not query.strip():
            return None

        q_clean = query.strip().lower()
        treatments = self.list_benchmark_treatments()

        # 1. Exact ID match
        for t in treatments:
            if t["treatment_id"].lower() == q_clean:
                return t

        # 2. Exact or substring name match
        for t in treatments:
            if t["treatment_name"].lower() == q_clean or q_clean in t["treatment_name"].lower():
                return t

        # 3. Alias match
        for t in treatments:
            aliases = [a.lower() for a in t.get("aliases", [])]
            if any(q_clean == a or a in q_clean or q_clean in a for a in aliases):
                return t

        # 4. Keyword token match (e.g. "knee", "cataract", "angioplasty")
        tokens = [tok for tok in q_clean.split() if len(tok) >= 3]
        for t in treatments:
            t_text = f"{t['treatment_name']} {' '.join(t.get('aliases', []))}".lower()
            if any(tok in t_text for tok in tokens):
                return t

        return None

    def seed_database_if_empty(self, db: Session) -> int:
        """Seed treatment_costs database table if currently empty."""
        try:
            existing_count = db.query(TreatmentCost).count()
            if existing_count > 0:
                return existing_count

            items = self.list_benchmark_treatments()
            for item in items:
                record = TreatmentCost(
                    treatment_id=item["treatment_id"],
                    treatment_name=item["treatment_name"],
                    category=item["category"],
                    city=item.get("city"),
                    hospital_type=item.get("hospital_type"),
                    inpatient_outpatient=item.get("inpatient_outpatient", "inpatient"),
                    min_cost=float(item["min_cost"]),
                    typical_cost=float(item["typical_cost"]),
                    max_cost=float(item["max_cost"]),
                    currency=item.get("currency", "INR"),
                    length_of_stay_days=int(item.get("length_of_stay_days", 1)),
                    data_source_type=item.get("data_source_type", "synthetic_demo_data"),
                    dataset_version=item.get("dataset_version", "1.0.0"),
                    description=item.get("description"),
                )
                db.add(record)
            db.commit()
            logger.info(f"Seeded {len(items)} synthetic treatment benchmark records into database.")
            return len(items)
        except Exception as exc:
            db.rollback()
            logger.warning(f"Could not seed treatment_costs table: {exc}")
            return 0


# Default singleton instance
default_treatment_catalog_service = TreatmentCatalogService()


def get_treatment_catalog_service() -> TreatmentCatalogService:
    return default_treatment_catalog_service
