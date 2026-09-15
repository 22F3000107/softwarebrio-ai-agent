# Autonomous Lead Enrichment Agent

A Python-based autonomous lead enrichment agent that crawls public company websites, discovers relevant internal pages, cleans webpage content, and uses an LLM to extract structured company intelligence.

## Features

- Automated browser-based website crawling with Playwright
- Homepage and relevant internal-page discovery
- Handles JavaScript-rendered webpages
- Removes scripts, styles, navigation, headers, footers, and other boilerplate
- Context optimization before LLM processing
- Deterministic public email extraction
- LLM-based company intelligence extraction
- Pydantic schema validation
- Evidence-backed contact email filtering
- Leadership/team extraction with source URLs when available
- Confidence scoring
- Input token estimation
- Configurable API cost estimation
- Graceful handling of failed websites
- Batch processing continues when one company fails
- JSON and CSV output

## Architecture

```
Input Domains
     |
     v
+-------------------+
| Playwright Crawler|
+-------------------+
     |
     v
Relevant Page Discovery
     |
     v
+----------------------+
| Content Cleaning     |
| Context Optimization |
+----------------------+
     |
     +----------------------+
     |                      |
     v                      v
Email Extraction       Optimized Context
     |                      |
     +----------+-----------+
                |
                v
        +---------------+
        | Groq LLM      |
        | GPT OSS 20B   |
        +---------------+
                |
                v
        Pydantic Validation
                |
                v
        Confidence Scoring
                |
        +-------+-------+
        |               |
        v               v
   JSON Output      CSV Output
````

## Project Structure

```text
softwarebrio-ai-agent/
├── main.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── samples/
│   ├── sample_enrichment_results.json
│   └── sample_enrichment_results.csv
└── src/
    ├── browser/
    │   └── crawler.py
    ├── extraction/
    │   └── content_cleaner.py
    ├── llm/
    │   └── extractor.py
    ├── models/
    │   └── schemas.py
    └── utils/
        └── logger.py
```

## Requirements

* Python 3.12+
* Playwright
* Pydantic
* python-dotenv
* Groq
* Tenacity
* Groq API key

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/22F3000107/softwarebrio-ai-agent.git
cd softwarebrio-ai-agent
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

macOS/Linux:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Install the Playwright browser

```bash
playwright install chromium
```

## Environment Variables

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_groq_api_key
GROQ_INPUT_COST_PER_MILLION_TOKENS=0.075
```

A template is also provided in `.env.example`.

The API key should never be committed to GitHub.

## Usage

Run the agent with one or more company domains:

```bash
python3 main.py --domains postman.com
```

Multiple domains can be processed in a single run:

```bash
python3 main.py --domains postman.com supabase.com vapi.ai
```

The pipeline processes each company independently. If one domain fails, the agent reports the error and continues with the remaining domains.

## Output

Runtime results are generated locally in:

```text
outputs/enrichment_results.json
outputs/enrichment_results.csv
```

The `outputs/` directory is ignored by Git.

Sample results for the three required test domains are included in:

```text
samples/sample_enrichment_results.json
samples/sample_enrichment_results.csv
```

Each company result contains:

* Company overview
* Target audience / ICP
* Public contact emails
* Leadership/team information
* Confidence score
* Estimated input tokens
* Input character count
* Estimated input cost

### Example

```json
{
  "domain": "https://postman.com",
  "intelligence": {
    "company_overview": "Postman is an API platform for building and using APIs. It simplifies each step of the API lifecycle and streamlines collaboration to help developers create better APIs faster.",
    "target_audience": [
      "individual developers",
      "team developers",
      "enterprise organizations"
    ],
    "contact_points": [
      {
        "email": "info@postman.com",
        "source_url": "https://www.postman.com/company/about-postman/"
      }
    ],
    "leadership_team": [
      {
        "name": "Abhinav Asthana",
        "role": "CEO and co-founder",
        "linkedin_url": null,
        "source_url": "https://www.postman.com/company/about-postman/"
      }
    ],
    "confidence_score": 1.0
  },
  "processing": {
    "input_characters": 9000,
    "estimated_input_tokens": 2250,
    "estimated_input_cost_usd": 0.000169
  }
}
```

## Error Handling

The agent is designed to continue processing when individual websites fail.

Examples of handled failures include:

* DNS resolution failures
* Page-load timeouts
* HTTP errors
* Missing responses
* Potential bot-protection pages
* Missing webpage content
* Invalid LLM-generated team members

A failed company does not terminate the entire batch.

## Context Optimization

Raw HTML is not directly sent to the LLM.

The crawler first removes common webpage boilerplate such as:

* JavaScript
* CSS
* SVG elements
* Navigation
* Headers
* Footers

The remaining visible text is cleaned and limited using configurable per-page and total context limits.

This reduces unnecessary LLM input and helps control latency and API cost.

## Structured Extraction

LLM output is parsed as JSON and validated using Pydantic models.

The extraction schema contains:

```text
Company Overview
Target Audience
Contact Points
Leadership / Team
Confidence Score
```

Invalid leadership records are rejected by schema validation rather than being allowed into the final result.

Public emails are also extracted deterministically from crawled webpage content and used to filter LLM-generated contact points.

## Cost Tracking

The agent estimates input tokens using the cleaned context size:

```text
estimated_tokens ≈ characters / 4
```

Input cost is calculated using the configured rate:

```text
cost = estimated_tokens / 1,000,000 × input_price
```

The token count is an approximation and is intended for monitoring rather than exact billing reconciliation.

## Tested Domains

The pipeline has been tested with:

```text
postman.com
supabase.com
vapi.ai
```

It has also been tested with an invalid domain to verify that a failed company does not stop subsequent processing.

## Future Improvements

Potential extensions include:

* External search for LinkedIn profiles
* Browser search integration
* More advanced agentic workflows
* Exact tokenizer-based cost tracking
* More sophisticated page prioritization
* Additional anti-bot and retry strategies