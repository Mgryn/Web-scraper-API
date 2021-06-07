import os

user = 'root'
password = 'password'
host = 'mongodb'
port = 27017
database = 'flaskdb'

DATABASE_CONNECTION_URI = f'mongodb://{user}:{password}@{host}:{port}/{database}?authSource=admin'

