import pandas as pd
import requests
import io

def fetch_sp500():
    print("Fetching S&P 500 tickers from Wikipedia...")
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        tables = pd.read_html(response.text)
        df = tables[0]
        tickers = df['Symbol'].tolist()
        return [t.replace('.', '-') for t in tickers]
    except Exception as e:
        print(f"Error fetching S&P 500: {e}")
        return []

def fetch_nasdaq100():
    print("Fetching Nasdaq 100 tickers from Wikipedia...")
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        tables = pd.read_html(response.text)
        for df in tables:
            if 'Ticker' in df.columns:
                return df['Ticker'].tolist()
            if 'Symbol' in df.columns and len(df) > 90 and len(df) < 110:
                return df['Symbol'].tolist()
        return []
    except Exception as e:
        print(f"Error fetching Nasdaq 100: {e}")
        return []

def fetch_dow30():
    print("Fetching Dow Jones Industrial Average tickers from Wikipedia...")
    url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        tables = pd.read_html(response.text)
        for df in tables:
            # The Dow table usually has 'Company', 'Exchange', 'Symbol'
            if 'Symbol' in df.columns and len(df) >= 30 and len(df) <= 35:
                return df['Symbol'].tolist()
        return []
    except Exception as e:
        print(f"Error fetching Dow 30: {e}")
        return []

def fetch_russell2000():
    print("Fetching Russell 2000 tickers from iShares...")
    # Use the iShares IWM holdings CSV URL
    url = "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        # iShares CSV has several header lines before the actual data
        csv_text = response.text
        lines = csv_text.splitlines()
        
        # Find the line that starts with "Ticker"
        start_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("Ticker,"):
                start_idx = i
                break
        
        df = pd.read_csv(io.StringIO("\n".join(lines[start_idx:])))
        tickers = df['Ticker'].dropna().tolist()
        # Filter out non-equity symbols (e.g., "XTSLA", or cash positions)
        # iShares tickers are already clean but let's be safe
        clean_tickers = [str(t).replace('.', '-') for t in tickers if isinstance(t, str) and len(t) <= 5]
        return clean_tickers
    except Exception as e:
        print(f"Error fetching Russell 2000: {e}")
        return []

def main():
    sp500 = fetch_sp500()
    nasdaq100 = fetch_nasdaq100()
    dow30 = fetch_dow30()
    russell2000 = fetch_russell2000()

    all_tickers = sorted(list(set(sp500 + nasdaq100 + dow30 + russell2000)))
    
    print(f"\nFetched:")
    print(f"- S&P 500: {len(sp500)}")
    print(f"- Nasdaq 100: {len(nasdaq100)}")
    print(f"- Dow 30: {len(dow30)}")
    print(f"- Russell 2000: {len(russell2000)}")
    print(f"- Total Unique: {len(all_tickers)}")

    with open("stock-bot/data/watchlist_expanded.csv", "w") as f:
        f.write("\n".join(all_tickers))
    
    print(f"\nSaved all unique tickers to stock-bot/data/watchlist_expanded.csv")

if __name__ == "__main__":
    main()
