import getpass
import json
import pprint
import re
import string
import sys
from datetime import datetime

import requests
import urllib3
from tqdm import tqdm

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

# First get the active jobs filtering only the backup type
job_url = base_url + "/query?type=Job&filter=ScheduleEnabled==True"

job_response = requests.get(job_url, headers=headers, verify=verify)

job_json = job_response.json()

# Filter these down to just the names
job_names = [x['Name'] for x in job_json['Refs']['Refs']] # modified to work with the query 

job_ids = []

for i in job_json['Refs']['Refs']:
	job_ids.append({
		"name": i['Name'],
		"id": i['UID']
	})

# job_ids = [x['UID'] for x in job_json['Refs']['Refs']]

# Next we need to get all the backup files so we can get the UIDs
backup_url = base_url + "/backupFiles"

backup_res = requests.get(backup_url, headers=headers, verify=verify)

backup_json = backup_res.json()

# Pull out the UIDs
ids = [x['UID'] for x in backup_json['Refs']]

# Next run a get on each of these files to get the details
confirm = input(f"There are a total of {len(ids)} backups to process, are you happy to continue? Y/N: ")

if confirm != "Y":
	sys.exit("Closing programme")

print("Sending requests to all backup endpoints\n")

backup_details = []
for item in tqdm(ids):	
	url = f"{base_url}/backupFiles/{item}?format=Entity&sortDesc==CreationTimeUtc"
	bu_data = requests.get(url, headers=headers, verify=verify).json()
	backup_details.append(bu_data)

# Next create two lists; one for full backups and the second for incrementals
full_cap = []
inc_cap = []

# Function to do the sorting
def sort_data(data):
		data = {
			"creationTime": item['CreationTimeUtc'],
			"name": item['Links'][0]['Name'],
			"fileName": item['Name'],
			"backupType": item['FileType'],
			"backupFile": item['FilePath'] / 1024**3,
			"BackupSize": item['BackupSize'] / 1024**3,
			"DataSize": item['DataSize']
		}
		return data

filtered_job_names = []
filtered_jobs = []

print("Filtering Jobs\n")

for i in tqdm(backup_details):
	for j in job_names:
		if i['Links'][0]['Name'] == j:
			filtered_jobs.append({
			"creationTime": i['CreationTimeUtc'],
			"name": i['Links'][0]['Name'],
			"fileType": i['FileType'],
			"fileName": i['Name'],
			"backupFile": i['FilePath'],
			"BackupSize": i['BackupSize'] / 1024**3,
			"DataSize": i['DataSize']/ 1024**3
		})


# Next we need I need to change the above so that we group all the job data together
jobs_grouped = []

print("Sorting the backups\n")
for i in tqdm(job_names):
	temp_data = []
	for j in filtered_jobs:
		if i == j['name']:
			temp_data.append(j)
	jobs_grouped.append({
		"jobName": i,
		"backups": temp_data
	})

with open('results.json', 'w') as json_file:
	json.dump(jobs_grouped, json_file, indent=4)

# Next phase is get something useful 
# Need to get some dates

averages = []

for i in jobs_grouped:
	backup_size = 0
	full_points = 0
	data_size = 0
	for j in i['backups']:
		if j['fileType'] == 'vbk':
			full_points += 1
			backup_size += j['BackupSize']
			data_size += j['DataSize']
	averages.append({
		"name": i['jobName'],
		"avBackupSize": backup_size / full_points,
		"avDataSize": data_size / full_points
	})

with open('averages.json', 'w') as json_file:
	json.dump(averages, json_file, indent=4)

bun_results = []

for i in jobs_grouped:
	backup_names = []
	for j in i['backups']:
		# file_start = j['fileName'].split(".")[0]
		file_start = re.split('D202[0-9]', j['fileName'])[0]
		if "." in file_start:
			file_start = file_start.split(".")[0]
		backup_names.append(file_start)
	bun_dedup = list(set(backup_names))
	bun_results.append(bun_dedup)

pprint.pprint(bun_results)

results = []
for i in job_ids:
	cat_vms_url = f"{base_url}/jobs/{i['id']}/includes"
	cat_vms_res = requests.get(cat_vms_url, headers=headers, verify=verify)
	cat_vms_json = cat_vms_res.json()
	vm_names = []
	for k in cat_vms_json['ObjectInJobs']:
			vm_names.append(k['Name'])
	results.append({
		"name": i['name'], 
		"vms": vm_names,
		"length": len(vm_names)
	})
	
with open("vm_jobs.json", "w") as json_file:
	json.dump(results, json_file, indent=4)

print("Complete")

# Note to self, need to find a way of running through all the backup files and getting
# averages against each instead of across the total
