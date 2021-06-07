import requests, base64
import os, config
#from celery import Celery
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.image as mpim
#from flask_pymongo import PyMongo
#from bson.objectid import ObjectId

#celery.task(name='tasks.download')
url = "https://www.onet.pl/"
item_type = 'images'

def download(url, item_type):   
    #query = {'_id': ObjectId(ide)}
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    if item_type == 'text':
        [x.extract() for x in soup.findAll(['script', 'style'])]
        # bylo ..soup.get_text('\n', stirp=True)
        text = soup.get_text('\n', strip=True)
        #add_text = {'$set': {'text': text}}
        #task = mongo.db.items.update_one(query, add_text)
        print(type(text))
        return text
    elif item_type == 'images':
        #[x.extract() for x in soup.findAll(['script', 'style'])]
        img_links = [url+img.attrs.get('src') for img in soup.findAll('img')]
        print(img_links)
        imgs = []
        for link in img_links[:10]:
            r = requests.get(link)
            with open('images/'+link.split("/")[-1], 'wb') as f:
                #r.raw.decode_content = True
                f.write(r.content)


            b64_img = base64.b64encode(requests.get(link).content)
            b64_img = b64_img.decode('utf-8')
            imgs.append(b64_img)
            #add_image = {'$set': {str(link): b64_img}}
            #task = mongo.db.items.update_one(query, add_image)
        return imgs
        #pobranie obrazkow oraz przeksztalcenie ich w string (base64)
        #dodanie kolejnych elementow do dokumentu od danym id
        # 'tytul_obrazka': string_base_64
    #status = {'$set': {'status': 'FINISHED'}}
    #task = mongo.db.items.update_one(query, status) 
    ### czy to powinno zwracac jakakolwiek wartosc? ? ? ? ?
    return 'failed'


result = download(url, item_type)
print(result)