import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


# =========================================================
# LOAD .ENV
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():

    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={os.getenv('DB_SERVER')};"
        f"DATABASE={os.getenv('DB_DATABASE')};"
        f"UID={os.getenv('DB_USERNAME')};"
        f"PWD={os.getenv('DB_PASSWORD')};"
        "TrustServerCertificate=yes;"
    )

    return pyodbc.connect(connection_string)


# =========================================================
# CREATE USER
# =========================================================

def create_user(email, password_hash):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.Users
            (
                Email,
                PasswordHash
            )
            OUTPUT INSERTED.UserID
            VALUES (?, ?)
            """,
            email,
            password_hash
        )

        user_id = cursor.fetchone()[0]

        conn.commit()

        return user_id

    finally:

        conn.close()


# =========================================================
# GET USER
# =========================================================

def get_user(email):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                UserID,
                Email,
                PasswordHash
            FROM dbo.Users
            WHERE Email = ?
            """,
            email
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "UserID": row[0],
            "Email": row[1],
            "PasswordHash": row[2]
        }

    finally:

        conn.close()


# =========================================================
# SAVE INVESTMENT
# =========================================================

def save_investment(
    user_id,
    ticker,
    initial_investment,
    years,
    monthly_investment,
    cagr,
    total_contributions,
    growth,
    final_value,
    run_date
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.investment_data
            (
                UserID,
                Ticker,
                [Initial Investment],
                Years,
                [Monthly Investment],
                CAGR,
                [Total Contributions],
                Growth,
                [Final value],
                [Run Date]
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            user_id,
            ticker,
            initial_investment,
            years,
            monthly_investment,
            cagr,
            total_contributions,
            growth,
            final_value,
            run_date
        )

        conn.commit()

    finally:

        conn.close()


# =========================================================
# GET USER'S INVESTMENTS
# =========================================================

def get_user_investments(user_id):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                RunID,
                Ticker,
                [Initial Investment],
                Years,
                [Monthly Investment],
                CAGR,
                [Total Contributions],
                Growth,
                [Final value],
                [Run Date]
            FROM dbo.investment_data
            WHERE UserID = ?
            ORDER BY RunID DESC
            """,
            user_id
        )

        columns = [
            column[0]
            for column in cursor.description
        ]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    finally:

        conn.close()