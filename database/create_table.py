import psycopg2
from config import config
from db import Db

def create_tables():
    db = Db()
    cur = db.connect()

    query="""
        CREATE TABLE daily_survey(
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer VARCHAR(50) NOT NULL
        );
        """

        
    try:
        y=cur.execute(query)
        db.commit();
        print("Tables Created successfully")

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)


if __name__ =="__main__":
    create_tables()
