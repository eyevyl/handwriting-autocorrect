"""Smoke tests for the initial package structure."""

import importlib


MODULES = (
    "handwriting",
    "handwriting.goodnotes.extraction",
    "handwriting.dataset.pipeline",
    "handwriting.models.base",
    "handwriting.training.runner",
    "handwriting.evaluation.metrics",
    "handwriting.visualization.render",
)


def test_research_modules_import():
    for module_name in MODULES:
        assert importlib.import_module(module_name) is not None
