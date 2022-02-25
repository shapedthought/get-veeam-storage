from typing import Any, List
import requests
from requests.auth import HTTPBasicAuth
import datetime
import urllib3
from rich.progress import track
from typing import Dict, List, Optional
from capacity_sorter import capacity_sorter
urllib3.disable_warnings()


class EmClass:
    """
    Enterprise Manager API Class

    Initial creation of the class sets the port and basic API headers

    Methods:
    login - logs into the API and sets the access token
    get_bu_servers - gets a list of the backup servers associated with the Enterprise Manager
    get_jobs - gets a list of all the jobs associated with the Veeam server
    get_vm_jobs - gets the vms in the jobs above
    get_buf_ids - gets the backup file ids
    get_backup_files - gets the backup files - take a interger for the quantity of days to analyse
    filter_jobs - filters the backup files by the active jobs
    add_vm_details - adds VM details to the backup_details object
    add_repo_details - adds repo details to the backup_details object
    get_repos - gets repo information - name & capacity
    """

    def __init__(self) -> None:
        self.port = 9398
        self.headers: Dict[Optional[str], Optional[str]] = {"Accept": "application/json"}

    def _get_data(self, url: str) -> Any:
        data = requests.get(url, headers=self.headers, verify=False)
        return data.json()

    def set_threads(self, threads: int) -> None:
        self.threads = threads

    def login(self, address: str, username: str, password: str) -> int:
        self.__address = address
        self.__username = username
        self.__password = password
        self.login_url = f"https://{self.__address}:{self.port}/api/sessionMngr/?v=v1_6"
        self.base_url = f"https://{self.__address}:{self.port}/api"
        auth = HTTPBasicAuth(self.__username, self.__password)
        res = requests.post(self.login_url, auth=auth, verify=False)
        self.token = res.headers.get('X-RestSvcSessionId')
        self.headers['X-RestSvcSessionId'] = self.token
        return res.status_code

    def get_address(self) -> str:
        return self.__address

    # Adds token to the header
    def set_headers(self, token: str) -> None:
        self.headers['X-RestSvcSessionId'] = token

    def set_host(self, host: str) -> None:
        self.__address = host
        self.base_url = f"https://{self.__address}:{self.port}/api"

    # Gets and sets the bu server names
    def get_bu_servers(self) -> None:
        bu_url = self.base_url + "/backupServers"
        self.bus_json: Dict[str, Any] = self._get_data(bu_url)

    # Sets the ID of the backup server
    def set_name_id(self, index) -> None:
        self.bus_name = self.bus_json['Refs'][index]['Name']
        self.bu_id = self.bus_json['Refs'][index]['UID'].split(":")[-1]

    # Gets the jobs filtered by schedule enabled
    # Need to try this with format entity added
    def get_jobs(self, filtered: bool=True) -> None:
        if filtered:
            job_url = f"{self.base_url}/query?type=Job&filter=ScheduleEnabled==True&JobType==Backup&BackupServerUid=={self.bu_id}"
        else:
            job_url = f"{self.base_url}/query?type=Job&filter=JobType==Backup&BackupServerUid=={self.bu_id}"

        self.job_json = self._get_data(job_url)
        self.job_names = [x['Name'] for x in self.job_json['Refs']['Refs']]
        self.job_ids: List[Dict[str, str]] = []
        for i in self.job_json['Refs']['Refs']:
            self.job_ids.append({
                "name": i['Name'],
                "id": i['UID']
            })

    # v11 has /api/v1/jobs but not everyone has it
    def get_vm_jobs(self) -> None:
        # Loops through the job ids and gets back the VM names
        self.vms_per_job = []
        for i in track(self.job_ids, description="Gettings Job Data"):
            # for i in  tqdm(self.job_ids):
            cat_vms_url = f"{self.base_url}/jobs/{i['id']}/includes"
            cat_vms_json = self._get_data(cat_vms_url)
            vm_names: List[str] = []
            for k in cat_vms_json['ObjectInJobs']:
                vm_names.append(k['Name'])
            self.vms_per_job.append({
                "name": i['name'],
                "vms": vm_names,
                "length": len(vm_names)
            })

    def get_backup_files(self, day_qty: int) -> None:
        # Gets the backup ids for all jobs in the timerange and backup server
        utc_now = datetime.datetime.utcnow()
        days = datetime.timedelta(day_qty)
        old_date = utc_now - days
        old_date_z = old_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        backup_url = f'{self.base_url}/query?type=BackupFile&format=Entities&filter=CreationTimeUTC>="{old_date_z}"&BackupServerUid=={self.bu_id}'
        self.backup_json = self._get_data(backup_url)

        self.backup_details = self.backup_json['Entities']['BackupFiles']['BackupFiles']

    def __sort_buf_ids(self):
        # converts the backup ids into their URLs ready for processing
        self.bu_urls: List[str] = []
        for i in self.ids:
            url = f"{self.base_url}/backupFiles/{i}?format=Entity"
            self.bu_urls.append(url)

    def run_filter_jobs(self) -> None:
        # Filters out the backup files to just the ones that have a schedule attached
        self.filtered_jobs: List[Dict[str, Any]] = []
        for i in self.backup_details:
            for j in self.job_names:
                if i['Links'][0]['Name'] == j:
                    self.filtered_jobs.append({
                        "creationTime": i['CreationTimeUtc'],
                        "name": i['Links'][0]['Name'],
                        "fileType": i['FileType'],
                        "fileName": i['Name'],
                        "backupFile": i['FilePath'],
                        "DeduplicationRatio": i['DeduplicationRatio'],
                        "CompressRatio": i['CompressRatio'],
                        "BackupSize": i['BackupSize'] / 1024**3,
                        "DataSize": i['DataSize'] / 1024**3
                    })

    def run_capacity_sorter(self) -> None:
        # Runs the capacity sorter to get the relevant info from the job data
        self.sorted_cap = capacity_sorter(self.jobs_grouped)
        for i in self.sorted_cap:
            for j in self.vms_per_job:
                if i['jobName'] == j['name']:
                    i['vmQty'] = j['length']
                    i['vmsInJob'] = j['vms']

    def add_vm_details(self) -> None:
        # Adds the VM names to the sorted jobs
        self.jobs_grouped = []
        for i in track(self.job_names, description="Sorting the backups"):
            # for i in tqdm(self.job_names):
            temp_data = []
            for j in self.filtered_jobs:
                if i == j['name']:
                    temp_data.append(j)
            self.jobs_grouped.append({
                "jobName": i,
                "backups": temp_data
            })

    def add_repo_details(self) -> None:
        # Adds the repo name to each job object
        backup_url = self.base_url + "/backups"
        backup_json = self._get_data(backup_url)
        self.bu_uuid = [x['UID'] for x in backup_json['Refs']]
        for i in track(self.bu_uuid, description="Add Repo Details"):
            # for i in tqdm(self.bu_uuid):
            id = i.split(":")[-1]
            bu_url = self.base_url + f"/backups/{id}?format=Entity"
            res_json = self._get_data(bu_url)
            self.backup_details.append(res_json)

        for i in self.sorted_cap:
            for j in self.backup_details:
                if i['jobName'] == j['Name']:
                    i['repository'] = j['Links'][0]['Name']

    def add_v11_details(self, repo_info, job_info):
        # Adds the v11 repo tasks to the object, that class needs to be run
        # separately
        for i in repo_info:
            for j in self.sorted_cap:
                if i['name'] == j['repository']:
                    j['repoMaxTasks'] = i['maxTaskCount']
                    j['repoPerVM'] = i['perVmBackup']
        # loops through the v11 job object and adds the proxy info
        for i in job_info['data']:
            for j in self.sorted_cap:
                if i['name'] == j['jobName']:
                    j['backupProxies'] = i['storage']['backupProxies']

    def get_repos(self) -> None:
        # Gets the repos information, runs standalone
        repo_url = self.base_url + "/query?type=Repository&format=Entities"
        repo_json = self._get_data(repo_url)
        self.repo_info: List[Any] = []
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
