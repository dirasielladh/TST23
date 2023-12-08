# Module import
import mariadb
import sys

# Menghubungkan MariaDB 
db = None
try:
    db = mariadb.connect(
		user="root",
		password="",
		host="localhost",
		port=3306,
		database="database"
  
	)
    
except mariadb.Error as error:
    print(f"Connecting error to MariaDB: {error}")
    sys.exit(1)