"""
Standalone script: visits Upwork as an anonymous visitor and prints
fresh cookies + auth token as JSON to stdout.

Called as a subprocess by AuthManager so Selenium's internal asyncio
event loop never conflicts with Discord's event loop.
"""
import json
import sys

from seleniumbase import SB


def main():
    cookies = {}
    auth_token = None

    try:
        with SB(uc=True, headless=True) as driver:
            driver.get("https://www.upwork.com/nx/search/jobs/")
            driver.sleep(5)  # Wait for Cloudflare to clear

            for cookie in driver.get_cookies():
                cookies[cookie["name"]] = cookie["value"]

            auth_token = (
                cookies.get("UniversalSearchNuxt_vt")
                or cookies.get("visitor_gql_token")
                or cookies.get("visitor_topnav_gql_token")
            )

    except Exception as e:
        print(json.dumps({"error": str(e)}), flush=True)
        sys.exit(1)

    print(json.dumps({"cookies": cookies, "auth_token": auth_token}), flush=True)


if __name__ == "__main__":
    main()
