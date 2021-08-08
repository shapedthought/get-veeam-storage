import requests
import urllib3
import pprint
import getpass
from tqdm import tqdm
import re
import json
import sys
from datetime import datetime
import string
from dateutil import parser

urllib3.disable_warnings()

# HOST = input("Enter server address:")
# username = input('Enter Username: ')
# password = getpass.getpass("Enter password: ")

HOST = "192.168.4.44"
username = "administrator@testlab.net"
password = "2Ch1mps4"

PORT = "9398"
verify = False
headers = {"Accept": "application/json"}

login_url = f"https://{HOST}:{PORT}/api/sessionMngr/?v=v1_6"

response = requests.post(login_url, auth=requests.auth.HTTPBasicAuth(username, password), verify=verify)
res_headers = response.headers

token = res_headers.get('X-RestSvcSessionId')

headers['X-RestSvcSessionId'] = token
base_url = f"https://{HOST}:{PORT}/api"

def json_export(name, json_data):
    with open(name, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)

def data_getter(url):
    backup_url = base_url + url
    backup_res = requests.get(backup_url, headers=headers, verify=verify)
    return backup_res.json()

repos = data_getter('/restorePoints')

json_export("restore_basic.json", repos)

repos_id = [x['UID'] for x in repos['Refs']]

repo_detail = []

print("Getting rp details")

for i in tqdm(repos_id):
    guid = i.split(":")[-1]
    data=  data_getter(f"/restorePoints/{guid}/backupFiles")
    repo_detail.append(data)

json_export("restore_detail_bu.json", repo_detail)