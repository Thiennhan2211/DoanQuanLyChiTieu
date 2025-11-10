import requests

def get_exchange_rate(from_currency, to_currency="VND"):
    if from_currency == to_currency:
        return 1.0
    try:
        url = f"https://api.exchangerate.host/convert?from={from_currency}&to={to_currency}"
        response = requests.get(url)
        data = response.json()
        return data.get("result", 1.0)
    except Exception:
        return 1.0
