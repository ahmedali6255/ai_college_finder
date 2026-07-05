"""
api.py
------
Thin wrapper around the free Hipolabs Universities API
(http://universities.hipolabs.com). No API key is required.

Docs / example: http://universities.hipolabs.com/search?country=Pakistan
"""

from typing import List, Optional

import requests

from utils import University

BASE_URL = "http://universities.hipolabs.com/search"
REQUEST_TIMEOUT = 10  # seconds


class UniversityAPIError(Exception):
    """Raised when the Universities API cannot be reached or parsed."""


class UniversityAPI:
    """Small client for searching universities by country and/or name."""

    @staticmethod
    def search(country: Optional[str] = None, name: Optional[str] = None) -> List[University]:
        """Search universities. At least one of country/name should be set.

        Returns a list of University objects. Raises UniversityAPIError on
        network or parsing failure so the GUI layer can show a friendly
        message instead of crashing.
        """
        params = {}
        if country and country.strip():
            params["country"] = country.strip()
        if name and name.strip():
            params["name"] = name.strip()

        if not params:
            raise UniversityAPIError("Provide a country or a university name to search.")

        try:
            response = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            raw_results = response.json()
        except requests.exceptions.Timeout:
            raise UniversityAPIError("The request timed out. Please check your internet connection.")
        except requests.exceptions.ConnectionError:
            raise UniversityAPIError("Could not connect to the Universities API. Check your internet connection.")
        except requests.exceptions.HTTPError as exc:
            raise UniversityAPIError(f"Universities API returned an error: {exc}")
        except ValueError:
            raise UniversityAPIError("Received an unexpected response from the Universities API.")

        universities = []
        for item in raw_results:
            websites = item.get("web_pages") or []
            state_prov = item.get("state-province") or ""
            universities.append(
                University(
                    name=item.get("name", "Unknown University"),
                    country=item.get("country", "Unknown"),
                    website=websites[0] if websites else "",
                    state_province=state_prov or "",
                )
            )

        # Cap results so the UI stays responsive on very broad searches
        # (e.g. searching a large country with no name filter).
        return universities[:100]
