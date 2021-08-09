### Veeam Job Capacity Reporter

The VJCR creates a report which maps a Veeam Job with it's assocaited VMs, backups capacity information and repository it is assigned to.

The VJCR uses Veeam's Enterprise Manager APIs to gather this information. In future updates the new Veeam API will be used togather 
information not included in the Enterprise Manager API

How to use:
1. Install Python, remember to add to PATH
2. clone or download the repo
3. Open a terminal to the folder and enter: pip install -r requirements.txt
4. Run: python .\get_storage_data.py
5. Follow the instructions

As there are several steps in the process the program will ask if you wish to save the intermediary data. Selecting either option does not 
affect the further operations.

If you save all the files you will have:
* jobs_details.json > holds all the backup file information
* backups_by_jobs > This maps the backups files to the jobs
* capacity_breakdowns.json > The main output file
* repository_details.json > Capacity information for each repository

This is an ongoing project which will be translated to GO in the future.
