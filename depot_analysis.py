import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np

def depot_analysis_ui():

    df = pd.read_csv('./data/data.csv')

    df["date"] = pd.to_datetime(df["date"])
    df["type"] = df["type"].str.lower()

    total_transfered_amount = df.loc[
        (df["type"] == "customer_inpayment") |
        (df["type"] == "transfer_inbound"),
        "amount"
    ].sum()

    current_cash_total = df["amount"].sum()
    fees = df["fee"].sum()
    current_cash_total += fees

    zinsen_total = df.loc[df["type"] == "interest_payment", "amount"].sum()
    dividents_total = df.loc[df["type"] == "dividend", "amount"].sum()

    st.header("Depot Analysis")

    col1, col2 = st.columns(2)
    col1.markdown(f"Deposited: {total_transfered_amount:.2f} €")
    col2.markdown(f"Paid Fees: {-fees:.2f} €")

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"Current Cash Balance: \n{current_cash_total:.2f} €")
    col2.markdown(f"Received Interest: \n{zinsen_total:.2f} €")
    col3.markdown(f"Received Dividends: \n{dividents_total:.2f} €")

    labels = ["Deposited", "Interest", "Dividends"]
    values = [total_transfered_amount, zinsen_total, dividents_total]

    fig = px.pie(values=values, names=labels, title="Cash")
    st.plotly_chart(fig)

    df_buy = df[df["type"] == "buy"].copy()
    df_sell = df[df["type"] == "sell"].copy()

    df_buy["amount"] = df_buy["amount"].abs()
    df_sell["amount"] = df_sell["amount"].abs()

    buy_sum = df_buy.groupby("name").agg(
        amount_buy=("amount", "sum"),
        buy_date=("date", "min")
    ).reset_index()

    sell_sum = df_sell.groupby("name").agg(
        amount_sell=("amount", "sum"),
        sell_date=("date", "max")
    ).reset_index()

    summary = pd.merge(
        buy_sum,
        sell_sum,
        on="name",
        how="outer"
    )

    summary[["amount_buy", "amount_sell"]] = summary[["amount_buy", "amount_sell"]].fillna(0)

    summary["buy_date"] = pd.to_datetime(summary["buy_date"])
    summary["sell_date"] = pd.to_datetime(summary["sell_date"])

    summary["holding_days"] = (
        summary["sell_date"] - summary["buy_date"]
    ).dt.days

    summary["return"] = (
        (summary["amount_sell"] - summary["amount_buy"]) /
        summary["amount_buy"]
    )

    summary.loc[summary["amount_buy"] == 0, "return"] = None


    summary["annualized_return"] = np.where(
        summary["holding_days"] > 0,
        (1 + summary["return"]) ** (365 / summary["holding_days"]) - 1,
        None
    )


    summary["sell_display"] = summary["amount_sell"].replace(0, None)
        
        
        
    st.write(df)

    
    st.divider
    

    groups = dict(tuple(df.groupby("symbol")))

    for symbol, sub_df in groups.items():
        name = sub_df["name"].iloc[0]

        st.markdown(
            f"### {name} <span style='font-size:14px; color:gray;'>({symbol})</span>",
            unsafe_allow_html=True
        )

        # sicherstellen, dass type vergleichbar ist
        sub_df["type"] = sub_df["type"].str.lower()

        # aufteilen
        transaction_df = sub_df[(sub_df["type"] == "buy") | (sub_df["type"] == "sell")]
        dividend_df = sub_df[sub_df["type"] == "dividend"]
        others_df = sub_df[(sub_df["type"] != "buy") & (sub_df["type"] != "sell") & (sub_df["type"] != "dividend")]

        # shares korrekt berechnen (ohne dividends)
        buy_df = transaction_df[transaction_df["type"] == "buy"]
        sell_df = transaction_df[transaction_df["type"] == "sell"]

        current_shares = buy_df["shares"].sum() + sell_df["shares"].sum()

        st.markdown(f"**Current Shares:** {current_shares:.2f}")

        # normale Transaktionen
        st.markdown("**Transactions**")
        st.dataframe(transaction_df[["date", "type", "shares", "amount", "price", "fee", "tax"]])

        # Dividenden separat
        if not dividend_df.empty:
            st.markdown("**Dividends**")
            st.dataframe(dividend_df[["date", "amount", "tax"]])
            
        if not others_df.empty:
            st.markdown("**Others**")
            st.dataframe(others_df)