import pymysql

try:
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="chatbot_db"
    )

    print("Database Connected!")

    conn.close()

except Exception as e:
    print("Error:", e)