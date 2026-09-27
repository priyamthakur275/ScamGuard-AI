from sqlalchemy.orm import Session

from app_service.core.exceptions import NotFoundError
from app_service.schemas.message import AnalysisResult
from app_service.services.demo_examples import DEMO_EXAMPLES, get_demo_example
from app_service.services.extraction import ExtractionService
from app_service.services.message_service import MessageService


class DemoService:
    """Runs a catalog example through the SAME real extraction + ML/XAI
    pipeline a genuine scan uses (ExtractionService.extract then
    MessageService.analyze_ephemeral) -- the only difference from a real
    scan is that analyze_ephemeral never writes to the database. This is
    not a simplified or parallel demo pipeline; it is a deliberate,
    minimal wrapper around the exact same real one.
    """

    def __init__(self, db: Session):
        self.message_service = MessageService(db)

    @staticmethod
    def list_examples() -> list[dict]:
        return [
            {"id": e.id, "label": e.label, "category": e.category, "input_type": e.input_type}
            for e in DEMO_EXAMPLES
        ]

    def run_example(self, example_id: str) -> AnalysisResult:
        example = get_demo_example(example_id)
        if example is None:
            raise NotFoundError(f"Unknown demo example '{example_id}'.")

        extracted_text, metadata = ExtractionService.extract(None, example.text, example.input_type)
        # Embedded directly in the result's own metadata (not just known by
        # context in the frontend) so this can never be mistaken for a real
        # scan even if the result object ends up rendered through a shared
        # component -- "never present fabricated demo outputs as live
        # production scans" extends to never letting a genuine demo output
        # look unlabeled, too.
        metadata = {**(metadata or {}), "is_demo": True, "demo_example_id": example.id}
        result = self.message_service.analyze_ephemeral(extracted_text, example.input_type, metadata)
        return result
