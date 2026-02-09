"""Template service — vessel-type, voyage-type, and event templates.

Returns applicable templates and delegates quantity computation to the
ConsumptionEngine when a template is applied.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundException
from src.modules.prediction.constants import (
    EVENT_TEMPLATES,
    VESSEL_TYPE_TEMPLATES,
    VOYAGE_TYPE_TEMPLATES,
)
from src.modules.prediction.consumption_engine import ConsumptionEngine
from src.modules.prediction.schemas import PredictedItem, TemplateResponse


class TemplateService:
    """List and apply procurement templates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_templates(
        self,
        vessel_type: str | None = None,
        voyage_days: int | None = None,
    ) -> list[TemplateResponse]:
        """Return templates filtered by vessel type and/or voyage duration.

        Combines vessel-type templates, voyage-type templates, and event
        templates into a single list.  Filters are applied when provided.
        """
        templates: list[TemplateResponse] = []

        # Vessel-type templates
        for type_key, template_data in VESSEL_TYPE_TEMPLATES.items():
            if vessel_type and type_key != vessel_type:
                continue
            templates.append(
                TemplateResponse(
                    id=f"VESSEL_{type_key}",
                    name=template_data["name"],
                    description=template_data["description"],
                    vessel_types=[type_key],
                    categories=template_data["categories"],
                    voyage_type=None,
                )
            )

        # Voyage-type templates
        for voyage_key, voyage_data in VOYAGE_TYPE_TEMPLATES.items():
            if voyage_days is not None and voyage_days > voyage_data["max_days"]:
                continue
            templates.append(
                TemplateResponse(
                    id=f"VOYAGE_{voyage_key}",
                    name=voyage_data["name"],
                    description=f"Up to {voyage_data['max_days']} days",
                    vessel_types=[],
                    categories=[],
                    voyage_type=voyage_key,
                )
            )

        # Event templates (always included — not filtered by vessel/voyage)
        for event_key, event_data in EVENT_TEMPLATES.items():
            templates.append(
                TemplateResponse(
                    id=f"EVENT_{event_key}",
                    name=event_data["name"],
                    description=event_data["description"],
                    vessel_types=[],
                    categories=event_data["categories"],
                    voyage_type=None,
                )
            )

        return templates

    async def apply_template(
        self,
        template_id: str,
        vessel_id: uuid.UUID,
        voyage_days: int,
        crew_size: int,
    ) -> list[PredictedItem]:
        """Apply a template: resolve its categories then run the consumption engine.

        Template ID format:
        - ``VESSEL_TANKER`` — vessel-type template
        - ``VOYAGE_COASTAL`` — voyage-type template (uses all categories with adjustment)
        - ``EVENT_DRYDOCK`` — event template
        """
        categories = self._resolve_template_categories(template_id)

        engine = ConsumptionEngine(self.db)
        return await engine.predict_quantities(
            vessel_id=vessel_id,
            voyage_days=voyage_days,
            crew_size=crew_size,
            categories=categories if categories else None,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_template_categories(template_id: str) -> list[str]:
        """Resolve a template ID to a list of IMPA category prefixes."""
        parts = template_id.split("_", 1)
        if len(parts) != 2:
            raise NotFoundException(f"Template '{template_id}' not found")

        template_type, template_key = parts

        if template_type == "VESSEL":
            template_data = VESSEL_TYPE_TEMPLATES.get(template_key)
            if template_data is None:
                raise NotFoundException(f"Vessel template '{template_key}' not found")
            return template_data["categories"]

        if template_type == "VOYAGE":
            voyage_data = VOYAGE_TYPE_TEMPLATES.get(template_key)
            if voyage_data is None:
                raise NotFoundException(f"Voyage template '{template_key}' not found")
            # Voyage templates use all categories (the engine handles adjustments)
            return []

        if template_type == "EVENT":
            event_data = EVENT_TEMPLATES.get(template_key)
            if event_data is None:
                raise NotFoundException(f"Event template '{template_key}' not found")
            return event_data["categories"]

        raise NotFoundException(f"Template '{template_id}' not found")
