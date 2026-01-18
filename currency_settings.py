"""Currency settings and conversion utilities."""

import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen


DEFAULT_API_URL = "https://api.unirateapi.com/api/convert"
DEFAULT_RATES = {
    "AZN": 1.0,
    "USD": 0.0,
    "EUR": 0.0,
    "TRY": 0.0,
}


class CurrencySettingsManager:
    def __init__(self, db=None):
        self.db = db
        self.settings_file = os.path.join(os.path.dirname(__file__), "app_settings.json")

    def _default_data(self):
        return {
            "api_url": DEFAULT_API_URL,
            "api_key": "",
            "rates": DEFAULT_RATES.copy(),
            "last_fetch": None,
        }

    def load_local(self):
        if not os.path.exists(self.settings_file):
            return self._default_data()
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        return self._merge_defaults(data)

    def save_local(self, data):
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_db(self):
        if not self.db:
            return None
        try:
            value = self.db.get_app_setting("currency_settings")
            return self._merge_defaults(value or {})
        except Exception:
            return None

    def save_db(self, data):
        if not self.db:
            return
        self.db.set_app_setting("currency_settings", data)

    def load(self):
        data = self.load_db()
        if data is None:
            data = self.load_local()
        data = self._merge_defaults(data)
        # Keep local copy in sync
        try:
            self.save_local(data)
        except Exception:
            pass
        return data

    def save(self, data):
        data = self._merge_defaults(data)
        self.save_local(data)
        self.save_db(data)

    def get_rates(self):
        data = self.load()
        return data.get("rates", DEFAULT_RATES.copy())

    def convert_to_azn(self, amount, currency):
        rates = self.get_rates()
        rate = rates.get(currency, 1.0)
        if currency == "AZN":
            rate = 1.0
        if rate in (None, 0):
            return 0.0
        return amount * rate

    def last_fetch_time(self):
        data = self.load()
        last_fetch = data.get("last_fetch")
        if not last_fetch:
            return None
        try:
            return datetime.fromisoformat(last_fetch)
        except Exception:
            return None

    def is_update_due(self, min_days=5):
        last_fetch = self.last_fetch_time()
        if not last_fetch:
            return True
        return datetime.now(timezone.utc) - last_fetch >= timedelta(days=min_days)

    def update_from_api(self, force=False, min_days=5):
        data = self.load()
        if not force and not self.is_update_due(min_days=min_days):
            raise Exception("Update is not due yet.")

        api_url = data.get("api_url", DEFAULT_API_URL)
        api_key = data.get("api_key", "")
        if not api_url:
            raise Exception("API URL is empty.")
        if not api_key:
            raise Exception("API key is empty.")

        new_rates = DEFAULT_RATES.copy()
        for code in ("USD", "EUR", "TRY"):
            params = {
                "api_key": api_key,
                "from": code,
                "to": "AZN",
                "amount": 1,
            }
            joiner = "&" if "?" in api_url else "?"
            url = f"{api_url}{joiner}{urlencode(params)}"
            with urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))

            if "result" not in payload:
                raise Exception(f"Unexpected API response: {payload}")

            new_rates[code] = float(payload["result"])

        new_rates["AZN"] = 1.0

        data["rates"] = new_rates
        data["last_fetch"] = datetime.now(timezone.utc).isoformat()
        self.save(data)
        return data

    def _merge_defaults(self, data):
        merged = self._default_data()
        if isinstance(data, dict):
            merged.update(data)
        if "rates" not in merged or not isinstance(merged["rates"], dict):
            merged["rates"] = DEFAULT_RATES.copy()
        else:
            for code, value in DEFAULT_RATES.items():
                merged["rates"].setdefault(code, value)
        return merged
