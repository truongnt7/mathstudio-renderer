"""Base classes for template parameter models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TemplateParameters(BaseModel):
    """Base class for all template parameter models.

    All subclasses must set ``extra="forbid"`` to prevent injection of
    arbitrary parameters from request data.
    """

    model_config = ConfigDict(extra="forbid")


class EmptyParameters(TemplateParameters):
    """Parameter model for templates that accept no parameters."""

    model_config = ConfigDict(extra="forbid")
