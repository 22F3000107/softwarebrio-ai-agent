import argparse
import csv
import json
from pathlib import Path

from src.browser.crawler import crawl_website
from src.extraction.content_cleaner import (
    extract_emails,
    optimize_context,
)
from src.llm.extractor import (
    estimate_input_cost,
    estimate_tokens,
    extract_company_intelligence,
)


def normalize_domain(domain: str) -> str:
    """
    Convert a domain into a normalized HTTPS URL.
    """
    domain = domain.strip()

    if not domain.startswith(("http://", "https://")):
        domain = f"https://{domain}"

    return domain.rstrip("/")


def enrich_company(website: str):
    """
    Run the complete enrichment pipeline for one company.
    """

    print("\n" + "=" * 60)
    print(f"Starting enrichment for: {website}")
    print("=" * 60)

    # Step 1: Crawl website
    crawl_result = crawl_website(website)

    print(f"Pages discovered: {len(crawl_result['pages'])}")

    # Step 2: Clean and optimize content
    combined_content = optimize_context(
        crawl_result["pages"],
        max_chars_per_page=2500,
        max_total_chars=9000,
    )

    # Extract emails deterministically from crawled content
    extracted_emails = {}

    for page in crawl_result["pages"]:
       if page.get("error"):
          continue

       page_emails = extract_emails(
          page.get("content", "")
       )

       for email in page_emails:
          if email not in extracted_emails:
                extracted_emails[email] = page["url"]

    print(
       f"Deterministic emails found: "
       f"{extracted_emails}"
    )

    print(
        f"Total optimized context characters: "
        f"{len(combined_content)}"
    )

    estimated_tokens = estimate_tokens(
       combined_content
    )

    estimated_cost = estimate_input_cost(
       estimated_tokens
    )

    print(
       f"Estimated input tokens: "
       f"{estimated_tokens}"
    )

    print(
       f"Estimated input cost: "
       f"${estimated_cost:.6f}"
    )

    if not combined_content:
        print("No usable content found. Skipping company.")
        return None

    # Step 3: Extract structured intelligence
    result = extract_company_intelligence(
        combined_content,
        extracted_emails=extracted_emails,
    )

    # Keep only contact emails that were deterministically
    # found in the crawled website content.
    result.contact_points = [
        contact
        for contact in result.contact_points
        if contact.email.lower() in extracted_emails
    ]

    result.confidence_score = calculate_confidence(
        result,
        crawl_result,
    )

    # Step 4: Display result
    print("\nCOMPANY INTELLIGENCE")
    print("-" * 60)
    print(result.model_dump_json(indent=2))

    return {
    "result": result,
    "processing": {
        "input_characters": len(combined_content),
        "estimated_input_tokens": estimated_tokens,
        "estimated_input_cost_usd": estimated_cost,
    },
}

def save_csv(results, output_file):
    """
    Save company intelligence results to CSV.
    """

    rows = []

    for item in results:
        intelligence = item["intelligence"]

        rows.append(
            {
                "domain": item["domain"],
                "company_overview": intelligence["company_overview"],
                "target_audience": ", ".join(
                    intelligence["target_audience"]
                ),
                "contact_emails": ", ".join(
                    contact["email"]
                    for contact in intelligence["contact_points"]
                ),
                "leadership_team": "; ".join(
                    f"{member['name']} - {member['role']}"
                    for member in intelligence["leadership_team"]
                ),
                "confidence_score": intelligence["confidence_score"],
                "estimated_input_tokens": item["processing"]["estimated_input_tokens"],
                "input_characters": item["processing"]["input_characters"],
                "estimated_input_cost_usd": item["processing"]["estimated_input_cost_usd"],
            }
        )

    fieldnames = [
        "domain",
        "company_overview",
        "target_audience",
        "contact_emails",
        "leadership_team",
        "confidence_score",
        "estimated_input_tokens",
        "input_characters",
        "estimated_input_cost_usd",
    ]

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)


def calculate_confidence(
    result,
    crawl_result,
) -> float:
    """
    Calculate an explainable confidence score
    from the available evidence.
    """

    score = 0.0

    # Company overview
    if result.company_overview.strip():
        score += 0.25

    # Target audience
    if result.target_audience:
        score += 0.20

    # Contact information
    if result.contact_points:
        score += 0.20

    # Leadership/team information
    if result.leadership_team:
        score += 0.15

    # Source URLs
    sourced_contacts = sum(
        1
        for contact in result.contact_points
        if contact.source_url
    )

    sourced_team = sum(
        1
        for member in result.leadership_team
        if member.source_url
    )

    if sourced_contacts > 0:
        score += 0.10

    if sourced_team > 0:
        score += 0.10

    # Reduce confidence when crawl errors occurred
    crawl_errors = sum(
        1
        for page in crawl_result["pages"]
        if page.get("error")
    )

    if crawl_errors > 0:
        score -= min(
            0.20,
            crawl_errors * 0.05
        )

    return round(
        max(0.0, min(1.0, score)),
        2
    )

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Lead Enrichment Agent"
    )

    parser.add_argument(
        "--domains",
        nargs="+",
        required=True,
        help="Company domains to enrich",
    )

    args = parser.parse_args()

    results = []

    for domain in args.domains:
        website = normalize_domain(domain)

        try:
            enrichment = enrich_company(website)

            if enrichment is not None:
               results.append(
                    {
                       "domain": website,
                       "intelligence": enrichment["result"].model_dump(),
                       "processing": enrichment["processing"],
                    }
                )
                    

        except Exception as e:
            print(
                f"\nERROR processing {website}: {e}"
            )
            print("Continuing with the next company...")

    # Save combined results to JSON
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "enrichment_results.json"

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"\nSaved results to: {output_file}"
    )

    csv_file = output_dir / "enrichment_results.csv"

    save_csv(
        results,
        csv_file
    )

    print(
       f"Saved CSV results to: {csv_file}"
    )


if __name__ == "__main__":
    main()