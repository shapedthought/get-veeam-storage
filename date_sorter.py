import json
import pprint
import re
from datetime import datetime
import dateutil.parser as parser

with open("results.json") as results_data:
    json_data = json.load(results_data)

job = json_data[0]

file_names = []
new_averages = []

backups = job['backups']

backups.sort(reverse=True, key= lambda x: parser.parse(x['creationTime']))

fulls = []
incs = []

for i in backups:
    if i['fileType'] == 'vbk':
        fulls.append(i)
    if i['fileType'] == 'vib':
        incs.append(i)

last_full = fulls[0]
last_inc = incs[0]

pprint.pprint(last_full)
pprint.pprint(last_inc)

print(f"Last Full Data: {last_full['DataSize']}")
print(f"Last inc Data: {last_inc['DataSize']}")
print(f"Last Full Backup: {last_full['BackupSize']}")
print(f"Last Full Backup: {last_inc['BackupSize']}")
change_rate = (last_full['BackupSize']) / (last_inc['BackupSize'])
print(f"Last change rate: {change_rate}")