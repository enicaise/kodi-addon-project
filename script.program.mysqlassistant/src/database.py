import mysql.connector
from mysql.connector import Error

def create_connection(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            password=user_password,
            database=db_name
        )
        print("Connection to MySQL DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection

def check_database_structure(connection):
    cursor = connection.cursor()
    # Example query to check if a specific table exists
    cursor.execute("SHOW TABLES LIKE 'videos'")
    result = cursor.fetchone()
    if result:
        print("Table 'videos' exists.")
    else:
        print("Table 'videos' does not exist. Please create it.")
    cursor.close()

def close_connection(connection):
    if connection:
        connection.close()
        print("Connection to MySQL DB closed")