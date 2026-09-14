from urllib.parse import urlparse

from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


RELEVANT_KEYWORDS = [
    "about",
    "team",
    "company",
    "contact",
    "pricing",
]


def discover_relevant_links(page, base_url: str) -> list[str]:
    """
    Discover relevant internal pages from a webpage.
    """

    base_domain = urlparse(base_url).netloc

    links = page.locator("a").evaluate_all(
        """
        elements => elements.map(a => ({
            text: a.innerText,
            href: a.href
        }))
        """
    )

    relevant_links = []

    for link in links:
        href = link.get("href", "")
        text = link.get("text", "").lower()

        if not href:
            continue

        parsed_url = urlparse(href)

        

        # Only keep links from the same domain or its subdomains
        if not (
           parsed_url.netloc == base_domain
           or parsed_url.netloc.endswith("." + base_domain)
       ):
           continue

        combined_text = f"{text} {href.lower()}"

        if any(keyword in combined_text for keyword in RELEVANT_KEYWORDS):
            clean_url = href.split("#")[0]

            if clean_url not in relevant_links:
                relevant_links.append(clean_url)

    return relevant_links


def crawl_page(page, url: str) -> dict:
    """
    Crawl one webpage and extract its visible text.
    """

    try:
        response = page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        if response is None:
            return {
                "url": url,
                "title": "",
                "content": "",
                "error": "No response received",
            }

        if response.status >= 400:
            return {
                "url": url,
                "title": "",
                "content": "",
                "error": f"HTTP {response.status}",
            }

        page.wait_for_timeout(2000)

        title = page.title()

        # Remove common webpage boilerplate elements
        page.evaluate(
            """
            () => {
                const selectors = [
                    "script",
                    "style",
                    "noscript",
                    "svg",
                    "nav",
                    "header",
                    "footer"
                ];

                selectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(element => {
                        element.remove();
                    });
                });
            }
            """
        )

        content = page.locator("body").inner_text()

        lower_content = content.lower()

        bot_block_indicators = [
            "access denied",
            "checking your browser",
            "verify you are human",
            "captcha",
            "cf-chl",
            "unusual traffic",
        ]

        if any(
            indicator in lower_content
            for indicator in bot_block_indicators
        ):
            return {
                "url": url,
                "title": title,
                "content": "",
                "error": "Possible bot protection detected",
            }
        
        return {
            "url": url,
            "title": title,
            "content": content,
            "error": None,
        }


    except PlaywrightTimeoutError:
        return {
            "url": url,
            "title": "",
            "content": "",
            "error": "Page load timeout",
        }

    except Exception as e:
        return {
            "url": url,
            "title": "",
            "content": "",
            "error": str(e),
        }


def crawl_website(base_url: str) -> dict:
    """
    Crawl the homepage and discover relevant internal pages.
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 1. Load homepage for link discovery
            page.goto(
                base_url,
                wait_until="domcontentloaded",
                timeout=30000
        )

            page.wait_for_timeout(2000)

            # 2. Discover relevant internal links BEFORE cleaning the page
            relevant_links = discover_relevant_links(
                page,
                base_url
            )

            print("Discovered relevant links:")
            for link in relevant_links:
                print(" -", link)

            # 3. Crawl and clean homepage
            homepage = crawl_page(page, base_url)

            # 4. Crawl discovered pages
            pages = [homepage]

            for url in relevant_links:
                result = crawl_page(page, url)
                pages.append(result)

            return {
                "base_url": base_url,
                "pages": pages,
            }

        finally:
            browser.close()