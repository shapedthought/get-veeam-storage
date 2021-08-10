import datetime
import getpass
import time
import sys
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import urllib3
import json
import os
from halo import Halo
spinner = Halo(text='Loading', spinner='dots')

urllib3.disable_warnings()

backup_files = []


def get_data(url, headers, verify):
    try:
        data = requests.get(url, headers=headers, verify=verify)
        data_json = data.json()
        return data_json
    except:
        print(f"Error with {url}")
        pass


def json_writer(name, json_data):
    with open(name, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)

def main():

    PORT = "9398"
    verify = False
    headers = {"Accept": "application/json"}
    HOST = ""

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
            headers['X-RestSvcSessionId'] = headers_data['token']
            HOST = headers_data['host']
        else:
            # User Input if required
            HOST = input("Enter server address: ")
            username = input('Enter Username: ')
            password = getpass.getpass("Enter password: ")
            login_url = f"https://{HOST}:{PORT}/api/sessionMngr/?v=v1_6"
            response = requests.post(login_url, auth=requests.auth.HTTPBasicAuth(
                username, password), verify=verify)
            # Gets the access token and sets the header
            res_headers = response.headers
            token = res_headers.get('X-RestSvcSessionId')
            headers['X-RestSvcSessionId'] = token
            res_save = {
                "token": res_headers.get('X-RestSvcSessionId'),
                "date": res_headers.get('Date'), 
                "host": HOST
            }
            json_writer("headers.json", res_save)

    while True:
        max_threads = int(input("Max Threads? "))
        if max_threads < 1:
            print("Max threads must be higher than 0")
        else:
            break

    # Makes the request to the backupfile endpoint to get the quantity of backups in the last 14-days
    base_url = f"https://{HOST}:{PORT}/api"


    if os.path.exists('backup_ids.json'):
        check_file = input(
            "A list of backups IDs found, use for this run? Y/N ")
    else:
        check_file = "N"

    if check_file == "Y":
        with open('backup_ids.json', 'r') as backup_uids:
            ids = json.load(backup_uids)
    else:
        # Adding check on the backup server, in case there is more than on
        backup_server = base_url + "/backupServers"

        bus_response = requests.get(
            backup_server, headers=headers, verify=verify)

        bus_json = bus_response.json()

        print("Backup Servers Found")
        for index, item in enumerate(bus_json['Refs']):
            print(f"Index: {index}: Name: {item['Name']}")

        bu_index = 0

        while True:
            bu_index = int(
                input("Please select backup server index to assess: "))
            if bu_index > len(bus_json['Refs']):
                print("Out of range, please try again")
            else:
                break

        bu_id = bus_json['Refs'][bu_index]['UID'].split(":")[-1]
        bus_name = bus_json['Refs'][bu_index]['Name']

        utc_now = datetime.datetime.utcnow()
        days = datetime.timedelta(14)
        old_date = utc_now - days
        old_date_z = old_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        backup_url = f'{base_url}/query?type=BackupFile&filter=CreationTimeUTC>="{old_date_z}"&BackupServerUid=={bu_id}'

        print("Getting the Backup File IDs")
        spinner.start()
        backup_res = requests.get(backup_url, headers=headers, verify=verify)
        spinner.stop()

        backup_json = backup_res.json()

        ids = [x['UID'] for x in backup_json['Refs']['Refs']]

    bu_urls = []
    for i in ids:
        url = f"{base_url}/backupFiles/{i}?format=Entity"
        bu_urls.append(url)

    print(
        f"There are a total of {len(ids)} backup files created in the last 14-days")

    test_qty = len(ids) if len(ids) < 100 else 100
    confirm = input(f"Start test of {test_qty} requests, continue? Y/N: ")
    backup_files = []
    if confirm == "Y":
        start = time.time()
        threads = []
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            for url in tqdm(bu_urls):
                threads.append(executor.submit(get_data, url, headers, verify))

            for task in as_completed(threads):
                backup_files.append(task.result())
    else:
        sys.exit("Exiting programme")
    end = time.time()
    execute_time = (end - start) / test_qty
    print(f"Time for per request was {execute_time:.2f} seconds")
    time_required = len(ids) * execute_time
    print(
        f"Total execution time for all {len(ids)} will be {time_required:.2f} seconds")

    with open("backup_ids.json", "w") as json_file:
        json.dump(ids, json_file)

if __name__ == "__main__":
    main()
