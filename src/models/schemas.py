import re

from pydantic import BaseModel, Field, field_validator


class ContactPoint(BaseModel):
    email: str
    source_url: str | None = None


class TeamMember(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """
        Reject obviously incomplete or placeholder names.
        """

        value = value.strip()

        if len(value.split()) < 2:
            raise ValueError(
                "Leadership name must contain at least first and last name"
            )

        if not re.fullmatch(
            r"[A-Za-zÀ-ÖØ-öø-ÿ' -]+",
            value,
        ):
            raise ValueError(
                "Leadership name contains invalid characters"
            )

        return value

    role: str
    linkedin_url: str | None = None
    source_url: str | None = None


class CompanyIntelligence(BaseModel):

    @field_validator("company_overview")
    @classmethod
    def clean_overview(cls, value: str) -> str:
        """
        Normalize whitespace in the company overview.
        """

        return " ".join(value.split())

    company_overview: str = Field(
        default="",
        description="A concise two-sentence overview of the company."
    )

    target_audience: list[str] = Field(
        default_factory=list,
        description="The company's target audience or ideal customer profile."
    )

    contact_points: list[ContactPoint] = Field(
        default_factory=list,
        description="Generic or public company email addresses only."
    )

    leadership_team: list[TeamMember] = Field(
        default_factory=list,
        description="Key leadership or team members found in public web content."
    )

    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the extracted company intelligence."
    )