"""HTTP-only dashboard client. Models and SQLite stay behind the API."""

import os

import httpx


class APIError(RuntimeError):
    pass


class SupportAPI:
    def __init__(self, base_url=None):
        self.base_url = (base_url or os.environ.get("SUPPORT_API_URL", "http://127.0.0.1:8000")).rstrip("/")

    def request(self, method, path, **kwargs):
        try:
            headers = {"X-API-Key": os.environ["SUPPORT_API_KEY"]} if os.environ.get("SUPPORT_API_KEY") else {}
            with httpx.Client(base_url=self.base_url, timeout=120, trust_env=False, headers=headers) as client:
                response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise APIError("That ticket could not be found. Refresh the list and try again.") from None
            if error.response.status_code == 422:
                raise APIError("The request was not accepted. Check the text and correction fields, then try again.") from None
            raise APIError("The API could not complete this request. Please try again.") from None
        except (httpx.RequestError, ValueError):
            raise APIError("Cannot reach the support API. Start the backend and refresh this page.") from None

    def health(self):
        return self.request("GET", "/health")

    def analytics(self):
        return self.request("GET", "/analytics")

    def taxonomy(self):
        return self.request("GET", "/taxonomy")

    def create_ticket(self, text):
        return self.request("POST", "/tickets", json={"text": text})

    def tickets(self, limit=20, offset=0, needs_review=None):
        params = {"limit": limit, "offset": offset}
        if needs_review is not None:
            params["needs_review"] = needs_review
        return self.request("GET", "/tickets", params=params)

    def ticket(self, ticket_id):
        return self.request("GET", f"/tickets/{ticket_id}")

    def feedback(self, ticket_id):
        return self.request("GET", f"/tickets/{ticket_id}/feedback")

    def add_feedback(self, ticket_id, values):
        return self.request("POST", f"/tickets/{ticket_id}/feedback", json=values)
