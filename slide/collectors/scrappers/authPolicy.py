import base64
from typing import Tuple

from bs4 import BeautifulSoup, Tag
import requests

from slide.collectors import AuthPolicy

class ANPAuthPolicy(AuthPolicy):
    """
    This class aims to scrap the auth token for each basin available at: "https://reate.cprm.gov.br/anp/TERRESTRE"
    """

    def __init__(self) -> None:
        super().__init__()

    def fetch(self, url: str) -> list[Tuple[str, str]]:
        """
        Fetch basin links from the given URL.

        Args:
            url (str): The URL to fetch basin links from.

        Returns:
            list[Tuple[str, str]]: A list of tuples containing basin names and their corresponding links.
        """
        response = requests.get(url)

        if response.status_code != 200:
            raise requests.exceptions.RequestException(
                f"Failed to fetch basin links from {url} with status code {response.status_code}"
            )

        basin_links = []
        soup = BeautifulSoup(response.content, "html.parser")
        # Find all <h4> tags that start with 'Bacia'
        titles = soup.find_all("h4")
        for title in titles:
            basin_name: str = title.get_text(strip=True).lower()
            if not basin_name.startswith("bacia"):
                continue

            # Find the nearest <a> tag with an href attribute
            link_tag = title.find_next("a", href=True)
            if not link_tag or not isinstance(link_tag, Tag):
                continue

            link = link_tag.get("href")
            # Store the basin name and link in the dictionary
            basin_links.append((basin_name, link))

        return basin_links

    def get(self) -> list[Tuple[str, str]]:
        """
        Scrape the authentication headers for each basin link.

        Returns:
            list[Tuple[str, str]]: A list of tuples containing basin names and their corresponding authentication headers.
        """
        # Implement the scraping logic here
        url = "https://reate.cprm.gov.br" + "/anp/TERRESTRE"
        basin_links = self.fetch(url)

        auths = []
        for name, link in basin_links:
            user = link.split("/")[-1]
            passcode = "null"
            basic_auth = f"{user}:{passcode}"
            encoded_bytes = base64.b64encode(basic_auth.encode("utf-8"))
            auths.append((name, f"Basic {encoded_bytes.decode('utf-8')}"))

        return auths
