import re
import flask
import json
from flask import request, jsonify
from V11apiClass import v11API

app = flask.Flask(__name__)

@app.route('/repos', methods=['POST'])
def repos():
    data = json.loads(request.data)
    host = data['host']
    username = data['name']
    password = data['password']
    v11api = v11API(host, username, password)

    v11api.login()

    v11api.get_repos()
    v11api.get_repo_info()

    return jsonify(v11api.repo_info)

@app.route('/proxies', methods=['POST'])
def proxies():
    data = json.loads(request.data)
    host = data['host']
    username = data['name']
    password = data['password']
    v11api = v11API(host, username, password)

    v11api.login()

    v11api.get_proxies()
    v11api.get_proxy_info()

    return jsonify(v11api.proxy_info)

app.run()