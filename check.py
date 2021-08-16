from EmApiClass import EmClass
import datetime
import getpass
import json
import os
import sys
import time
from typing import List, Dict, Any

import requests
import urllib3
from halo import Halo

spinner = Halo(text='Loading', spinner='dots')

urllib3.disable_warnings()

backup_files: List[str] = []


def get_data(url: str, headers: List[Dict], verify: bool):
    try:
        data = requests.get(url, headers=headers, verify=verify)
        data_json = data.json()
        return data_json
    except:
        print(f"Error with {url}")
        pass


def json_writer(name: str, json_data: Any):
    with open(name, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)


def main():
    if not os.path.exists("confirm_check.json"):
        print("Welcome to the VBR Assessment checker")
        print(
            "This tools is supplied under the MIT licence and is not associated with Veeam")
        confirm = input("Are you happy to continue? Enter YES: ")
        if confirm != "YES":
            sys.exit("Closing Programme")
        confirm_text = {
            "confirmed_date": str(datetime.datetime.utcnow()),
            "confirmation": confirm
        }
        json_writer("confirm.json", confirm_text)

    # PORT = "9398"
    # verify = False
    # headers = {"Accept": "application/json"}
    HOST = ""
    headers_updated = False

    em_api = EmClass()

    # check the headers file if it exists to save entering in the password again
    if os.path.exists('headers.json'):
        with open("headers.json", 'r') as headers_file:
            headers_data = json.load(headers_file)
        date_string = headers_data['date'][:-4]
        old_date = datetime.datetime.strptime(
            date_string, '%a, %d %b %Y %H:%M:%S')
        time_now = datetime.datetime.utcnow()
        min = datetime.timedelta(minutes=15)
        p_time = time_now - min
        if old_date > p_time:
            print("Valid Token found in headers.json file, continuing...")
            em_api.set_headers(headers_data['token'])
            # headers['X-RestSvcSessionId'] = headers_data['token']
            # HOST = headers_data['host']
            headers_updated = True
    if headers_updated == False:
        # User Input if required
        HOST = input("Enter server address: ")
        username = input('Enter Username: ')
        password = getpass.getpass("Enter password: ")

        status_code = em_api.login(HOST, username, password)
        if status_code != 201:
            sys.exit("Login Unsuccessful, please try again")

        res_save = {
            "token": em_api.headers.get('X-RestSvcSessionId'),
            "date": str(datetime.datetime.utcnow()),
            "host": HOST
        }
        json_writer("headers.json", res_save)

    while (max_threads := int(input("Max Threads? "))) < 1: 
        print("Max threads must be higher than 0")
    # while True:
    #     max_threads = int(input("Max Threads? "))
    #     if max_threads < 1:
    #         print("Max threads must be higher than 0")
    #     else:
    #         break

    em_api.set_threads(max_threads)
    # Makes the request to the backupfile endpoint to get the quantity of backups in the last 14-days
    # base_url = f"https://{HOST}:{PORT}/api"

    if os.path.exists('backup_ids.json'):
        check_file = input(
            "A list of backups IDs found, use for this run? Y/N ")
    else:
        check_file = "N"

    if check_file == "Y":
        with open('backup_ids.json', 'r') as backup_uids:
            ids = json.load(backup_uids)
        em_api.set_buf_ids(ids)
    else:
        # Adding check on the backup server, in case there is more than on
        em_api.get_bu_servers()

        # backup_server = base_url + "/backupServers"

        # bus_response = requests.get(
        #     backup_server, headers=headers, verify=verify)

        # bus_json = bus_response.json()

        print("Backup Servers Found")
        for index, item in enumerate(em_api.bus_json['Refs']):
            print(f"Index: {index}: Name: {item['Name']}")

        bu_index = 0

        while True:
            bu_index = int(
                input("Please select backup server index to assess: "))
            if bu_index > len(em_api.bus_json['Refs']):
                print("Out of range, please try again")
            else:
                break

        bu_id = em_api.bus_json['Refs'][bu_index]['UID'].split(":")[-1]

        # utc_now = datetime.datetime.utcnow()
        # days = datetime.timedelta(14)
        # old_date = utc_now - days
        # old_date_z = old_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        # backup_url = f'{base_url}/query?type=BackupFile&filter=CreationTimeUTC>="{old_date_z}"&BackupServerUid=={bu_id}'

        print("Getting the Backup File IDs")
        spinner.start()
        em_api.get_buf_ids(14, bu_id)
        # backup_res = requests.get(backup_url, headers=headers, verify=verify)
        spinner.stop()

        # backup_json = backup_res.json()

        # ids = [x['UID'] for x in backup_json['Refs']['Refs']]

    print(
        f"There are a total of {len(em_api.ids)} backup files created in the last 14-days")

    max_req = 1000 if len(em_api.ids) > 1000 else len(em_api.ids)
    send_req = int(input(f"How many requests to test? Max {max_req}: "))
    send_req = max_req if send_req > max_req else send_req

    # This has all been done in the class now
    # bu_urls = []
    # for i in range(send_req):
    #     url = f"{base_url}/backupFiles/{em_api.ids[i]}?format=Entity"
    #     bu_urls.append(url)

    confirm = input(f"Start test of {send_req} requests, continue? Y/N: ")
    backup_files = []
    if confirm == "Y":
        start = time.time()
        em_api.get_backup_files()
        # threads = []
        # with ThreadPoolExecutor(max_workers=max_threads) as executor:
        #     for url in tqdm(bu_urls):
        #         threads.append(executor.submit(get_data, url, headers, verify))

        #     for task in as_completed(threads):
        #         backup_files.append(task.result())
    else:
        sys.exit("Exiting programme")
    end = time.time()
    execute_time = (end - start) / send_req
    print(f"Time for per request was {execute_time:.2f} seconds")
    time_required = len(em_api.ids) * execute_time
    print(
        f"Total execution time for all {len(em_api.ids)} will be {time_required:.2f} seconds")

    with open("backup_ids.json", "w") as json_file:
        json.dump(em_api.ids, json_file)


if __name__ == "__main__":
    main()
