from database import get_connection #confirming python pyodbc connection to SQL Server

try:
    conn = get_connection()

    print("Connected successfully!")

    cursor = conn.cursor()
    cursor.execute("SELECT 1")

    result = cursor.fetchone()

    print("SQL returned:", result)

    cursor.close()
    conn.close()

except Exception as e:
    print("Connection failed:")
    print(e)