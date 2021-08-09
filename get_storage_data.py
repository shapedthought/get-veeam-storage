import getpass
import json
import sys
import datetime

import requests
import urllib3
from tqdm import tqdm

from capacity_sorter import capacity_sorter

urllib3.disable_warnings()

def json_writer(name, json_data):
	with open(name, 'w') as json_file:
		json.dump(json_data, json_file, indent=4)

def get_data(base_url, ep_url, headers, verify):
    job_url = base_url + ep_url
    job_response = requests.get(job_url, headers=headers, verify=verify)
    job_json = job_response.json()
    return job_json

def main():
	HOST = input("Enter server address: ")
	username = input('Enter Username: ')
	password = getpass.getpass("Enter password: ")

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

	job_url = base_url + "/query?type=Job&filter=ScheduleEnabled==True&JobType==Backup"

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

	# This section is to get VMs per-job, works for perJob too
	vms_per_job = []
	for i in job_ids:
		cat_vms_url = f"{base_url}/jobs/{i['id']}/includes"
		cat_vms_res = requests.get(cat_vms_url, headers=headers, verify=verify)
		cat_vms_json = cat_vms_res.json()
		vm_names = []
		for k in cat_vms_json['ObjectInJobs']:
				vm_names.append(k['Name'])
		vms_per_job.append({
			"name": i['name'], 
			"vms": vm_names,
			"length": len(vm_names)
		})

	utc_now = datetime.datetime.utcnow()
	days = datetime.timedelta(14)
	old_date = utc_now - days
	old_date_z = old_date.strftime('%Y-%m-%dT%H:%M:%SZ')

	# Next we need to get all the backup files so we can get the UIDs
	# Updated the endpoint so that it only pulls down the last two weeks for backups
	# backup_url = base_url + "/backupFiles"
	backup_url =  f'{base_url}/query?type=BackupFile&filter=CreationTimeUTC>="{old_date_z}"'

	backup_res = requests.get(backup_url, headers=headers, verify=verify)

	backup_json = backup_res.json()

	# Pull out the UIDs
	# ids = [x['UID'] for x in backup_json['Refs']]
	ids = [x['UID'] for x in backup_json['Refs']['Refs']]

	# Next run a get on each of these files to get the details
	print("")
	confirm = input(f"There are a total of {len(ids)} backups to process, are you happy to continue? Y/N: ")

	if confirm != "Y":
		sys.exit("Closing programme")

	print("Sending requests to all backupfile endpoints")

	backup_details = []
	for item in tqdm(ids):	
		# url = f"{base_url}/backupFiles/{item}?format=Entity&sortDesc==CreationTimeUtc"
		url = f"{base_url}/backupFiles/{item}"
		bu_data = requests.get(url, headers=headers, verify=verify).json()
		backup_details.append(bu_data)
	print("")
	backup_export = input("Output the detailed backup data? Y/N: ")
	if backup_export == "Y":
		json_writer('job_details.json', backup_details)

	# Next create two lists; one for full backups and the second for incrementals
	filtered_jobs = []

	print("")
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

	print("")
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

	print("")
	export_results = input("Export Backups sorted by job? Y/N: ")
	if export_results == "Y":
		print("Jobs Exported\n")
		json_writer('backups_by_job.json', jobs_grouped)

	sorted_cap = capacity_sorter(jobs_grouped)

	# Updating each object with the quantity of VMs
	for i in sorted_cap:
		for j in vms_per_job:
			if i['jobName'] == j['name']:
				i['vmQty'] = j['length']
				i['vmsInJob'] = j['vms']


	# Adding calls to /backup and /backup/id to get the repository info
	backup_url = base_url + "/backups"

	backup_res = requests.get(backup_url, headers=headers, verify=verify)

	backup_json = backup_res.json()

	uids = [x['UID'] for x in backup_json['Refs']]

	backup_details = []

	print("Performing last Repository related actions \n")

	for i in tqdm(uids):
		id = i.split(":")[-1]
		bu_url = base_url + f"/backups/{id}?format=Entity"
		res_data = requests.get(bu_url, headers=headers, verify=verify)
		res_json = res_data.json()
		backup_details.append(res_json)

	for i in sorted_cap:
		for j in backup_details:
			if i['jobName'] == j['Name']:
				i['repository'] = j['Links'][0]['Name']

	json_writer("capacity_breakdowns.json", sorted_cap)

	# Getting the repository information

	repo_url = base_url + "/query?type=Repository&format=Entities"

	repo_res = requests.get(repo_url, headers=headers, verify=verify)

	backup_json = repo_res.json()

	repo_info = []

	for i in backup_json['Entities']['Repositories']['Repositories']:
		cap = round(i['Capacity'] / 1024**3, 4)
		free = round(i['FreeSpace'] / 1024**3, 4)
		used = round(cap - free, 4)
		data = {
			"name": i['Name'],
			"CapacityGB": cap,
			"FreeSpaceGB": free,
			"UsedSpaceGB": used
		}
		repo_info.append(data)
	
	json_writer("repository_details.json", repo_info)
	
	print("Complete")

if __name__ == "__main__":
	main()