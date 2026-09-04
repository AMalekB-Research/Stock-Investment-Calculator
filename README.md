# Stock-Investment-Calculator (SIC)

End-to-end UX/UI, Product/Data analyst project


https://github.com/user-attachments/assets/0bc91f0e-32d9-4f1f-836d-3069ac6a07aa



## Overview 

Personal finance is an ever-growing topic.
I have taken a strong interest in this as my future finances depend on it...
The below tool estimates the projected value of a UK stock investment.
using real historical market data pulled live from Yahoo Finance. 
Built to begin the automation process,
initially to practise applying loops, conditions and libraries 
leading me down a rabbit hole into financial logic to a real-world problem I care about.
Using the data to calculate Compound Annual Growth Rate (CAGR) to predict year-by-year returns.

The project allowed me to explore the complete journey from 
problem → concept → interface → working product.

> **Important:** This is an educational and exploratory project. 
It is not intended to provide financial advice or predict future investment returns.

## The Problem

Investing in the stock market can be daunting.   
To then not be able to imagine the potential projection of your investment is another thing.   
Without turning over spreadsheets of historical data and completing mathematical problems,
to separate the numbers from context.

I wanted to create a digital product to help the less experienced mathematicians and brokers
understand how their initial investment, monthly contributions and time in the market
can influence the potential growth of people's savings.


## Who Is This For?

A beginner/intermediate investor who wants to explore “what if?” scenarios without building their own spreadsheet.

Their likely needs:

* Understand how much they could contribute over time
* See the difference between contributions and investment growth
* Experiment with different time horizons
* Compare different stocks
* Understand the assumptions behind the projection
* Get an answer without needing financial modelling knowledge

## Research & Competitive Landscape

Current investment calculators only estimate on an average return rate, risk level   
or no projection at all.

| Tool | Strength | Gap|
|--------|--------|-------|
| Aviva Investments| Simple, trusted| Low, Medium, High growth rate only, no historic stock data|
| Calculator.net | Allows more user input| Users unsure on what to input for return rate|
| Trading121| Real stock data| No projection/"what if" model|
| This Tool (SIC)| Real historical data| To be reviewed later within the project|


## Design Process

* Initial Sketch


## The Analytical Approach 

So.. how?! this tool uses the Compound Annual Growth Rate (CAGR) calculation.

CAGR = (End Value / Start Value)^(1 / Number of Years) − 1

Behind the scenes the calculation is applied year-on-year, 
inline with the users inputed monthly contributions, 
to project an estimated future values.
This calculation tkes into account compounding interest, 
that simple average does not.
The calculation is then saved within a SQL table to be called upon later. 

## Assumptions & Limitations

However this does not capture:
* CAGR smooths returns into a single average — it does not reflect real year-to-year volatility or drawdowns. 
* Past performance (the historical data used) is not indicative of future results.
* The model assumes contributions and reinvestment happen consistently with no fees, taxes, or dividend withholding.

## Validation 

I shared the tool with 4 people and gather quick feedback: 

* All testers we ecstatic with the projected value,
  until I added a section to confirm that this is only an
  "estimate & does not model year-to-year stock-market volatility
  or changing economic conditions."
* Testers response was to request to be able to view their previous investment searches.
  - added.
* Testers wanted to see the split between money in and the growth over the years.
  - added a breakdown chart.
  

## Results/ Outcome 

* Reducing cognitive load allowing users to visualise estimated projections,
  without investing real funds.
* Visual representation of a graph to show protential projections
  along its compounding journey.
* Reducing multi-step manual calculation into a signle guided input form.
* Allows for an easily accessible historical stock performance calculator,
  which can be used by users with no previous finance background.

## What I Would Do Differently 

This project journey was mainly for my own personal use, however if I were to be able to develop on this and collaborate with other teams in a company I would...

Collaborate with research teams and run a larger usability test round. 
To create a more extensive and accurate product for potential users.

Request Devs to: 
* Expand beyond the UK stock market to include USD & index funds comparisons,
  and show the estimate return in the users selected currency.
* Expand on the possibility for the program to take into consideration
  live news on the ticker.
* Add a volatility band or Monte Carlo simulation instead of a single deterministic line.


## Tech Stack

* Language: Python, HTML (JAVA), T-SQL
* Data: yfinance
* Analysis: pandas, numpy etc
* Interface: Streamlit, Flask
