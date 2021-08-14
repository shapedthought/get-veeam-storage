import requests
import urllib3
urllib3.disable_warnings()

class v11API:
    """
    V11 API Class

    Initial creation of the class sets all the login requirements

    Methods:
    login - logs into the API and sets the access token
    check_login - checks if the login was successful
    get_proxies - gets the proxy data
    get_repos - gets the repo data
    get_proxy_info - pulls out the task count for that proxy
    get_repo_info - pulls out the maxTasks and if it is using perVM or perJob
    """
    def __init__(self, address, username, password) -> None:
        self.address = address
        self.username = username
        self.password = password
        self.port = 9419
        self.headers = {"accept": "application/json",
                                    "x-api-version": "1.0-rev1", "Content-Type": "application/x-www-form-urlencoded"}
        self.token_header = {"accept": "application.json", "x-api-version": "1.0-rev1"}
        self.data = {"grant_type" : "password", "username" : self.username, "password": self.password}
    
    def login(self) -> None:
        self.login_url = f"https://{self.address}:{self.port}/api/oauth2/token"
        res = requests.post(self.login_url, data=self.data, headers=self.headers, verify=False)
        self.res_json = res.json()
        self.status_code = res.status_code
        self.token = self.res_json.get('access_token')
        self.token_header['Authorization'] = 'Bearer ' + self.token

    def check_login(self) -> bool:
        if self.check_status != 201:
            return False

    def get_proxies(self) -> None:
        proxy_res = requests.get(f'https://{self.address}:{self.port}/api/v1/backupInfrastructure/proxies', headers=self.token_header, verify=False)
        self.proxy_json = proxy_res.json()

    def get_repos(self) -> None:
        repo_res = requests.get(f'https://{self.address}:{self.port}/api/v1/backupInfrastructure/repositories', headers=self.token_header, verify=False)
        self.repo_json = repo_res.json()

    def get_proxy_info(self) -> None:
        self.proxy_info = []
        for i in self.proxy_json['data']:
            data = {
                "name": i['name'],
                "maxTaskCount": i['server']['maxTaskCount']
            }
            self.proxy_info.append(data)

    def get_repo_info(self) -> None:
        self.repo_info = []
        for i in self.repo_json['data']:
            data = {
                "name": i['name'],
                "maxTaskCount": i['repository']['maxTaskCount'],
                "perVmBackup": i['repository']['advancedSettings']['perVmBackup']
            }
            self.repo_info.append(data)