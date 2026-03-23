"""Shared test fixtures for session-scoped dataset caching."""

import pytest

from parserf.models import FaultModel, FaultModelDataset


@pytest.fixture(scope="session", params=list(FaultModel))
def dataset(request):
    """Session-scoped FaultModelDataset, one per fault model."""
    return FaultModelDataset(request.param)


@pytest.fixture(scope="session")
def dataset_31():
    """Session-scoped FaultModelDataset for UCERF3 fault model 3.1."""
    return FaultModelDataset(FaultModel.UCERF3_31)
