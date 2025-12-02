

import sqlite3


with sqlite3.connect('db.sqlite3') as con:

    cur = con.cursor()
    cur.execute('''DELETE FROM carts_cartitem
        WHERE product_id NOT IN (SELECT id FROM baraa_tbl);
        ''')
    con.commit()
