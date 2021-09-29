import psycopg2
from db import Db

db = Db()
cur = db.connect()


def create_daily_survey_table():

    query="""
        CREATE TABLE daily_survey(
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            question_id VARCHAR(200) NOT NULL,
            answer VARCHAR(50) NOT NULL
        );
        """
        
    try:
        y=cur.execute(query)
        db.commit()
        print("Tables Created successfully")

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)


def create_leave_table():

    query="""
        CREATE TABLE employee_leave (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            leave_start_date DATE NOT NULL,
            leave_end_date DATE NOT NULL,
            remarks VARCHAR(300),
            leave_days INT NOT NULL,
            UNIQUE (user_id, leave_start_date)
        );
        """
        
    try:
        y=cur.execute(query)
        db.commit()
        print("Tables Created successfully")

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

def create_question_table():
    query = """
        CREATE TABLE question (
            id SERIAL PRIMARY KEY,
            text VARCHAR(255) NOT NULL,
            type VARCHAR(50) NOT NULL
        );
        """
    try:
        y=cur.execute(query)
        db.commit()
        print("Question table Created successfully")

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

def create_question_option():
    query = """
        CREATE TABLE question_option (
            id SERIAL PRIMARY KEY,
            value VARCHAR(50) NOT NULL,
            display_text VARCHAR(50) NOT NULL,
            question_id SERIAL NOT NULL,
            CONSTRAINT fk_question FOREIGN KEY(question_id) REFERENCES question(id)
        );
    """

    try:
        y=cur.execute(query)
        db.commit()
        print("Question options created successfully")

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)



if __name__ =="__main__":
    create_question_table()
    create_question_option()
