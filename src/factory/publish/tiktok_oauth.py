"""TikTok OAuth helper — get initial tokens for a brand.

Usage:
    python -m factory.publish.tiktok_oauth --brand shitpostfactoryhq

This opens a browser for TikTok OAuth authorization, then exchanges
the authorization code for access + refresh tokens.

Steps:
1. Run this script
2. Browser opens TikTok authorization page
3. Log in with the TikTok account for the brand
4. Authorize the app
5. Copy the authorization code from the callback URL
6. Paste it into the terminal
7. Tokens are saved to tokens/<brand>_tiktok.json
"""
from __future__ import annotations

import argparse
import sys
import webbrowser
from urllib.parse import urlencode

from factory.publish.tiktok import exchange_code, _get_credentials


def main():
    parser = argparse.ArgumentParser(description="TikTok OAuth helper")
    parser.add_argument("--brand", required=True, help="Brand name")
    parser.add_argument("--redirect-uri", default="https://localhost", help="Redirect URI registered in TikTok app")
    parser.add_argument("--scope", default="video.publish,user.info.basic", help="Comma-separated scopes")
    args = parser.parse_args()

    client_key, _ = _get_credentials()

    # Build authorization URL
    auth_params = {
        "client_key": client_key,
        "scope": args.scope,
        "response_type": "code",
        "redirect_uri": args.redirect_uri,
        "state": args.brand,
    }
    auth_url = f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(auth_params)}"

    print(f"\n{'='*60}")
    print(f"TikTok OAuth — Brand: {args.brand}")
    print(f"{'='*60}\n")
    print(f"1. Opening browser to:\n   {auth_url}\n")
    print(f"2. Log in with the TikTok account for '{args.brand}'")
    print(f"3. Authorize the app")
    print(f"4. Copy the 'code' parameter from the callback URL")
    print(f"   (It will look like: https://localhost?code=ACTUAL_CODE&state=...)")
    print(f"5. Paste it below\n")

    webbrowser.open(auth_url)

    code = input("Authorization code: ").strip()
    if not code:
        print("No code provided. Exiting.")
        sys.exit(1)

    print(f"\nExchanging code for tokens...")
    try:
        tokens = exchange_code(code, args.redirect_uri, args.brand)
        print(f"\n{'='*60}")
        print(f"SUCCESS! Tokens saved for brand: {args.brand}")
        print(f"{'='*60}")
        print(f"  Access token: {tokens.access_token[:20]}...")
        print(f"  Refresh token: {tokens.refresh_token[:20]}...")
        print(f"  Open ID: {tokens.open_id}")
        print(f"  Scopes: {tokens.scope}")
        print(f"\nTokens are valid for:")
        print(f"  Access token: 24 hours (auto-refreshed by pipeline)")
        print(f"  Refresh token: 365 days")
        print(f"\nToken file: tokens/{args.brand}_tiktok.json")
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
