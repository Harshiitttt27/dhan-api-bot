import json
from dhanhq import dhanhq
from config import Config

# Initialize Dhan Client
config = Config()
client = dhanhq(config.DHAN_CLIENT_ID, config.DHAN_ACCESS_TOKEN)

# Your watchlist (symbols like NSE)
WATCHLIST = ["TCS", "INFY", "ITC", "RELIANCE", "HDFCBANK"]

def fetch_security_ids():
    try:
        # Fetch NSE Equity security master
        print("Fetching NSE Equity Security Master from Dhan...")
        data = client.security_master(exchange_segment="NSE_EQ")

        if not data or 'data' not in data:
            print("Failed to fetch security master")
            return

        securities = data['data']
        print(f"Total securities fetched: {len(securities)}")

        symbol_to_id = {}
        for sec in securities:
            trading_symbol = sec.get('trading_symbol')
            if trading_symbol in WATCHLIST:
                symbol_to_id[trading_symbol] = sec.get('security_id')

        print("\n✅ Security IDs found for watchlist:")
        for sym, sec_id in symbol_to_id.items():
            print(f"{sym} -> {sec_id}")

        # Save mapping to JSON for reuse
        with open("security_ids.json", "w") as f:
            json.dump(symbol_to_id, f, indent=4)

        print("\n💾 Security IDs saved to security_ids.json")

    except Exception as e:
        print("Error fetching security IDs:", e)

if __name__ == "__main__":
    fetch_security_ids()
