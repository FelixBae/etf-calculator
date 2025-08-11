import streamlit as st
import pandas as pd

# 💰 Konstante Parameter
INTEREST_PA = 0.063  # Jahreszins
INTEREST_PM = INTEREST_PA / 12  # Monatszins

# 📈 Berechnungsfunktion
def calculate_months(amount: int, start_kapital: int, gehalt: int):
    investment = start_kapital
    accumulated_interest = 0
    data = []

    for i in range(amount):
        interest_this_month = investment * INTEREST_PM
        investment += gehalt
        accumulated_interest += interest_this_month
        net_worth = investment + accumulated_interest

        data.append({
            "Monat": i + 1,
            "Investiert": investment,
            "Zinsen (Monat)": interest_this_month,
            "Zinsen (Gesamt)": accumulated_interest,
            "Vermögen": net_worth
        })

    return pd.DataFrame(data)

# 🎨 Streamlit UI
def streamlit_ui():
    st.set_page_config(
        layout="wide",
        page_title="ETF-Rechner",
        page_icon="📊"
    )

    st.header("ETF-Rechner")
    st.divider()
    st.write("")
    st.write("")
    st.write("")

    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        start_kapital = st.slider("Start Kapital", min_value=0, max_value=100000, value=10000)
        gehalt = st.slider("Sparrate", min_value=0, max_value=10000, value=1800)
        monate = st.slider("Anzahl Monate", min_value=1, max_value=300, value=12)

    df = calculate_months(monate, start_kapital, gehalt)

    with col2:
        st.line_chart(df.set_index("Monat")[["Vermögen", "Investiert", "Zinsen (Gesamt)"]])
        st.write("")
        st.write("")
        st.write("")

    st.dataframe(df)

# 🚀 Startpunkt
if __name__ == "__main__":
    streamlit_ui()
