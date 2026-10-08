import streamlit as st
from financial_agents import run_financial_analysis


st.set_page_config(
    page_title="FinAgent",
    page_icon="📈",
    layout="wide"
)

st.title("📈 FinAgent")
st.subheader("AI-Powered Financial Analysis")

st.write(
    "Analyze stocks using real-time market data from Yahoo Finance "
    "and AI-powered financial analysis."
)

query = st.text_input(
    "Enter your stock analysis",
    placeholder="e.g., Analyze AAPL for the last 1 month"
)

if st.button("Analyze Stock"):

    if not query.strip():
        st.warning("Please enter a stock analysis query.")

    else:
        with st.spinner("Analyzing market data..."):
            result = run_financial_analysis(query)

        # Prevent Streamlit from interpreting dollar signs as LaTeX
        result = result.replace("$", "USD ")

        st.markdown("### Analysis")
        st.markdown(result)