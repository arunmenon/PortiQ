"""Unit conversion service — 3-tier lookup (product → category → universal)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundException, ValidationException
from src.models.enums import UnitType
from src.models.unit import UnitConversion, UnitOfMeasure
from src.modules.product.schemas import ConversionResult, UnitConversionCreate


class UnitConversionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def convert(
        self,
        value: Decimal,
        from_unit: str,
        to_unit: str,
        category_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
    ) -> ConversionResult:
        """Convert *value* between units using the 3-tier lookup hierarchy.

        Lookup order:
        1. Product-specific conversion
        2. Category-specific conversion
        3. Universal (no product/category) conversion
        4. Transitive via base_unit

        Raises :class:`ValidationException` when no conversion path exists.
        """
        if from_unit == to_unit:
            return ConversionResult(
                original_value=value,
                converted_value=value,
                conversion_factor=Decimal("1"),
                conversion_path=[from_unit],
            )

        # Direct lookup through 3 tiers
        factor = await self._find_direct_factor(from_unit, to_unit, product_id, category_id)
        if factor is not None:
            return ConversionResult(
                original_value=value,
                converted_value=value * factor,
                conversion_factor=factor,
                conversion_path=[from_unit, to_unit],
            )

        # Try reverse direction
        factor = await self._find_direct_factor(to_unit, from_unit, product_id, category_id)
        if factor is not None:
            inverse = Decimal("1") / factor
            return ConversionResult(
                original_value=value,
                converted_value=value * inverse,
                conversion_factor=inverse,
                conversion_path=[from_unit, to_unit],
            )

        # Transitive via base_unit
        result = await self._try_transitive(value, from_unit, to_unit, product_id, category_id)
        if result is not None:
            return result

        raise ValidationException(
            message=f"No conversion path from '{from_unit}' to '{to_unit}'",
        )

    async def _find_direct_factor(
        self,
        from_unit: str,
        to_unit: str,
        product_id: uuid.UUID | None,
        category_id: uuid.UUID | None,
    ) -> Decimal | None:
        """Search product → category → universal tiers for a direct factor."""
        tiers: list[tuple[uuid.UUID | None, uuid.UUID | None]] = []
        if product_id is not None:
            tiers.append((product_id, category_id))
        if category_id is not None:
            tiers.append((None, category_id))
        tiers.append((None, None))

        for p_id, c_id in tiers:
            stmt = select(UnitConversion.conversion_factor).where(
                UnitConversion.from_unit == from_unit,
                UnitConversion.to_unit == to_unit,
            )
            if p_id is not None:
                stmt = stmt.where(UnitConversion.product_id == p_id)
            else:
                stmt = stmt.where(UnitConversion.product_id.is_(None))
            if c_id is not None:
                stmt = stmt.where(UnitConversion.category_id == c_id)
            else:
                stmt = stmt.where(UnitConversion.category_id.is_(None))

            result = await self._session.execute(stmt)
            factor = result.scalar_one_or_none()
            if factor is not None:
                return factor
        return None

    async def _try_transitive(
        self,
        value: Decimal,
        from_unit: str,
        to_unit: str,
        product_id: uuid.UUID | None,
        category_id: uuid.UUID | None,
    ) -> ConversionResult | None:
        """Attempt conversion via the base_unit of from_unit or to_unit's unit type."""
        # Try from_unit's base first, then to_unit's base
        for pivot_unit_code in (from_unit, to_unit):
            stmt = select(UnitOfMeasure.base_unit).where(UnitOfMeasure.code == pivot_unit_code)
            result = await self._session.execute(stmt)
            base = result.scalar_one_or_none()
            if base is None or base == from_unit or base == to_unit:
                continue

            # from_unit → base
            factor_a = await self._find_direct_factor(from_unit, base, product_id, category_id)
            if factor_a is None:
                factor_a_rev = await self._find_direct_factor(base, from_unit, product_id, category_id)
                if factor_a_rev is not None:
                    factor_a = Decimal("1") / factor_a_rev
            if factor_a is None:
                continue

            # base → to_unit
            factor_b = await self._find_direct_factor(base, to_unit, product_id, category_id)
            if factor_b is None:
                factor_b_rev = await self._find_direct_factor(to_unit, base, product_id, category_id)
                if factor_b_rev is not None:
                    factor_b = Decimal("1") / factor_b_rev
            if factor_b is None:
                continue

            combined = factor_a * factor_b
            return ConversionResult(
                original_value=value,
                converted_value=value * combined,
                conversion_factor=combined,
                conversion_path=[from_unit, base, to_unit],
            )

        return None

    async def list_units(self, unit_type: UnitType | None = None) -> list[UnitOfMeasure]:
        stmt = select(UnitOfMeasure).order_by(UnitOfMeasure.display_order)
        if unit_type is not None:
            stmt = stmt.where(UnitOfMeasure.unit_type == unit_type)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_conversion(self, data: UnitConversionCreate) -> UnitConversion:
        conversion = UnitConversion(
            from_unit=data.from_unit,
            to_unit=data.to_unit,
            conversion_factor=data.conversion_factor,
            category_id=data.category_id,
            product_id=data.product_id,
        )
        self._session.add(conversion)
        await self._session.flush()
        return conversion

    async def list_conversions(
        self,
        from_unit: str | None = None,
        category_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
    ) -> list[UnitConversion]:
        stmt = select(UnitConversion)
        if from_unit is not None:
            stmt = stmt.where(UnitConversion.from_unit == from_unit)
        if category_id is not None:
            stmt = stmt.where(UnitConversion.category_id == category_id)
        if product_id is not None:
            stmt = stmt.where(UnitConversion.product_id == product_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
