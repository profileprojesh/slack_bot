import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

params = {
    'host':os.getenv('DB_HOST'),
    'user':os.getenv('DB_USER'),
    'password':os.getenv('DB_PASSWORD'),
    'dbname':os.getenv('DB_NAME'),
}

class Db:
    def __init__(self):
        self.conn =None

    def connect(self):
        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        self.conn = psycopg2.connect(**params)
		
        # create a cursor
        cursor = self.conn.cursor()
        return cursor

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
        print('Database connection closed.')
