# REQUIREMENTS: requests, flask

from flask import Flask
import flask, json, requests as r

TOKEN = "GITHUB TOKEN"
REP = "REP NAME"

# LOAD THE DATABASE CODE
exec(r.get('https://adamyes.github.io/directs/github.py').text)

app = Flask(__name__)
db = Database(TOKEN, REP)


@app.route('/', methods=['GET', 'POST', 'DELETE'])
def r1():
    headers = flask.request.headers
    path = headers.get('path') if "path" in headers else "."
    if flask.request.method == 'GET':
        # TODO GET SHA
        item = db.get(path)
        if item.type == "directory":
            response = flask.make_response({**{"children": [x.to_dict() for x in item.children]}, **item.to_dict()})
        else:
            response = flask.make_response(item.content)
        response.headers.set('sha', item.sha)
        response.headers.set('type', item.type)
        response.headers.set('path', item.path)
        response.headers.set('name', item.name)
        return response
    elif flask.request.method == 'POST':
        if not "path" in headers: 
            flask.abort(flask.Response("path header not found", 400))
        data = flask.request.data
        try:
            data = json.loads(data)
            print(data)
        except:
            pass
        try:
            db.set(headers.get('path'), data)
        except:
            flask.abort(flask.Response('An error occurred', 400))
        return 'success'
    elif flask.request.method == 'DELETE':
        if not "path" in headers: 
            flask.abort(flask.Response("path header not found", 400))
        try:
            db.remove(headers.get('path'))
        except:
            flask.abort(flask.Response('An error occurred', 400))
        return 'success'

app.run(port=5000)
        

# HOW TO USE IT
# 1) getting data
# make a GET request to localhost:5000 (the port might be differnet)
# The header MUST contain a "path" item for example
# python: requests.get('http://localhost:5000/', headers={'path': 'README.md'})
# javascript: fetch('http://localhost:5000/', {headers: {path: 'README.md'} })
# 
# the headers u get back from the get request will always contain information about the path for example
# response.header => {type, size, sha} type is either file or directory

# 2) SETTING data
# make a post request with the data u want to set, the path must be in the header
# 
# 3) deleting a file or a folder
