"""Multi-agent financial analysis pipeline using Gemini and Yahoo Finance."""

import os
import re
import json

import yfinance as yf
from dotenv import load_dotenv
from google import genai

load_dotenv()


def normalize_period(period: str) -> str:
    """Normalize a user-supplied period into a yfinance-compatible format."""

    if not period:
        return "6mo"

    p = str(period).strip().lower()
    match = re.match(r"^(\d+)(m|mo|y|d|w)$", p)

    if match:
        num, unit = match.group(1), match.group(2)

        if unit == "m":
            unit = "mo"

        return f"{num}{unit}"

    return p


def summarize_stock_data(stock_data) -> str:
    """Create a compact summary of real market data for the LLM."""

    first = stock_data.iloc[0]
    latest = stock_data.iloc[-1]

    start_price = float(first["Close"])
    end_price = float(latest["Close"])

    pct_change = (
        ((end_price - start_price) / start_price) * 100
        if start_price
        else 0.0
    )

    period_high = float(stock_data["High"].max())
    period_low = float(stock_data["Low"].min())

    first_date = stock_data.index[0].strftime("%Y-%m-%d")
    latest_date = stock_data.index[-1].strftime("%Y-%m-%d")

    return (
        f"Data range: {first_date} to {latest_date}\n"
        f"Starting close: {start_price:.2f}\n"
        f"Latest close: {end_price:.2f}\n"
        f"Change over period: {pct_change:.2f}%\n"
        f"Period high: {period_high:.2f}\n"
        f"Period low: {period_low:.2f}\n"
        f"Latest volume: {int(latest['Volume'])}"
    )


class GeminiAgent:
    """Wrapper around a Gemini model with a specific role."""

    def __init__(self, api_key: str, role: str, system_prompt: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-3.5-flash-lite"
        self.role = role
        self.system_prompt = system_prompt

    def generate(self, prompt: str) -> str:
        full_prompt = (
            f"{self.system_prompt}\n\n"
            f"User Request: {prompt}"
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt
        )

        return response.text


class FinancialTools:
    """Provides access to financial market data."""

    def get_stock_data(self, symbol: str, period: str = "6mo"):
        ticker = yf.Ticker(symbol)
        return ticker.history(period=period)


class FinancialAnalysisTeam:
    """Coordinates the query parser and market analyst agents."""

    def __init__(self, gemini_api_key: str):

        self.tools = FinancialTools()

        self.query_parser = GeminiAgent(
            gemini_api_key,
            "Query Parser",
            """
            You are a financial query parser.

            Extract from the user query:
            - Stock symbol/ticker
            - Analysis type
            - Time period

            Return ONLY valid JSON using:
            {
                "symbol": "AAPL",
                "analysis_type": "comprehensive",
                "time_period": "6mo"
            }
            """
        )

        self.market_analyst = GeminiAgent(
            gemini_api_key,
            "Market Analyst",
            """
            You are a senior financial analyst.

            Analyze the provided market data clearly and professionally.

            Include:
            - Price trend
            - Performance
            - Risk factors
            - Key observations
            - Balanced investment perspective

            Clearly state that the analysis is for educational
            and research purposes and is not financial advice.
            """
        )

    def parse_query(self, query: str):

        response = self.query_parser.generate(query)

        try:
            json_match = re.search(
                r"\{.*\}",
                response,
                re.DOTALL
            )

            data = (
                json.loads(json_match.group())
                if json_match
                else {}
            )

        except Exception:
            data = {}

        symbol = data.get("symbol")

        if not symbol:

            symbol_match = re.search(
                r"\b([A-Z]{1,5})\b",
                query.upper()
            )

            if not symbol_match:
                raise ValueError(
                    "No stock ticker symbol found in query."
                )

            symbol = symbol_match.group(1)

            data = {
                "symbol": symbol,
                "analysis_type": "comprehensive",
                "time_period": "6mo",
            }

        return data

    def analyze_market(self, query_info, stock_data) -> str:

        data_summary = summarize_stock_data(stock_data)

        prompt = (
            f"Analyze stock {query_info['symbol']} "
            f"for the period "
            f"{query_info.get('time_period', '6mo')}.\n\n"

            f"REAL MARKET DATA:\n"
            f"{data_summary}\n\n"

            f"Base your analysis only on the provided data. "
            f"Discuss the observed trend, performance, risks, "
            f"and provide a balanced interpretation."
        )

        return self.market_analyst.generate(prompt)

    def analyze(self, query: str) -> str:

        query_info = self.parse_query(query)

        period = normalize_period(
            query_info.get("time_period", "6mo")
        )

        stock_data = self.tools.get_stock_data(
            query_info["symbol"],
            period
        )

        if stock_data.empty:
            return (
                f"No data available for "
                f"{query_info['symbol']} "
                f"in period {period}."
            )

        return self.analyze_market(
            query_info,
            stock_data
        )


def run_financial_analysis(query: str) -> str:

    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not gemini_api_key:
        return (
            "Error: GEMINI_API_KEY "
            "environment variable is not set."
        )

    team = FinancialAnalysisTeam(gemini_api_key)

    try:
        return team.analyze(query)

    except Exception as e:
        return f"Error during analysis: {e}"