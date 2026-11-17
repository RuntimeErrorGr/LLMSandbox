import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Param(BaseModel):
    name: str = Field(description="snake_case parameter name, for example min_count")
    default: str | int | float = Field(description="default value")
    description: str = Field(description="one sentence: what the parameter controls")


class ModuleDesign(BaseModel):
    name: str = Field(description="module name in kebab-case starting with 'detect-'")
    threat: Literal["label_flip", "clean_label"] = Field(description="threat from the catalog")
    title: str = Field(description="short human title of the detector")
    method: str = Field(description="2 to 4 sentences: the detection idea and why it works")
    steps: list[str] = Field(description="3 to 8 concrete algorithm steps for the code")
    params: list[Param] = Field(description="parameters with defaults; must include 'dataset'")
    libraries: list[str] = Field(description="Python libraries used, only from the runner image")

    @field_validator("name")
    @classmethod
    def kebab_case_detector(cls, value: str) -> str:
        name = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
        return name if name.startswith("detect-") else f"detect-{name}"
