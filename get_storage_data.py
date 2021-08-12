import datetime
import getpass
import json
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

import requests
import urllib3
from halo import Halo
from tqdm import tqdm

spinner = Halo(text='Loading', spinner='dots')
from capacity_sorter import capacity_sorter

urllib3.disable_warnings()
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

def json_writer(name, json_data):
	with open(name, 'w') as json_file:
		json.dump(json_data, json_file, indent=4)

def get_data(url, headers, verify):
    try:
        data = requests.get(url, headers=headers, verify=verify)
        data_json = data.json()
        return data_json
    except Exception as e:
      logging.error(f'Error with {url}', exc_info=True)
      pass

def runner(urls, max_threads, headers, verify):
	threads = []
	items = []
	with ThreadPoolExecutor(max_workers=max_threads) as executor:
		for url in urls:
			threads.append(executor.submit(get_data, url, headers, verify))
		
		for task in as_completed(threads):
			items.append(task.result())
	return items

def main():
	if not os.path.exists("confirm.json"):
		print("Welcome to the VBR Assessment")
		print("This tools is supplied under the MIT licence and is not associated with Veeam")
		confirm = input("Are you happy to continue? Enter YES: ")
		if confirm != "YES":
			sys.exit("Closing Programme")
		confirm_text = {
			"confirmed_date": str(datetime.datetime.utcnow()),
			"confirmation": confirm
		}
		json_writer("confirm.json", confirm_text)

	HOST = input("Enter server address: ")
	username = input('Enter Username: ')
	password = getpass.getpass("Enter password: ")
	a_days = int(input("How many days back would you like to assess?: "))
	while True:
		max_threads = int(input("Max Threads? "))
		if max_threads < 1:
			print("Max threads must be higher than 0")
		else:
			break
	

	PORT = "9398"
	verify = False
	headers = {"Accept": "application/json"}
	login_url = f"https://{HOST}:{PORT}/api/sessionMngr/?v=v1_6"

	response = requests.post(login_url, auth=requests.auth.HTTPBasicAuth(username, password), verify=verify)
	if response.status_code != 201:
		sys.exit("Login Unsuccessful, please try again")
	else:
		print("Login Successful")
	res_headers = response.headers
	token = res_headers.get('X-RestSvcSessionId')
	headers['X-RestSvcSessionId'] = token

	base_url = f"https://{HOST}:{PORT}/api"
	
	# Adding check on the backup server, in case there is more than on
	backup_server = base_url + "/backupServers"
	
	print("Getting the backup server list")

	spinner.start()
	bus_response = requests.get(backup_server, headers=headers, verify=verify)
	spinner.stop()

	bus_json = bus_response.json()

	print("Backup Servers Found")
	for index, item in enumerate(bus_json['Refs']):
		print(f"Index: {index}: Name: {item['Name']}")

	bu_index = 0

	while True:
		bu_index = int(input("Please select backup server index to assess: "))
		if bu_index > len(bus_json['Refs']):
			print("Out of range, please try again")
		else:
			break

	bu_id = bus_json['Refs'][bu_index]['UID'].split(":")[-1]
	bus_name = bus_json['Refs'][bu_index]['Name']

	# First get the active jobs filtering only the backup type

	job_url = f"{base_url}/query?type=Job&filter=ScheduleEnabled==True&JobType==Backup&BackupServerUid=={bu_id}"

	print("Getting the job names")
	spinner.start()
	job_response = requests.get(job_url, headers=headers, verify=verify)
	spinner.stop()

	job_json = job_response.json()

	# Filter these down to just the names
	job_names = [x['Name'] for x in job_json['Refs']['Refs']] 

	job_ids = []

	for i in job_json['Refs']['Refs']:
		job_ids.append({
			"name": i['Name'],
			"id": i['UID']
		})

	# This section is to get VMs per-job, works for perJob too
	vms_per_job = []
	
	print("Getting jobs details")

	# changed back from the thread pool as it broke things
	vms_per_job = []
	for i in  tqdm(job_ids):
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
	days = datetime.timedelta(a_days)
	old_date = utc_now - days
	old_date_z = old_date.strftime('%Y-%m-%dT%H:%M:%SZ')

	# Next we need to get all the backup files so we can get the UIDs
	backup_url =  f'{base_url}/query?type=BackupFile&filter=CreationTimeUTC>="{old_date_z}"&BackupServerUid=={bu_id}'

	print("Getting the Backup File IDs")
	spinner.start()
	backup_res = requests.get(backup_url, headers=headers, verify=verify)
	spinner.stop()
	backup_json = backup_res.json()

	# Pull out the UIDs
	ids = [x['UID'] for x in backup_json['Refs']['Refs']]


	bu_urls = []

	for i in ids:
		url = f"{base_url}/backupFiles/{i}?format=Entity"
		bu_urls.append(url)

	# Next run a get on each of these files to get the details
	confirm = input(f"There are a total of {len(ids)} backups to process, are you happy to continue? Y/N: ")

	if confirm != "Y":
		sys.exit("Closing programme")

	print("Sending requests to all backupfile endpoint")

	backup_details = []
	threads = []
	with ThreadPoolExecutor(max_workers=max_threads) as executor:
		for url in tqdm(bu_urls):
			threads.append(executor.submit(get_data, url, headers, verify))
		
		for task in as_completed(threads):
			backup_details.append(task.result())
	

	backup_export = input("Output the detailed backup data? Y/N: ")
	if backup_export == "Y":
		json_writer(f'{bus_name}_job_details.json', backup_details)


	# Next create two lists; one for full backups and the second for incrementals
	filtered_jobs = []

	print("Filtering Jobs")

	spinner.start()
	for i in backup_details:
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
	spinner.stop()

	# Next we need I need to change the above so that we group all the job data together
	jobs_grouped = []

	print("Sorting the backups")
	for i in tqdm(job_names):
		temp_data = []
		for j in filtered_jobs:
			if i == j['name']:
				temp_data.append(j)
		jobs_grouped.append({
			"jobName": i,
			"backups": temp_data
		})

	export_results = input("Export Backups sorted by job? Y/N: ")
	if export_results == "Y":
		print("Jobs Exported")
		json_writer(f'{bus_name}_backups_by_job.json', jobs_grouped)

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

	print("Performing last Repository related actions")

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

	json_writer(f"{bus_name}_capacity_breakdowns.json", sorted_cap)

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
	
	json_writer("all_repository_details.json", repo_info)
	
	print("Complete")

if __name__ == "__main__":
	main()
