from get_storage_data import get_data
import requests
import urllib3
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
urllib3.disable_warnings()

class EmClass:
    """
    Enterprise Manager API Class

    Initial creation of the class sets all the login requirements

    Methods:
    login - logs into the API and sets the access token
    get_bu_servers - gets a list of the backup servers associated with the Enterprise Manager
    get_jobs - gets a list of all the jobs associated with the by server
    get_vm_jobs - gets the vms in the jobs above
    get_buf_ids - gets the backup file ids
    get_backup_files - gets the backup files - requires date to be supplied in UTC
    filter_jobs - filters the backup files by the active jobs
    add_vm_details - adds VM details to the backup_details object
    add_repo_details - adds repo details to the backup_details object
    get_repos - gets repo information - name & capacity
    """
    def __init__(self, address, username, password, threads) -> None:
        self.address = address
        self.username = username
        self.password = password
        self.port = 9398
        self.threads = threads
        self.headers = {"Accept": "application/json"}
        self.login_url = f"https://{self.address}:{self.port}/api/sessionMngr/?v=v1_6"
        self.base_url = f"https://{self.address}:{self.port}/api"

    def get_data(self, url):
         data = requests.get(url, headers=self.headers, verify=False)
         return data.json()

    def login(self):
        res = requests.post(self.login_url, auth=requests.auth.HTTPBasicAuth(self.username, self.password), verify=False)
        self.res_json = res.json()
        self.status_code = res.status_code
        self.res_headers = res.headers
        self.token = self.res_headers.get('X-RestSvcSessionId')
        self.headers['X-RestSvcSessionId'] = self.token

    def get_bu_servers(self):
        bu_url = self.base_url + "/backupServers"
        self.bus_json = self.get_data(bu_url)

    def get_jobs(self, bu_id):
        job_url = f"{self.base_url}/query?type=Job&filter=ScheduleEnabled==True&JobType==Backup&BackupServerUid=={bu_id}"
        self.job_json = self.get_data(job_url)
        self.job_ids = []
        for i in self.job_json['Refs']['Refs']:
            self.job_ids.append({
                "name": i['Name'],
                "id": i['UID']
            })
        
    def get_vm_jobs(self):
        self.vms_per_job = []
        for i in  tqdm(self.job_ids):
            cat_vms_url = f"{self.base_url}/jobs/{i['id']}/includes"
            cat_vms_json= get_data(cat_vms_url)
            vm_names = []
            for k in cat_vms_json['ObjectInJobs']:
                    vm_names.append(k['Name'])
            self.vms_per_job.append({
                "name": i['name'], 
                "vms": vm_names,
                "length": len(vm_names)
            })

    def get_buf_ids(self, old_date_z, bu_id):
        backup_url =  f'{self.base_url}/query?type=BackupFile&filter=CreationTimeUTC>="{old_date_z}"&BackupServerUid=={bu_id}'
        self.backup_json = get_data(backup_url)
        self.ids = [x['UID'] for x in self.backup_json['Refs']['Refs']]
        self.backup_urls = []
        for i in self.ids:
            url = f"{self.base_url}/backupFiles/{i}?format=Entity"
            self.bu_urls.append(url)

    def get_backup_files(self):
        self.backup_details = []
        threads = []
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            for url in tqdm(self.bu_urls):
                threads.append(executor.submit(self.get_data, url))

        for task in as_completed(threads):
            self.backup_details.append(task.result())

    def filter_jobs(self):
        self.filter_jobs = []
        for i in self.backup_details:
            for j in self.job_names:
                if i['Links'][0]['Name'] == j:
                    self.filtered_jobs.append({
                    "creationTime": i['CreationTimeUtc'],
                    "name": i['Links'][0]['Name'],
                    "fileType": i['FileType'],
                    "fileName": i['Name'],
                    "backupFile": i['FilePath'],
                    "BackupSize": i['BackupSize'] / 1024**3,
                    "DataSize": i['DataSize']/ 1024**3
                    })
                
    def add_vm_details(self):
        self.jobs_grouped = []
        for i in tqdm(self.job_names):
            temp_data = []
            for j in self.filtered_jobs:
                if i == j['name']:
                    temp_data.append(j)
            self.jobs_grouped.append({
                "jobName": i,
                "backups": temp_data
            })
            
        for i in self.sorted_cap:
            for j in self.vms_per_job:
                if i['jobName'] == j['name']:
                    i['vmQty'] = j['length']
                    i['vmsInJob'] = j['vms']

    def add_repo_details(self):
        backup_url = self.base_url + "/backups"
        backup_json  = get_data(backup_url)
        self.bu_uuid = [x['UID'] for x in backup_json['Refs']]
        for i in tqdm(self.bu_uuid):
            id = i.split(":")[-1]
            bu_url = self.base_url + f"/backups/{id}?format=Entity"
            res_data = get_data(bu_url)
            res_json = res_data.json()
            self.backup_details.append(res_json)

        for i in self.sorted_cap:
            for j in self.backup_details:
                if i['jobName'] == j['Name']:
                    i['repository'] = j['Links'][0]['Name']


    def get_repos(self):
        repo_url = self.base_url + "/query?type=Repository&format=Entities"
        repo_json = self.get_data(repo_url)
        self.repo_details = []
        for i in repo_json['Entities']['Repositories']['Repositories']:
            cap = round(i['Capacity'] / 1024**3, 4)
            free = round(i['FreeSpace'] / 1024**3, 4)
            used = round(cap - free, 4)
            data = {
            "name": i['Name'],
            "CapacityGB": cap,
            "FreeSpaceGB": free,
            "UsedSpaceGB": used
            }
            self.repo_info.append(data)