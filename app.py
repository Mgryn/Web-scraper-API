import requests
import base64
import os
import config
from celery import Celery
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from urllib.parse import urljoin, urlparse


def create_app():
    """Create Flask app, connect it to MongoDB and redis"""
    flask_app = Flask(__name__)
    flask_app.config['MONGO_URI'] = config.DATABASE_CONNECTION_URI
    flask_app.config.update(
    CELERY_BROKER_URL=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
    CELERY_RESULT_BACKEND=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')
    )
    flask_app.app_context().push()
    return flask_app


def make_celery(app):
    """Create Celery worker, which will manage downloading data"""
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.conf.update(app.config)
    celery.Task = ContextTask
    return celery
    

def to_dict(data):
    """Transform information about a record into a dictionary"""
    return {'id': str(data.get('_id')), 'url': data.get('url'),
     'type': data.get('item_type'), 'status':data.get('status')}


def is_valid(url):
    """Check if provided url has proper scheme"""
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)


def get_all_images(url):
    """Download all the images from given url,
    return them as a list"""
    soup = BeautifulSoup(requests.get(url).content, "html.parser")
    urls = []
    # select only images
    for img in soup.find_all('img'):
        # select only links with a source image
        img_url = img.attrs.get('src')
        if not img_url:
            continue
        # creat full url for the image
        img_url = urljoin(url, img_url)
        try:
            # clean url from query parameters
            pos = img_url.index('?')
            img_url = img_url[:pos]
        except ValueError:
            pass
        # if full url has a proper scheme, add it to list
        if is_valid(img_url):
            urls.append(img_url)
    return urls

def download_b64(url):
    """Download image from a given url,
    transform it into a Base64 string with utf-8 coding"""
    response = requests.get(url).content
    # transforming image into a Base64 string
    my_string = base64.b64encode(response)
    my_string = my_string.decode('utf-8')
    # extract filename from the url
    filename = url.split('/')[-1].split('.')[-2]
    # extract image extension from the url
    img_type = url.split('.')[-1]
    # return as dictionary, ready to be put into database
    return {filename: {'img_type': img_type, 'img':my_string}}

app = create_app()
mongo = PyMongo(app)
celery = make_celery(app)


@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    """ Create new download tasks,
    get information about existing ones."""
    # POST: create new task to download text/images
    if request.method == 'POST':
        # parse the arguments
        url = request.args.get('url')
        item_type = request.args.get('item_type')
        # create a record in the database
        data ={'url': url, 'item_type': item_type, 'status': 'PENDING'}
        task = mongo.db.items.insert_one(data)
        # get Id of created record
        id = str(task.inserted_id)
        # send download task to celery worker
        celery.send_task('tasks.download', args=[url, item_type, id], kwargs={})
        # return information about record and task status
        return jsonify({'id': id, 'url': url, 'type': item_type, 'status':'PENDING'}), 200
    # GET: retrieve information about existing records
    elif request.method == 'GET':
        url = request.args.get('url')
        # if url is not provided, return all records
        if url is None:
            data = mongo.db.items.find()
        else:
            # otherwise return only records with provided url
            data = mongo.db.items.find({'url': url})
        if data is None:
            return jsonify('there is no such record'), 200
        data_json = []
        for x in data:
            data_json.append(to_dict(x))    
        return jsonify(data_json), 200


@app.route('/tasks/<string:id>', methods=['GET'])
def return_task(id):
    """Information about a single task.
    Requires id, created when adding record to database"""
    record = mongo.db.items.find({'_id': ObjectId(id)})
    if record is None:
        return jsonify('there is no such record')
    data_json = []
    for x in record:
        data_json.append(to_dict(x))
    return jsonify(data_json), 200


@app.route('/text/<string:id>', methods=['GET'])
def get_text(id):
    """Get the text downloaded from a webpage"""
    record = mongo.db.items.find_one({'_id': ObjectId(id)})
    if record is None:
        return jsonify('there is no such record')
    retrieved_txt = {'url': record['url'], 'text': record['text']}
    return jsonify(retrieved_txt)

@app.route('/images/<string:id>', methods=['GET'])
def get_images(id):
    # retrieve only images from the record,
    record = mongo.db.items.find_one({'_id': ObjectId(id)},
        {'_id':False, 'item_type':False, 'status':False, 'url':False})
    if record is None:
        return jsonify('there is no such record')
    # get the names of saved images
    keys = record.keys()
    img_dict = {}
    for key in keys:
        # add images to the dictionary
        img_dict.update({key:record[key]})
    return jsonify(img_dict)


@app.route('/delete_all', methods=['POST'])
def delete_mongo():
    """Delete all record from the database"""
    mongo.db.items.remove({})
    return jsonify('database dropped'), 200


@celery.task(name='tasks.download')
def download(url, item_type, ide):
    """download the data from given url, 
    send it to database with celery worker"""   
    query = {'_id': ObjectId(ide)}
    # if url doesn't have proper structure do not download
    if not is_valid(url):
        # update record status
        status = {'$set': {'status': 'FAILED: INVALID URL'}}
        task = mongo.db.items.update_one(query, status)
        # exit without downloading
        return 404
    if str(item_type) == "images":
        img_urls = get_all_images(url)
        for img_url in img_urls:
            # download image as Base64 string
            b64_img = download_b64(img_url)
            # add the image to the record in the database
            add_image = {'$set': b64_img}
            task = mongo.db.items.update_one(query, add_image)
    elif str(item_type) == "text":
        soup = BeautifulSoup(requests.get(url).text, 'html.parser')
        # filter out script and style elements
        [x.extract() for x in soup.findAll(['script', 'style'])]
        # clean text from whitespace at the ends
        text = soup.get_text(strip=True)
        # add downloaded text to teh record in the database
        add_text = {'$set': {'text': text}}
        task = mongo.db.items.update_one(query, add_text)
    # after succesful download, update status of the record
    status = {'$set': {'status': 'FINISHED'}}
    task = mongo.db.items.update_one(query, status) 
    return 200
