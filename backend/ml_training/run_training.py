"""CLI entrypoint for running a full training job.

Usage:
    python -m ml_training.run_training --dataset ml_training/datasets/sample_messages.csv \
        --version v1 --artifacts-dir artifacts

This is the composition root for the offline pipeline: the only place in
`ml_training` that constructs concrete classes directly. Everything else
in the package receives its collaborators via constructor injection.
"""
import argparse
import logging
import sys

from ml_common.preprocessing.pipeline import TextPreprocessingPipeline
from ml_common.registry.model_registry import ModelRegistry
from ml_training.config import TrainingConfig
from ml_training.data.loader import DatasetLoader, DatasetSource, LoaderConfig
from ml_training.data.validator import DatasetValidator
from ml_training.evaluation.evaluator import ModelEvaluator
from ml_common.features.tfidf_vectorizer import TfidfFeatureExtractor
from ml_training.training.train_pipeline import TrainingPipeline, default_trainers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ml_training.run_training")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and register scam-detection models")
    parser.add_argument(
        "--dataset",
        action="append",
        required=True,
        help="Path to a labeled CSV dataset (text,label columns). Repeatable to merge sources.",
    )
    parser.add_argument("--version", required=True, help="Version tag to register artifacts under")
    parser.add_argument("--artifacts-dir", default="artifacts", help="Root directory for artifact storage")
    parser.add_argument(
        "--no-promote",
        action="store_true",
        help="Register the winning model without promoting it to production",
    )
    return parser.parse_args(argv)


def build_pipeline(dataset_paths: list[str], artifacts_dir: str) -> TrainingPipeline:
    config = TrainingConfig(artifacts_dir=artifacts_dir)

    loader = DatasetLoader(
        LoaderConfig(sources=[DatasetSource(path=path) for path in dataset_paths])
    )
    validator = DatasetValidator()
    preprocessor = TextPreprocessingPipeline()
    vectorizer = TfidfFeatureExtractor(config.tfidf)
    trainers = default_trainers(config)
    evaluator = ModelEvaluator()
    registry = ModelRegistry(root_dir=artifacts_dir)

    return TrainingPipeline(
        config=config,
        loader=loader,
        validator=validator,
        preprocessor=preprocessor,
        vectorizer=vectorizer,
        trainers=trainers,
        evaluator=evaluator,
        registry=registry,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pipeline = build_pipeline(args.dataset, args.artifacts_dir)

    logger.info("Starting training run version=%s datasets=%s", args.version, args.dataset)
    result = pipeline.run(version=args.version, promote_winner=not args.no_promote)

    logger.info(
        "Training complete: train_rows=%d test_rows=%d vocabulary_size=%d",
        result.train_rows,
        result.test_rows,
        result.vocabulary_size,
    )
    for candidate in result.candidates:
        logger.info(
            "  %-20s accuracy=%.3f precision=%.3f recall=%.3f f1=%.3f roc_auc=%.3f fpr=%.3f",
            candidate.model_name,
            candidate.metrics.accuracy,
            candidate.metrics.precision,
            candidate.metrics.recall,
            candidate.metrics.f1,
            candidate.metrics.roc_auc,
            candidate.metrics.false_positive_rate,
        )
    logger.info(
        "Winner: %s (f1=%.3f) registered as version=%s%s",
        result.winner.model_name,
        result.winner.metrics.f1,
        args.version,
        "" if args.no_promote else " and promoted to production",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
