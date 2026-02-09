"""Tests for QuoteComparisonService — get, list, latest, staleness."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.exceptions import NotFoundException
from src.models.enums import TcoCalculationStatus
from src.models.tco_calculation import TcoCalculation
from src.modules.tco.comparison import QuoteComparisonService


def _make_calculation(
    rfq_id: uuid.UUID | None = None,
    status: TcoCalculationStatus = TcoCalculationStatus.COMPLETED,
) -> MagicMock:
    calc = MagicMock(spec=TcoCalculation)
    calc.id = uuid.uuid4()
    calc.rfq_id = rfq_id or uuid.uuid4()
    calc.status = status
    calc.created_at = datetime.now(UTC)
    return calc


def _mock_scalar_one_or_none(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _mock_scalars_all(values):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


class TestGetCalculation:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        db = AsyncMock()
        calc = _make_calculation()
        db.execute.return_value = _mock_scalar_one_or_none(calc)

        service = QuoteComparisonService(db)
        result = await service.get_calculation(calc.id)
        assert result.id == calc.id

    @pytest.mark.asyncio
    async def test_not_found(self) -> None:
        db = AsyncMock()
        db.execute.return_value = _mock_scalar_one_or_none(None)

        service = QuoteComparisonService(db)
        with pytest.raises(NotFoundException):
            await service.get_calculation(uuid.uuid4())


class TestListCalculations:
    @pytest.mark.asyncio
    async def test_returns_all_for_rfq(self) -> None:
        db = AsyncMock()
        rfq_id = uuid.uuid4()
        calcs = [
            _make_calculation(rfq_id=rfq_id),
            _make_calculation(rfq_id=rfq_id),
        ]
        db.execute.return_value = _mock_scalars_all(calcs)

        service = QuoteComparisonService(db)
        result = await service.list_calculations(rfq_id)
        assert len(result) == 2


class TestGetLatestCalculation:
    @pytest.mark.asyncio
    async def test_returns_latest_completed(self) -> None:
        db = AsyncMock()
        rfq_id = uuid.uuid4()
        calc = _make_calculation(rfq_id=rfq_id)
        db.execute.return_value = _mock_scalar_one_or_none(calc)

        service = QuoteComparisonService(db)
        result = await service.get_latest_calculation(rfq_id)
        assert result is not None
        assert result.status == TcoCalculationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_returns_none_when_none_completed(self) -> None:
        db = AsyncMock()
        db.execute.return_value = _mock_scalar_one_or_none(None)

        service = QuoteComparisonService(db)
        result = await service.get_latest_calculation(uuid.uuid4())
        assert result is None


class TestCheckStaleness:
    @pytest.mark.asyncio
    async def test_marks_stale_when_quotes_changed(self) -> None:
        db = AsyncMock()
        calc = _make_calculation(status=TcoCalculationStatus.COMPLETED)

        # First call: get_calculation
        # Second call: count of changed quotes
        mock_count = MagicMock()
        mock_count.scalar.return_value = 2

        db.execute.side_effect = [
            _mock_scalar_one_or_none(calc),
            mock_count,
        ]

        service = QuoteComparisonService(db)
        is_stale = await service.check_staleness(calc.id)

        assert is_stale is True
        assert calc.status == TcoCalculationStatus.STALE
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_stale_when_no_changes(self) -> None:
        db = AsyncMock()
        calc = _make_calculation(status=TcoCalculationStatus.COMPLETED)

        mock_count = MagicMock()
        mock_count.scalar.return_value = 0

        db.execute.side_effect = [
            _mock_scalar_one_or_none(calc),
            mock_count,
        ]

        service = QuoteComparisonService(db)
        is_stale = await service.check_staleness(calc.id)

        assert is_stale is False
