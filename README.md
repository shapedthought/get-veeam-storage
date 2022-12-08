### Veeam Job Capacity Reporter

This is not an official Veeam tool, and it is provided under the MIT license.

The VJCR creates a report which maps a Veeam Job with it's associated VMs, backups capacity information and repository it is assigned to.

The VJCR uses Veeam's Enterprise Manager APIs to gather most of this this information but there are a couple calls to the v11 API for additional details which are optional.

The latest version uses a different endpoint for the backup files data so reduces the requests significantly.

How to use:

1. Install Python, remember to add to PATH
2. clone or download the repo
3. Open a terminal to the folder and enter: pip install -r requirements.txt
4. Run: python .\get_storage_data.py

A user with Portal Administrator will be required to run the tool, Portal User does not have sufficient privileges to access the required data.

When running get_storage_data.py, there are several steps in the process the program will ask if you wish to save the intermediary data. Selecting either option does not affect the further operations, it just means you can keep that data if required.

All Capacity Figures are in GB.

If you save all the files you will have:

- jobs_details.json > holds all the backup file information
- backups_by_jobs > This maps the backups files to the jobs
- capacity_breakdowns.json > The main output file
- repository_details.json > Capacity information for each repository

As it is possible that some endpoints may not respond, error logging has been enabled and will be populated if any of the
backupFiles endpoints fail. If you wish to enable DEBUG in this line:

logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', **level=logging.DEBUG**)
