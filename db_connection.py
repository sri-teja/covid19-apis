HOST = "localhost"
USER = "<YOUR SQL USERNAME>"
PASS = "<YOUR SQL PASSWORD HERE>"
MYDB = "covid"


## for database
import pymysql
import pymysql.cursors as mc
import contextlib

DictCursor = mc.DictCursor
SSCursor = mc.SSCursor
SSDictCursor = mc.SSDictCursor
Cursor = mc.Cursor

## for database connection
@contextlib.contextmanager
def connection(cursorclass=Cursor,
               host=HOST, user=USER,
               passwd=PASS, dbname=MYDB,
               driver=pymysql):
    connection = driver.connect(
            host=host, user=user, passwd=passwd, db=dbname,
            cursorclass=cursorclass)
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        connection.close()

@contextlib.contextmanager
def cursor(cursorclass=Cursor, host=HOST, user=USER,
           passwd=PASS, dbname=MYDB):
    with connection(cursorclass, host, user, passwd, dbname) as conn:
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

class database:
    def getData(self, query):
        with cursor(SSDictCursor) as cur:
            # print(cur)
            connection = cur.connection
            # print(connection)
            cur.execute(query)
            result = cur.fetchall()
            # print(result)
            return list(result)

    def editData(self, query):
        with cursor(SSDictCursor) as cur:
            # print(cur)
            connection = cur.connection
            # print(connection)
            cur.execute(query)
            num = cur.lastrowid
            # print(num)
            return num

exdb = database()