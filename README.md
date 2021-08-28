### Veeam Job Capacity Reporter
This is not an official Veeam tool, and it is provided under the MIT licence.

The VJCR creates a report which maps a Veeam Job with it's associated VMs, backups capacity information and repository it is assigned to.

The VJCR uses Veeam's Enterprise Manager APIs to gather most of this this information but there are a couple calls to the v11 API for additional details which are optional. 

The latest version uses a different endpoint for the backup files data so reduces the requests significantly.

How to use:
1. Install Python, remember to add to PATH
2. clone or download the repo
3. Open a terminal to the folder and enter: pip install -r requirements.txt
4. To run tests with: python .\check.py (see below)
5. Run: python .\get_storage_data.py
6. Follow the instructions

check.py is designed to allow you to test how long the tool will take to run with different thread counts and different quantities of requests up to total of 1000.

It will then display the time it took to run the test and the estimated time it will take to run against all the backup files.

When running get_storage_data.py, there are several steps in the process the program will ask if you wish to save the intermediary data. Selecting either option does not affect the further operations, it just means you can keep that data if required. 

If you save all the files you will have:
* jobs_details.json > holds all the backup file information
* backups_by_jobs > This maps the backups files to the jobs
* capacity_breakdowns.json > The main output file
* repository_details.json > Capacity information for each repository

As it is possible that some endpoints may not respond, error logging has been enabled and will be populated if any of the 
backupFiles endpoints fail. If you wish to enable DEBUG in this line:

logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', **level=logging.DEBUG**)

This is an ongoing project which will be translated to GO in the future.
