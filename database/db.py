import psycopg2
from .config import config

class Db:
    conn =None;
    def __init__(self) -> None:
        pass

    def connect(self):
        params = config()

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
