import re
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from VBRapiClass import v11API
from EmApiClass import EmClass
from capacity_sorter import capacity_sorter

app = Flask(__name__)
CORS(app)

"""Experimental API Wrapper for the Get Storage Data report

    Routes:
    * login - login which passes to the Veeam API
        * POST requires the following in the body
            * host - address
            * name - username
            * password - password
    * jobInfo - main report
        * POST requires the following in the body
            * host - address
            * toke - oauth token
            * All other requests need the same data
    * vibCompress - VIB Compression data
    * repos - repos data
    * proxies - proxies data

    Requires flask > pip install flask
"""

@app.route('/login', methods=['POST'])
def login():
    data = json.loads(request.data)
    em_api = EmClass()
    res = em_api.login(data['host'], data['name'], data['password'])
    if res != 201:
        return 'login unsuccessful', 400
    else:
        return jsonify(em_api.token), 200

@app.route('/jobInfo', methods=['POST'])
def jobinfo():
    data = json.loads(request.data)
    host = data['host']
    token = data['token']
    em_api = EmClass()
    em_api.set_host(host)
    em_api.set_headers(token)
    em_api.get_bu_servers()
    em_api.set_name_id(0)
    em_api.get_jobs()
    em_api.get_vm_jobs()
    em_api.get_backup_files(14)
    # em_api.get_backup_files(10)
    em_api.run_filter_jobs()
    em_api.add_vm_details()
    em_api.run_capacity_sorter()
    em_api.add_repo_details()
    
    return jsonify(em_api.sorted_cap), 200

# returns all the backup file data without filtering
@app.route('/vibCompress', methods=['POST'])
def vibCompress():
    data = json.loads(request.get_data)
    host = data['host']
    token = data['token']
    em_api = EmClass()
    em_api.set_host(host)
    em_api.set_headers(token)
    em_api.get_bu_servers()
    em_api.set_name_id(0)
    em_api.get_backup_files(14)
    # em_api.get_backup_files(10)

    return jsonify(em_api.backup_details)



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