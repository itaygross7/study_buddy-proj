from bs4 import BeautifulSoup


def convert_html_to_text(html_content: str) -> str:
    """
    Converts HTML content to plain text, preserving line breaks for block elements.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator='\\n', strip=True)
