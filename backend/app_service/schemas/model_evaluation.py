from pydantic import BaseModel, ConfigDict


class ConfusionMatrix(BaseModel):
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int


class ModelEvaluationEntry(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    version: str
    is_production: bool
    trained_at: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    false_positive_rate: float
    confusion_matrix: ConfusionMatrix
    train_rows: int
    test_rows: int
    dataset_size: int
    # Explicit, real limitation text -- not boilerplate, an actual
    # statement about THIS entry's real sample size. None only when
    # dataset_size is genuinely unknown (pre-Phase-15 registry entries
    # that predate this field).
    dataset_limitation_note: str | None = None
