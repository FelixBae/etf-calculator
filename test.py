import streamlit as st
import pandas as pd
import numpy as np

try:
    import yfinance as yf
    USE_YF = True
except ImportError:
    USE_YF = False


MSCI_TICKER = "IWDA.AS"


# ==============================
# LOAD DATA
# ==============================
@st.cache_data
def load_data():
    df = pd.read_csv('./data/data.csv')

    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    for col in ['shares', 'price', 'fee', 'amount']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['type'] = df['type'].astype(str).str.lower().str.strip()
    df['symbol'] = df['symbol'].astype(str).str.strip()
    df['name'] = df['name'].astype(str).str.strip()

    df['asset'] = df['name'] + " (" + df['symbol'] + ")"

    return df.sort_values('date')


# ==============================
# SAFE SYMBOL EXTRACTION
# ==============================
def get_symbols(df):
    return (
        df['symbol']
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )


# ==============================
# FIFO ENGINE
# ==============================
def calculate_fifo(df):
    positions = {}
    closed = []

    for _, row in df.iterrows():
        asset = row['asset']
        qty = row['shares']
        price = row['price']
        fee = row['fee'] if not np.isnan(row['fee']) else 0

        if asset not in positions:
            positions[asset] = []

        if row['type'] == 'buy':
            positions[asset].append({
                'shares': qty,
                'price': price,
                'date': row['date'],
                'fee': fee
            })

        elif row['type'] == 'sell':
            remaining = qty

            while remaining > 0 and positions[asset]:
                lot = positions[asset][0]

                used = min(remaining, lot['shares'])

                profit = used * (price - lot['price'])

                closed.append({
                    'asset': asset,
                    'buy_date': lot['date'],
                    'sell_date': row['date'],
                    'shares': used,
                    'buy_price': lot['price'],
                    'sell_price': price,
                    'profit': profit
                })

                lot['shares'] -= used
                remaining -= used

                if lot['shares'] == 0:
                    positions[asset].pop(0)

    return positions, pd.DataFrame(closed)


# ==============================
# PRICE FETCH (ROBUST)
# ==============================
def get_prices(symbols):
    if not USE_YF or not symbols:
        return {}

    try:
        data = yf.download(symbols, period="1d", auto_adjust=True, progress=False)

        prices = {}

        # Single ticker case
        if isinstance(symbols, list) and len(symbols) == 1:
            prices[symbols[0]] = data['Close'].iloc[-1]
        else:
            for sym in symbols:
                try:
                    prices[sym] = data[sym]['Close'].iloc[-1]
                except Exception:
                    prices[sym] = np.nan

        return prices

    except Exception as e:
        st.warning(f"Preisabfrage fehlgeschlagen: {e}")
        return {}


# ==============================
# MSCI DATA
# ==============================
@st.cache_data
def get_msci(start):
    if not USE_YF:
        return None
    try:
        return yf.download(MSCI_TICKER, start=start, auto_adjust=True, progress=False)
    except:
        return None


# ==============================
# MAIN APP
# ==============================
def app():
    st.title("📈 Portfolio Dashboard (stabil)")

    df = load_data()

    st.subheader("📋 Transaktionen")
    st.dataframe(df)

    # FIFO
    open_pos, closed_trades = calculate_fifo(df)

    st.subheader("💰 Realisierte Gewinne (FIFO)")
    st.dataframe(closed_trades)

    # Preise holen
    symbols = get_symbols(df)
    prices = get_prices(symbols)

    # ==============================
    # OFFENE POSITIONEN
    # ==============================
    rows = []

    for asset, lots in open_pos.items():
        sym = asset.split("(")[-1].replace(")", "").strip()

        for lot in lots:
            current_price = prices.get(sym, np.nan)

            value_now = lot['shares'] * current_price
            cost = lot['shares'] * lot['price'] + lot.get('fee', 0)
            profit = value_now - cost

            rows.append({
                'asset': asset,
                'date': lot['date'],
                'shares': lot['shares'],
                'buy_price': lot['price'],
                'current_price': current_price,
                'value_now': value_now,
                'profit': profit
            })

    df_open = pd.DataFrame(rows)

    st.subheader("📦 Offene Lots")
    st.dataframe(df_open)

    if df_open.empty:
        st.warning("Keine offenen Positionen")
        return

    # ==============================
    # PORTFOLIO
    # ==============================
    portfolio = df_open.groupby('asset').agg({
        'value_now': 'sum',
        'profit': 'sum'
    }).reset_index()

    st.subheader("🌍 Portfolio")
    st.dataframe(portfolio)

    st.bar_chart(portfolio.set_index('asset')['profit'])

    # ==============================
    # MSCI BENCHMARK
    # ==============================
    st.subheader("🌍 Benchmark vs MSCI World")

    if USE_YF:
        msci = get_msci(df['date'].min())

        if msci is not None and not msci.empty:
            try:
                total_real = df_open['value_now'].sum()
                total_invested = df[df['type'] == 'buy']['amount'].sum()

                msci_buy = msci['Close'].iloc[0]
                msci_now = msci['Close'].iloc[-1]

                msci_shares = total_invested / msci_buy
                msci_value = msci_shares * msci_now

                col1, col2 = st.columns(2)
                col1.metric("Dein Portfolio", f"{total_real:.2f}")
                col2.metric("MSCI World", f"{msci_value:.2f}")

                st.metric("Differenz", f"{total_real - msci_value:.2f}")

            except Exception as e:
                st.warning(f"Benchmark Fehler: {e}")
        else:
            st.info("MSCI Daten nicht verfügbar")
    else:
        st.info("Installiere yfinance für Benchmark")

    # ==============================
    # EQUITY CURVE (vereinfachte Version)
    # ==============================
    st.subheader("📈 Equity Curve (approx)")

    dates = pd.date_range(df['date'].min(), pd.Timestamp.today())
    values = []

    for d in dates:
        temp = df[df['date'] <= d]
        open_tmp, _ = calculate_fifo(temp)

        total = 0
        for asset, lots in open_tmp.items():
            sym = asset.split("(")[-1].replace(")", "").strip()
            price = prices.get(sym, np.nan)

            for lot in lots:
                total += lot['shares'] * price

        values.append(total)

    equity = pd.DataFrame({'date': dates, 'value': values}).set_index('date')

    st.line_chart(equity)


if __name__ == "__main__":
    app()