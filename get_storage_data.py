from multiprocessing import cpu_count
from EmApiClass import EmClass
from V11apiClass import v11API
import getpass
import json
import logging
import sys
from typing import Any
from rich import print
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.console import Console
from halo import Halo

spinner = Halo(text='Loading', spinner='dots')


logging.basicConfig(filename='app.log', filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s')


def json_writer(name: str, json_data: Any):
    with open(name, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)


def main():
    print("")
    print(":zap: [green] Welcome to the Veeam VBR Assessment![/green] :zap:")
    print("")
    print("This tools is supplied under the MIT licence and is not associated with Veeam")
    print("")
    HOST = input("Enter the Enterprise Manager address: ")
    username = input('Enter Username: ')
    password = getpass.getpass("Enter password: ")
    a_days = int(input("How many days back would you like to assess?: "))
    filter_jobs = Prompt.ask("Assess Backups files connected to active jobs only?", show_choices=True, choices=["Y", "N"])
    filter_bool = False if filter_jobs == "N" else True

    em_api = EmClass()
    status_code = em_api.login(HOST, username, password)

    if status_code != 201:
        sys.exit("Login Unsuccessful, please try again")
    else:
        print("Login Successful")

    spinner.start(text="Getting the backup server list")
    em_api.get_bu_servers()
    spinner.stop()

    table = Table(title="Backup Servers Found")
    table.add_column("Index", justify="center", style="cyan")
    table.add_column("Name", justify="center", style="cyan")

    bu_index = 0
    console = Console()

    if len(em_api.bus_json['Refs']) > 1:
        for index, item in enumerate(em_api.bus_json['Refs']):
            table.add_row(str(index), item['Name'])

        console.print(table)

        while True:
            bu_index = int(input("Please select backup server index to assess: "))
            if bu_index > len(em_api.bus_json['Refs']):
                print("Out of range, please try again")
            else:
                break

    em_api.set_name_id(bu_index)

    spinner.start(text="Getting the job names")
    em_api.get_jobs(filter_bool)
    spinner.stop()

    em_api.get_vm_jobs()

    spinner.start(text="Getting the Backup Files")
    em_api.get_backup_files(a_days)
    spinner.stop()

    spinner.start(text="Filtering Jobs")
    em_api.run_filter_jobs()
    spinner.stop()

    # Next we need I need to change the above so that we group all the job data together

    em_api.add_vm_details()

    export_results = Prompt.ask("Export Backups sorted by jobs?", show_choices=True, choices=["Y", "N"])
    if export_results == "Y":
        print("Jobs Exported")
        json_writer(f'{em_api.bus_name}_backups_by_job.json',
                    em_api.jobs_grouped)

    em_api.run_capacity_sorter()
    em_api.add_repo_details()

    print("")
    print("[green]To collected Proxy and Repo information, the tool needs to log into the VBR direct API.[/green]")
    v11_check = Prompt.ask("Are you happy to proceed?", show_choices=True, choices=["Y", "N"])
    if v11_check == "Y":
        same_creds = Prompt.ask("Are the credentials the same as the Enterprise Manager API?", show_choices=True, choices=["Y", "N"])
        check_host = Prompt.ask("Is the address the same as Enterprise Manager?", show_choices=True, choices=["Y", "N"])
        if check_host == "Y":
            HOST_v11 = em_api.get_address()
        else:
            HOST_v11 = input("VBR server address: ")
        if same_creds != "Y":
            username2 = input('Enter Username: ')
            password2 = getpass.getpass("Enter password: ")
        else:
            username2 = username
            password2 = password
        try:
            spinner.start(text="Getting data")
            v11_api = v11API(HOST_v11, username2, password2)
            v11_api.login()
            v11_api.get_proxies()
            v11_api.get_proxy_info()
            v11_api.get_repos()
            v11_api.get_repo_info()
            v11_api.get_job_data()
            # output the proxy info to new file
            json_writer(f"{em_api.bus_name}_proxy_info.json",
                        v11_api.proxy_info)

            em_api.add_v11_details(v11_api.repo_info, v11_api.job_info)
            spinner.stop()
        except Exception as e:
            logging.error("Error with v11 API", exc_info=True)
            print("v11 API failed, continuing...")
            pass

    json_writer(f"{em_api.bus_name}_capacity_breakdowns.json",
                em_api.sorted_cap)

    # Getting the repository information
    em_api.get_repos()

    json_writer(f"{em_api.bus_name}_all_repository_details.json",
                em_api.repo_info)

    print("")
    results_table = Table(title="Summary Statistics")
    results_table.add_column("Job Name")
    results_table.add_column("Change Rate")
    results_table.add_column("VBK Mean Dedup")
    results_table.add_column("VIB Mean Dedup")
    results_table.add_column("VBK Mean Compress")
    results_table.add_column("VIB Mean Compress")

    for i in em_api.sorted_cap:
        results_table.add_row(i['jobName'], 
                              str(round(i['changeRateBu'], 2)), 
                              str(round(i['vbkMeanDedup'], 2)), 
                              str(round(i['vibMeanDedup'], 2)), 
                              str(round(i['vbkMeanCompress'], 2)), 
                              str(round(i['vibMeanCompress'], 2)))

    console.print(results_table)
    print("All figures are percentages")
    print("")

    cap_table = Table(title="Capacity and Points")
    cap_table.add_column("Job Name")
    cap_table.add_column("Repository")
    cap_table.add_column("Total Cap GB")
    cap_table.add_column("Total VBK")
    cap_table.add_column("Total VIB")
    cap_table.add_column("Total Points")
    for i in em_api.sorted_cap:
        cap_table.add_row(i['jobName'], 
                          i['repository'],
                          str(round(i['totalCap'],2)), 
                          str(round(i['totalVBKCap'],2)), 
                          str(round(i['totalVIBCap'],2)),
                          str(round(i['totalPoints'],2)))

    console.print(cap_table)
    print("")
    print(":fireworks: [green]Complete[/green] :fireworks:")


if __name__ == "__main__":
    main()
