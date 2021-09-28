import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

params = {
    'host':os.getenv('DB_HOST'),
    'user':os.getenv('DB_USER'),
    'password':os.getenv('DB_PASSWORD'),
    'dbname':os.getenv('DB_NAME'),
}

try:
    ps_connection = psycopg2.connect(**params)

    cursor = ps_connection.cursor()

    # call stored procedure
    cursor.execute('select * from employee_leave_table;')

    print("fechting Employee details who pushed changes to the production from function")
    result = cursor.fetchall()
    for row in result:
        print("Id = ", row[0], )
        print("user = ", row[1])
        print("leave_start_data  = ", row[2])
        print("leave_end_data  = ", row[3])

except (Exception, psycopg2.DatabaseError) as error:
    print("Error while connecting to PostgreSQL", error)

finally:
    # closing database connection.
    if ps_connection:
        cursor.close()
        ps_connection.close()
        print("PostgreSQL connection is closed")


