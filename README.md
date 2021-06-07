<h1> Web scraper API
    
</h1>

The purpose of the project is to setup an API, which downloads the text or all images from a given webpage.  For images, it additionally transforms them into a Base64 string before storing in the database (MongoDB). The content of the database can then be downloaded by providing Id of the record, given to the record at the time of inserting into the database.

In order to create the environment and setup the server user need to execute

​    docker-compose up

in the project's folder. All of the components for the environment will be downloaded automatically.

The API will start listening on port 5000.

<h2> Functionality
</h2>

In order to download the content of the website, POST method should be sent to /tasks endpoint, containing following parameters:

```python
# site_url - address of the website to scrape
# item_type - type of the items to download - either "images" or "text"
payload = {"url": site_url,
          "item_type": item_type}
```

An example of python script to send a new task:

```python
import requests
import json

# api-endpoint and parameters
endpoint = "http:/localhost:5000/tasks"
site_url = "http://www.your-site-address.com/"
item_type = "images"
payload = {"url":site_url, "item_type":item_type}
r = requests.post(url=endpoint, params=payload)
print(r.text)
```

This will result in an answer containing following information:

```python
{'id': '60be22caee0d390591d19bf9',
'status': 'PENDING',
'type': 'images',
'url': 'http://www.your-site-address.com/'}
```

The record will be vreated in the database and a Celery worker will be started to downolad the contents of the site. The task will be given an Id when the record is created in the database and the status of the record will be set as "PENDING". After the download of contents of the site is completed, the status will be changed to "FINISHED". When the request is received by API, it will check whether site url follow proper scheme, if it doesn't the status will be changed to "FAILED: INVALID URL".

In order to check the status of a task by provided Id, GET method should be sent to an endpoint /tasks/id :

```python
GET /tasks/60be22caee0d390591d19bf9
```

 It is possible to check all the records in the database with GET method sent to /tasks endpoint:

```python
GET /tasks
```

To check the records containg data from a given page, user should send GET method to /tasks endpoint, cointaing url of the page as a parameter:

```python
payload ={'url':'http://www.your-site-address.com/'}
```

Sending POST method to /delete_all endpoint will delete all records from the database.

Download of the data from the database is possible by sending GET method to /item_type/id endpoint:

```python
GET /images/60be22caee0d390591d19bf9
or
GET /text/60be22caee0d390591d19bf9
```

