# This function use a file called 'config.ini' with the following format
# [postgres-database]
#    database = 
#    user = 
#    password =  
#    host = 

import configparser

# Function to parse the database configuration file
def config(filename = 'config.ini', section = 'postgres-database'):
    config = configparser.ConfigParser()
    config.read(filename)
    db = {}
    if config.has_section(section):
        params = config.items(section)
        for param in params:
            db[param[0]] = param[1]
    return db
