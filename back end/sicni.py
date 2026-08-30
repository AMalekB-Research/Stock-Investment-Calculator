import math
import yfinance as yf


def validate_gbp_ticker(ticker):
    """
    Confirm that the requested ticker is priced in GBP.

    Returns:
        ticker_object, currency

    Raises:
        ValueError if the ticker cannot be found or is not GBP.
    """

    ticker = str(ticker or "").strip().upper()

    if not ticker:
        raise ValueError("Please enter a stock ticker.")

    try:
        stock = yf.Ticker(ticker)

        info = stock.fast_info

        currency = info.get("currency")

        if currency is None:
            # Fallback to ticker info if fast_info does not provide currency
            ticker_info = stock.info
            currency = ticker_info.get("currency")

    except Exception as error:
        raise ValueError(
            f"Could not retrieve information for ticker {ticker}."
        ) from error

    if not currency:
        raise ValueError(
            f"Could not determine the currency for {ticker}. "
            "Please check that the ticker is valid."
        )

    currency = str(currency).upper()

    if currency != "GBP":
        raise ValueError(
            f"{ticker} is priced in {currency}, not GBP. "
            "Please enter a GBP-denominated ticker."
        )

    return stock, currency


def calculate_investment(ticker, initial_investment, years, monthly_investment):
    """
    Calculate an investment projection using 10 years of historical
    data for a GBP-denominated ticker.
    """

    ticker = str(ticker or "").strip().upper()

    # ---------------------------------------------------------
    # VALIDATE TICKER AND CURRENCY
    # ---------------------------------------------------------

    stock, currency = validate_gbp_ticker(ticker)

    # ---------------------------------------------------------
    # GET HISTORICAL DATA
    # ---------------------------------------------------------

    history = stock.history(period="10y")

    if history.empty:
        raise ValueError(
            f"No historical data was found for {ticker}."
        )

    # Remove missing closing prices
    history = history.dropna(subset=["Close"])

    if history.empty:
        raise ValueError(
            f"No valid historical price data was found for {ticker}."
        )

    # ---------------------------------------------------------
    # GET START / END PRICE
    # ---------------------------------------------------------

    start_price = float(history["Close"].iloc[0])
    end_price = float(history["Close"].iloc[-1])

    # ---------------------------------------------------------
    # VALIDATE PRICES
    # ---------------------------------------------------------

    if not math.isfinite(start_price):
        raise ValueError(
            f"Invalid starting price returned for {ticker}."
        )

    if not math.isfinite(end_price):
        raise ValueError(
            f"Invalid latest price returned for {ticker}."
        )

    if start_price <= 0 or end_price <= 0:
        raise ValueError(
            f"Invalid historical prices returned for {ticker}."
        )

    # ---------------------------------------------------------
    # VALIDATE USER INPUT
    # ---------------------------------------------------------

    initial_investment = float(initial_investment)
    years = float(years)
    monthly_investment = float(monthly_investment)

    if not math.isfinite(initial_investment) or initial_investment < 0:
        raise ValueError(
            "Initial investment must be a valid positive number."
        )

    if not math.isfinite(years) or years <= 0:
        raise ValueError(
            "Years must be greater than zero."
        )

    if not math.isfinite(monthly_investment) or monthly_investment < 0:
        raise ValueError(
            "Monthly investment must be a valid positive number."
        )

    # ---------------------------------------------------------
    # CAGR
    # ---------------------------------------------------------

    cagr = (end_price / start_price) ** (1 / years) - 1

    if not math.isfinite(cagr):
        raise ValueError(
            f"CAGR calculation produced an invalid value for {ticker}."
        )

    # ---------------------------------------------------------
    # TOTAL CONTRIBUTIONS
    # ---------------------------------------------------------

    months = years * 12

    total_contributions = (
        initial_investment
        + (monthly_investment * months)
    )

    # ---------------------------------------------------------
    # FUTURE VALUE
    # ---------------------------------------------------------

    monthly_rate = (1 + cagr) ** (1 / 12) - 1

    if not math.isfinite(monthly_rate):
        raise ValueError(
            f"Investment rate calculation failed for {ticker}."
        )

    if monthly_rate == 0:
        final_value = total_contributions

    else:
        final_value = (
            initial_investment * ((1 + monthly_rate) ** months)
            + monthly_investment
            * (((1 + monthly_rate) ** months - 1) / monthly_rate)
        )

    # ---------------------------------------------------------
    # GROWTH
    # ---------------------------------------------------------

    growth = final_value - total_contributions

    # ---------------------------------------------------------
    # FINAL SQL-SAFE VALIDATION
    # ---------------------------------------------------------

    values = {
        "CAGR": cagr,
        "Total Contributions": total_contributions,
        "Growth": growth,
        "Final value": final_value,
    }

    for field_name, value in values.items():

        if not math.isfinite(float(value)):
            raise ValueError(
                f"{field_name} produced an invalid value."
            )

    # ---------------------------------------------------------
    # RETURN RESULTS
    # ---------------------------------------------------------

    return {
        "Ticker": ticker,
        "Currency": currency,
        "Initial Investment": initial_investment,
        "Years": years,
        "Monthly Investment": monthly_investment,
        "CAGR": cagr,
        "Total Contributions": total_contributions,
        "Growth": growth,
        "Final value": final_value,
    }