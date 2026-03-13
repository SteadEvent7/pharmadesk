from __future__ import annotations

from app.config import CONFIG


AFRICAN_CURRENCIES: dict[str, dict[str, str]] = {
    "XOF": {"label": "Franc CFA BCEAO (XOF)", "symbol": "FCFA"},
    "XAF": {"label": "Franc CFA BEAC (XAF)", "symbol": "FCFA"},
    "GNF": {"label": "Franc guineen (GNF)", "symbol": "FG"},
    "CDF": {"label": "Franc congolais (CDF)", "symbol": "FC"},
    "BIF": {"label": "Franc burundais (BIF)", "symbol": "FBu"},
    "RWF": {"label": "Franc rwandais (RWF)", "symbol": "FRw"},
    "NGN": {"label": "Naira nigerian (NGN)", "symbol": "NGN"},
    "GHS": {"label": "Cedi ghaneen (GHS)", "symbol": "GHS"},
    "KES": {"label": "Shilling kenyan (KES)", "symbol": "KES"},
    "UGX": {"label": "Shilling ougandais (UGX)", "symbol": "UGX"},
    "TZS": {"label": "Shilling tanzanien (TZS)", "symbol": "TZS"},
    "ZMW": {"label": "Kwacha zambien (ZMW)", "symbol": "ZMW"},
    "BWP": {"label": "Pula botswanais (BWP)", "symbol": "BWP"},
    "ZAR": {"label": "Rand sud-africain (ZAR)", "symbol": "ZAR"},
    "MAD": {"label": "Dirham marocain (MAD)", "symbol": "MAD"},
    "TND": {"label": "Dinar tunisien (TND)", "symbol": "TND"},
    "DZD": {"label": "Dinar algerien (DZD)", "symbol": "DZD"},
    "EGP": {"label": "Livre egyptienne (EGP)", "symbol": "EGP"},
}


def get_currency_symbol() -> str:
    currency = AFRICAN_CURRENCIES.get(CONFIG.currency_code)
    if currency:
        return currency["symbol"]
    return CONFIG.currency_code


def format_currency(amount: float) -> str:
    return f"{float(amount):.2f} {get_currency_symbol()}"