import datetime
import getpass
import time
import sys

import requests
import urllib3

urllib3.disable_warnings()


def main():
    # User Input
    HOST = input("Enter server address: ")
    username = input('Enter Username: ')
    password = getpass.getpass("Enter password: ")

    PORT = "9398"
    verify = False
    headers = {"Accept": "application/json"}
    login_url = f"https://{HOST}:{PORT}/api/sessionMngr/?v=v1_6"

    # Gets the access token and sets the header
    response = requests.post(login_url, auth=requests.auth.HTTPBasicAuth(
        username, password), verify=verify)
    res_headers = response.headers
    token = res_headers.get('X-RestSvcSessionId')
    headers['X-RestSvcSessionId'] = token

    # Makes the request to the backupfile endpoint to get the quantity of backups in the last 14-days
    base_url = f"https://{HOST}:{PORT}/api"

    utc_now = datetime.datetime.utcnow()
    days = datetime.timedelta(14)
    old_date = utc_now - days
    old_date_z = old_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    backup_url = f'{base_url}/query?type=BackupFile&filter=CreationTimeUTC>="{old_date_z}"'

    backup_res = requests.get(backup_url, headers=headers, verify=verify)

    backup_json = backup_res.json()

    ids = [x['UID'] for x in backup_json['Refs']['Refs']]

    print(f"There are a total of {len(ids)} backups in the last 14-days")

    confirm = input("Start test of 100 requests, continue? Y/N: ")
    if confirm == "Y":
        start = time.time()
        for i in range(100):
            # url = f"{base_url}/backupFiles/{item}?format=Entity&sortDesc==CreationTimeUtc"
            url = f"{base_url}/backupFiles/{i}?format=Entity"
            bu_data = requests.get(url, headers=headers, verify=verify).json()
    else:
        sys.exit("Exiting programme")
    end = time.time()

    execute_time = (end - start) / 100
    print(f"{execute_time:.2f} seconds")
    time_required = len(ids) * execute_time
    print(f"Total execution time {time_required:.2f} seconds")

if __name__ == "__main__":
    main()
