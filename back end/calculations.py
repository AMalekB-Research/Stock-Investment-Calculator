from decimal import Decimal


MAX_YEARS = 40
MAX_INITIAL = Decimal("10000000")
MAX_MONTHLY = Decimal("1000000")


def calculate_projection(initial, years, monthly, cagr):

    initial = Decimal(str(initial))
    monthly = Decimal(str(monthly))
    cagr = Decimal(str(cagr))
    years = int(years)

    if initial <= 0:
        raise ValueError("Initial investment must be greater than zero.")

    if initial > MAX_INITIAL:
        raise ValueError("Initial investment is too large.")

    if years < 1 or years > MAX_YEARS:
        raise ValueError("Years must be between 1 and 40.")

    if monthly < 0:
        raise ValueError("Monthly investment cannot be negative.")

    if monthly > MAX_MONTHLY:
        raise ValueError("Monthly investment is too large.")

    annual_investment = monthly * Decimal("12")

    money = initial

    series = [
        {
            "year": 0,
            "value": float(round(money, 2))
        }
    ]

    for year in range(1, years + 1):

        money = money * (Decimal("1") + cagr)

        money += annual_investment

        money = round(money, 2)

        series.append(
            {
                "year": year,
                "value": float(money)
            }
        )

    total_contributions = (
        initial +
        (annual_investment * years)
    )

    growth = money - total_contributions

    return {
        "series": series,

        "total_contributions": float(
            round(total_contributions, 2)
        ),

        "growth": float(
            round(growth, 2)
        ),

        "final_value": float(
            round(money, 2)
        )
    }