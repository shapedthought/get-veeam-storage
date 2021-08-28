import datetime
import getpass
import json
import logging
import os
import sys
from typing import Any

from halo import Halo

spinner = Halo(text='Loading', spinner='dots')
from capacity_sorter import capacity_sorter
from EmApiClass import EmClass
from V11apiClass import v11API

logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

def json_writer(name: str, json_data: Any):
	with open(name, 'w') as json_file:
		json.dump(json_data, json_file, indent=4)

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
	
	em_api = EmClass()
	status_code = em_api.login(HOST, username, password)

	if status_code != 201:
		sys.exit("Login Unsuccessful, please try again")
	else:
		print("Login Successful")

	print("Getting the backup server list")

	spinner.start()
	em_api.get_bu_servers()
	spinner.stop()

	print("Backup Servers Found")
	for index, item in enumerate(em_api.bus_json['Refs']):
		print(f"Index: {index}: Name: {item['Name']}")

	bu_index = 0

	while True:
		bu_index = int(input("Please select backup server index to assess: "))
		if bu_index > len(em_api.bus_json['Refs']):
			print("Out of range, please try again")
		else:
			break

	em_api.set_name_id(bu_index)

	print("Getting the job names")
	spinner.start()
	em_api.get_jobs()
	spinner.stop()
	
	print("Getting jobs details")
	em_api.get_vm_jobs()

	print("Getting the Backup Files")
	spinner.start()
	em_api.get_backup_files(a_days)
	spinner.stop()

	print("Filtering Jobs")

	spinner.start()
	em_api.run_filter_jobs()
	spinner.stop()

	# Next we need I need to change the above so that we group all the job data together

	print("Sorting the backups")
	em_api.add_vm_details()

	export_results = input("Export Backups sorted by job? Y/N: ")
	if export_results == "Y":
		print("Jobs Exported")
		json_writer(f'{em_api.bus_name}_backups_by_job.json', em_api.jobs_grouped)

	em_api.run_capacity_sorter()
	em_api.add_repo_details()

	print("To collected Proxy and Repo information, the tool needs to log into the VBR direct API.")
	v11_check = input("Are you happy to proceed? Y/N: ")
	if v11_check == "Y":
		same_creds = input("Are the credentials the same as with the Enterprise Manager API? Y/N: ")
		HOST_v11 = input("VBR server address: ")
		if same_creds != "Y":
			username2 = input('Enter Username: ')
			password2 = getpass.getpass("Enter password: ")
		else:
			username2 = username
			password2 = password
		try: 
			spinner.start()
			v11_api = v11API(HOST_v11, username2, password2)
			v11_api.login()
			v11_api.get_proxies()
			v11_api.get_proxy_info()
			v11_api.get_repos()
			v11_api.get_repo_info()
			# output the proxy info to new file
			json_writer(f"{em_api.bus_name}_proxy_info.json", v11_api.proxy_info)

			em_api.add_v11_details(v11_api.repo_info)
			spinner.stop()
		except Exception as e:
			logging.error("Error with v11 API", exc_info=True)
			print("v11 API failed, continuing...")
			pass

	json_writer(f"{em_api.bus_name}_capacity_breakdowns.json", em_api.sorted_cap)

	# Getting the repository information
	em_api.get_repos()
	
	json_writer(f"{em_api.bus_name}_all_repository_details.json", em_api.repo_info)
	
	print("Complete")

if __name__ == "__main__":
	main()
