import os
import json

from dotenv import load_dotenv
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.schemas import (
    CompanyIntelligence,
    TeamMember,
)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count from character count.

    This is an approximation intended for cost monitoring,
    not an exact tokenizer count.
    """

    return max(1, len(text) // 4)

def estimate_input_cost(tokens: int) -> float:
    """
    Estimate input API cost in USD.

    The rate is configurable through the environment file.
    """

    rate = float(
        os.getenv(
            "GROQ_INPUT_COST_PER_MILLION_TOKENS",
            "0"
        )
    )

    return (tokens / 1_000_000) * rate

load_dotenv()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(
        multiplier=1,
        min=2,
        max=8
    ),
)
def extract_company_intelligence(
    website_content: str,
    extracted_emails: dict[str, str] | None = None,
) -> CompanyIntelligence:
    """
    Extract structured company intelligence from cleaned website content.
    """

    client = Groq(
        api_key=os.getenv("GROQ_API_KEY")
    )

    extracted_emails = extracted_emails or {}

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                   "You are a company research and lead enrichment agent. "
                   "company_overview MUST contain exactly two concise sentences "
                   "describing what the company does, based only on the provided evidence. "
                   "If the evidence is sufficient, never leave company_overview empty. "
                   "Analyze the provided website content and return valid JSON "
                   "matching the requested schema. "
                   "Extract only information explicitly supported by the evidence. "
                   "Do not invent names, emails, roles, or LinkedIn URLs. "
                   "For target_audience, return a JSON array of audience segments. "
                   "Deterministically extracted emails are provided separately and should be "
                   "used when supported by the crawled evidence. "
                   "For contact_points, include ONLY generic or public company email addresses. "
                   "Each contact point MUST be a JSON object with exactly these fields: "
                   "email and source_url. "
                   "email must contain the email address. "
                   "source_url should contain the URL of the page where the email was found, "
                   "or null if the source URL cannot be determined. "
                   "Do not return contact points as plain strings. "
                   "Do not include phone numbers, physical addresses, or other contact types. "
                   "For leadership_team, include a person ONLY when the person's full name "
                   "and leadership/team role are explicitly stated in the provided website evidence. "
                   "Do not infer, guess, or derive a person's role from context. "
                   "Do not include people mentioned only in testimonials, customer stories, blog posts, "
                   "press mentions, or unrelated content unless the evidence explicitly identifies "
                   "them as a company leader or team member. "
                   "Prefer official company About, Team, Company, or Leadership pages when available. "
                   "If no leadership/team member is explicitly supported by the evidence, return []. "
                   "LinkedIn URLs should only be included when explicitly available in the evidence. "
                   "source_url MUST be the URL of the provided page that supports the person's name "
                   "and role. If no supporting source URL exists, do not include the person. "
                   "For list fields with no information, return []. "
                   "The confidence_score must be a number between 0.0 and 1.0."
               ),
            },
            {
                "role": "user",
                "content": (
                    "Extract company intelligence from the following "
                    "website content.\n\n"
                    f"{website_content}\n\n"
                    "Deterministically extracted public emails with source URLs:\n"
                    f"{extracted_emails}"
                ),
            },
        ],
        response_format={
            "type": "json_object"
        },
    )

  

    raw_data = json.loads(
        response.choices[0].message.content
    )

    valid_team = []

    for member in raw_data.get("leadership_team", []):
        try:
            validated_member = TeamMember.model_validate(member)
            valid_team.append(validated_member.model_dump())
        except Exception:
            continue

    raw_data["leadership_team"] = valid_team

    return CompanyIntelligence.model_validate(raw_data)