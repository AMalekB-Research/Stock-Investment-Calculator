from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection
from sicni import calculate_investment

import yfinance as yf
import math
import os
import secrets
import hashlib
import base64
import re


app = Flask(__name__)

# =========================================================
# SECURITY / SESSION CONFIGURATION
# =========================================================

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    secrets.token_hex(32)
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # Set True when using HTTPS in production
)

FRONTEND_ORIGIN = os.environ.get(
    "FRONTEND_ORIGIN",
    "http://127.0.0.1:5501"
)

CORS(
    app,
    supports_credentials=True,
    origins=[FRONTEND_ORIGIN],
)


# =========================================================
# HELPERS
# =========================================================

def get_request_json():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {}

    return data


def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT UserID, Email
            FROM Users
            WHERE UserID = ?
            """,
            user_id,
        )

        row = cursor.fetchone()

        if not row:
            session.clear()
            return None

        return {
            "UserID": row[0],
            "Email": row[1],
        }

    except Exception as error:

        print("CURRENT USER ERROR:", error)

        return None

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


def clean_number(value):
    """
    Converts a value into a SQL-safe finite float.

    Rejects:
    - None
    - NaN
    - Infinity
    - non-numeric values
    """

    try:
        number = float(value)

    except (TypeError, ValueError):

        return None

    if not math.isfinite(number):

        return None

    return number


# =========================================================
# PASSWORD HASHING
# =========================================================

def verify_legacy_pbkdf2_sha256(password, stored_hash):
    """
    Verify Django-style PBKDF2-SHA256 hashes.

    Format:
    pbkdf2_sha256$iterations$salt$hash
    """

    try:
        algorithm, iterations, salt, stored_key = stored_hash.split("$", 3)

        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations)

        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
            dklen=32,
        )

        derived_base64 = base64.b64encode(
            derived_key
        ).decode("ascii")

        return secrets.compare_digest(
            derived_base64,
            stored_key,
        )

    except (ValueError, TypeError):
        return False


def verify_password(password, stored_hash):
    """
    Verify supported password hash formats.

    Supports:
    - Django-style pbkdf2_sha256
    - Werkzeug PBKDF2
    """

    if not stored_hash:
        return False, False

    stored_hash = str(stored_hash)

    # Django-style PBKDF2-SHA256
    if stored_hash.startswith("pbkdf2_sha256$"):

        valid = verify_legacy_pbkdf2_sha256(
            password,
            stored_hash
        )

        return valid, False

    # Werkzeug PBKDF2
    if stored_hash.startswith("pbkdf2:"):

        try:
            valid = check_password_hash(
                stored_hash,
                password
            )

            return valid, False

        except (ValueError, TypeError):

            return False, False

    return False, False

# =========================================================
# TICKER / CURRENCY VALIDATION
# =========================================================

def validate_gbp_ticker(ticker):

    """
    Confirms that the Yahoo Finance ticker exists and is
    denominated in GBP.
    """

    ticker = str(
        ticker or ""
    ).strip().upper()

    if not ticker:

        return {
            "valid": False,
            "message": "Please enter a ticker."
        }

    # Only allow sensible Yahoo Finance ticker characters.
    if not re.fullmatch(
        r"[A-Z0-9.\-^=]{1,20}",
        ticker
    ):

        return {
            "valid": False,
            "message": "Please enter a valid stock ticker."
        }

    try:

        stock = yf.Ticker(ticker)

        info = stock.info

        currency = info.get("currency")

        if not currency:

            return {
                "valid": False,
                "message": (
                    f"Could not determine the currency for {ticker}. "
                    "Please check that the ticker is correct."
                )
            }

        currency = str(
            currency
        ).upper().strip()

        if currency != "GBP":

            return {
                "valid": False,
                "message": (
                    f"{ticker} is priced in {currency}, not GBP. "
                    "Please enter a GBP-denominated ticker."
                )
            }

        return {
            "valid": True,
            "ticker": ticker,
            "currency": "GBP",
        }

    except Exception as error:

        print(
            f"Ticker validation error for {ticker}: {error}"
        )

        return {
            "valid": False,
            "message": (
                f"Could not validate ticker {ticker}. "
                "Please check that the ticker is correct."
            )
        }


# =========================================================
# REGISTER
# =========================================================

@app.route("/api/register", methods=["POST"])
def register():

    conn = None
    cursor = None

    try:

        data = get_request_json()

        email = str(
            data.get("email", "")
        ).strip().lower()

        password = str(
            data.get("password", "")
        )

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not email:

            return jsonify({
                "message": "Please enter your email address."
            }), 400

        if len(email) > 255:

            return jsonify({
                "message": "Email address is too long."
            }), 400

        if not password:

            return jsonify({
                "message": "Please enter a password."
            }), 400

        if len(password) < 8:

            return jsonify({
                "message": (
                    "Password must be at least 8 characters."
                )
            }), 400

        if len(password) > 256:

            return jsonify({
                "message": "Password is too long."
            }), 400

        # -------------------------------------------------
        # DATABASE
        # -------------------------------------------------

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT UserID
            FROM Users
            WHERE Email = ?
            """,
            email,
        )

        existing_user = cursor.fetchone()

        if existing_user:

            return jsonify({
                "message": (
                    "An account with that email already exists."
                )
            }), 409

        # -------------------------------------------------
        # PASSWORD HASH
        # -------------------------------------------------

        password_hash = generate_password_hash(
            password
        )

        # -------------------------------------------------
        # CREATE USER
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO Users
            (
                Email,
                PasswordHash
            )
            OUTPUT INSERTED.UserID
            VALUES (?, ?)
            """,
            email,
            password_hash,
        )

        row = cursor.fetchone()

        if not row:

            conn.rollback()

            return jsonify({
                "message": (
                    "We couldn't create your account. "
                    "Please try again."
                ),
                "error": "REGISTRATION_FAILED"
            }), 500

        user_id = int(row[0])

        conn.commit()

        # -------------------------------------------------
        # CREATE SESSION
        # -------------------------------------------------

        session.clear()

        session["user_id"] = user_id

        return jsonify({
            "message": "Account created successfully.",
            "user": {
                "UserID": user_id,
                "Email": email,
            },
        }), 201

    except Exception as error:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print("REGISTER ERROR:", error)

        return jsonify({
            "message": (
                "We couldn't create your account right now. "
                "Please try again."
            ),
            "error": "REGISTRATION_FAILED"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# LOGIN
# =========================================================

@app.route("/api/login", methods=["POST"])
def login():

    conn = None
    cursor = None

    try:

        data = get_request_json()

        email = str(
            data.get("email", "")
        ).strip().lower()

        password = str(
            data.get("password", "")
        )

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not email:

            return jsonify({
                "message": "Please enter your email address."
            }), 400

        if not password:

            return jsonify({
                "message": "Please enter your password."
            }), 400

        if len(email) > 255:

            return jsonify({
                "message": "Invalid email or password."
            }), 401

        # -------------------------------------------------
        # GET ACCOUNT
        # -------------------------------------------------

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                UserID,
                Email,
                PasswordHash
            FROM Users
            WHERE Email = ?
            """,
            email,
        )

        row = cursor.fetchone()

        if not row:

            return jsonify({
                "message": "Invalid email or password."
            }), 401

        user_id = row[0]
        stored_email = row[1]
        password_hash = row[2]

        # -------------------------------------------------
        # VERIFY PASSWORD
        # -------------------------------------------------

        password_is_correct, needs_upgrade = verify_password(
            password,
            password_hash
        )

        if not password_is_correct:

            return jsonify({
                "message": "Invalid email or password."
            }), 401

        # -------------------------------------------------
        # UPGRADE OLD HASH
        # -------------------------------------------------

        if needs_upgrade:

            new_password_hash = generate_password_hash(
                password
            )

            cursor.execute(
                """
                UPDATE Users
                SET PasswordHash = ?
                WHERE UserID = ?
                """,
                new_password_hash,
                user_id,
            )

            conn.commit()

            print(
                f"Password hash upgraded for UserID {user_id}"
            )

        # -------------------------------------------------
        # CREATE SESSION
        # -------------------------------------------------

        session.clear()

        session["user_id"] = int(user_id)

        return jsonify({
            "message": "Login successful.",
            "user": {
                "UserID": user_id,
                "Email": stored_email,
            },
        }), 200

    except Exception as error:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        # IMPORTANT:
        # Technical details stay in the server terminal.
        # They are NOT sent to the user.

        print("LOGIN ERROR:", error)

        return jsonify({
            "message": (
                "We couldn't log you in right now. "
                "Please try again."
            ),
            "error": "LOGIN_FAILED"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# LOGOUT
# =========================================================

@app.route("/api/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "message": "Logged out successfully."
    }), 200


# =========================================================
# CURRENT USER
# =========================================================

@app.route("/api/me", methods=["GET"])
def me():

    user = get_current_user()

    if not user:

        return jsonify({
            "message": "Not logged in."
        }), 401

    return jsonify({
        "user": user
    }), 200


# =========================================================
# GET SAVED INVESTMENTS
# =========================================================

@app.route("/api/investments", methods=["GET"])
def get_investments():

    user = get_current_user()

    if not user:

        return jsonify({
            "message": "Please log in."
        }), 401

    conn = None
    cursor = None

    try:

        conn = get_connection()
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
            FROM investment_data
            WHERE UserID = ?
            ORDER BY
                [Run Date] DESC,
                RunID DESC
            """,
            user["UserID"],
        )

        rows = cursor.fetchall()

        columns = [
            "RunID",
            "Ticker",
            "Initial Investment",
            "Years",
            "Monthly Investment",
            "CAGR",
            "Total Contributions",
            "Growth",
            "Final value",
            "Run Date",
        ]

        investments = []

        for row in rows:

            investment = {}

            for index, column in enumerate(columns):

                value = row[index]

                if hasattr(value, "isoformat"):

                    value = value.isoformat()

                investment[column] = value

            investments.append(investment)

        return jsonify({
            "data": investments
        }), 200

    except Exception as error:

        print(
            "GET INVESTMENTS ERROR:",
            error
        )

        return jsonify({
            "message": (
                "We couldn't load your saved investments "
                "right now. Please try again."
            ),
            "error": "INVESTMENTS_LOAD_FAILED"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# SIC CALCULATION
# =========================================================

@app.route("/api/SIC", methods=["POST"])
def calculate_sic():

    user = get_current_user()

    if not user:

        return jsonify({
            "message": (
                "Please log in before calculating "
                "an investment."
            )
        }), 401

    conn = None
    cursor = None

    try:

        data = get_request_json()

        # -------------------------------------------------
        # GET INPUTS
        # -------------------------------------------------

        ticker = str(
            data.get("ticker", "")
        ).strip().upper()

        initial_investment = clean_number(
            data.get("initial_investment")
        )

        years = clean_number(
            data.get("years")
        )

        monthly_investment = clean_number(
            data.get("monthly_investment")
        )

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if not ticker:

            return jsonify({
                "message": "Please enter a ticker."
            }), 400

        if initial_investment is None:

            return jsonify({
                "message": (
                    "Initial investment must be a valid number."
                )
            }), 400

        if initial_investment < 0:

            return jsonify({
                "message": (
                    "Initial investment cannot be negative."
                )
            }), 400

        if years is None:

            return jsonify({
                "message": (
                    "Years must be a valid number."
                )
            }), 400

        if years <= 0:

            return jsonify({
                "message": (
                    "Years must be greater than zero."
                )
            }), 400

        if monthly_investment is None:

            return jsonify({
                "message": (
                    "Monthly investment must be a valid number."
                )
            }), 400

        if monthly_investment < 0:

            return jsonify({
                "message": (
                    "Monthly investment cannot be negative."
                )
            }), 400

        # -------------------------------------------------
        # GBP VALIDATION
        # -------------------------------------------------

        currency_check = validate_gbp_ticker(
            ticker
        )

        if not currency_check["valid"]:

            return jsonify({
                "message": currency_check["message"],
                "error": "INVALID_CURRENCY"
            }), 400

        ticker = currency_check["ticker"]

        # -------------------------------------------------
        # RUN INVESTMENT CALCULATION
        # -------------------------------------------------

        result = calculate_investment(
            ticker,
            initial_investment,
            years,
            monthly_investment,
        )

        if not result:

            return jsonify({
                "message": (
                    "The investment calculation returned "
                    "no result."
                )
            }), 400

        # -------------------------------------------------
        # NORMALISE RESULT
        # -------------------------------------------------

        final_value = clean_number(
            result.get("Final value")
        )

        total_contributions = clean_number(
            result.get("Total Contributions")
        )

        growth = clean_number(
            result.get("Growth")
        )

        cagr = clean_number(
            result.get("CAGR")
        )

        # -------------------------------------------------
        # SAFETY CHECKS
        #
        # These prevent NaN / Infinity from reaching SQL
        # Server and causing the TDS/RPC float error.
        # -------------------------------------------------

        if final_value is None:

            return jsonify({
                "message": (
                    f"Yahoo Finance returned an invalid "
                    f"final value for {ticker}. "
                    "The calculation was not saved."
                ),
                "error": "INVALID_FINAL_VALUE"
            }), 400

        if total_contributions is None:

            return jsonify({
                "message": (
                    "The calculation produced an invalid "
                    "total contribution value."
                ),
                "error": "INVALID_TOTAL_CONTRIBUTIONS"
            }), 400

        if growth is None:

            return jsonify({
                "message": (
                    "The calculation produced an invalid "
                    "growth value."
                ),
                "error": "INVALID_GROWTH"
            }), 400

        if cagr is None:

            return jsonify({
                "message": (
                    "The calculation produced an invalid "
                    "CAGR value."
                ),
                "error": "INVALID_CAGR"
            }), 400

        # -------------------------------------------------
        # FORCE FINITE VALUES
        # -------------------------------------------------

        result["Final value"] = final_value

        result["Total Contributions"] = (
            total_contributions
        )

        result["Growth"] = growth

        result["CAGR"] = cagr

        # -------------------------------------------------
        # SAVE TO DATABASE
        # -------------------------------------------------

        conn = get_connection()
        cursor = conn.cursor()

        # Generate RunID
        cursor.execute(
            """
            SELECT ISNULL(MAX(RunID), 0) + 1
            FROM investment_data
            """
        )

        run_id_row = cursor.fetchone()

        if not run_id_row:

            return jsonify({
                "message": (
                    "Could not generate a calculation ID."
                ),
                "error": "RUN_ID_FAILED"
            }), 500

        run_id = int(
            run_id_row[0]
        )

        # -------------------------------------------------
        # INSERT
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO investment_data
            (
                RunID,
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
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                CAST(GETDATE() AS DATE)
            )
            """,
            run_id,
            int(user["UserID"]),
            ticker,
            float(initial_investment),
            float(years),
            float(monthly_investment),
            float(cagr),
            float(total_contributions),
            float(growth),
            float(final_value),
        )

        conn.commit()

        # -------------------------------------------------
        # RETURN RESULT
        # -------------------------------------------------

        return jsonify({
            "message": (
                f"{ticker} calculated successfully "
                "and saved."
            ),
            "data": {
                "RunID": run_id,
                "Ticker": ticker,
                "Initial Investment": initial_investment,
                "Years": years,
                "Monthly Investment": monthly_investment,
                "CAGR": cagr,
                "Total Contributions": total_contributions,
                "Growth": growth,
                "Final value": final_value,
            }
        }), 200

    except Exception as error:

        if conn:

            try:
                conn.rollback()
            except Exception:
                pass

        print(
            "SIC ERROR:",
            error
        )

        return jsonify({
            "message": (
                "We couldn't complete that investment "
                "calculation. Please check the ticker and "
                "values and try again."
            ),
            "error": "CALCULATION_FAILED"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# TEST DATABASE CONNECTION
# =========================================================

@app.route("/test-db", methods=["GET"])
def test_database():

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT TOP 5 *
            FROM investment_data
            """
        )

        rows = cursor.fetchall()

        result = []

        for row in rows:

            result.append(
                list(row)
            )

        return jsonify({
            "status": "success",
            "data": result
        }), 200

    except Exception as error:

        print(
            "DATABASE ERROR:",
            error
        )

        return jsonify({
            "status": "error",
            "message": (
                "Database connection test failed."
            ),
            "error": "DATABASE_TEST_FAILED"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "message": "The requested page was not found."
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):

    return jsonify({
        "message": (
            "That action is not allowed."
        )
    }), 405


@app.errorhandler(500)
def internal_server_error(error):

    return jsonify({
        "message": (
            "Something went wrong on the server. "
            "Please try again."
        )
    }), 500


# =========================================================
# START FLASK
# =========================================================

if __name__ == "__main__":

    print("==========================================")
    print("SIC Investment Calculator API")
    print("==========================================")
    print("Server running on:")
    print("http://127.0.0.1:5000")
    print("==========================================")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )