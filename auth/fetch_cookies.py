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
        with SB(uc=True, headless2=True) as driver:
            driver.uc_open_with_reconnect("https://www.upwork.com/nx/search/jobs/", 5)
            
            # Aggressive polling: wait up to 30 seconds for the token to appear
            for _ in range(30):
                raw_cookies = driver.get_cookies()
                cookie_dict = {c["name"]: c["value"] for c in raw_cookies}
                
                auth_token = (
                    cookie_dict.get("UniversalSearchNuxt_vt")
                    or cookie_dict.get("visitor_gql_token")
                    or cookie_dict.get("visitor_topnav_gql_token")
                )
                
                if auth_token:
                    cookies.update(cookie_dict)
                    break
                driver.sleep(1)

    except KeyboardInterrupt:
        print(json.dumps({"error": "Process was interrupted by user (Ctrl+C)"}), flush=True)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}), flush=True)
        sys.exit(1)

    print(json.dumps({"cookies": cookies, "auth_token": auth_token}), flush=True)


if __name__ == "__main__":
    main()
