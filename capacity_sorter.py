import json
import pprint
import re

import dateutil.parser as parser

with open("results.json") as results_data:
    json_data = json.load(results_data)

file_names = []
new_averages = []

# this is one crazy loop

for i in json_data:
    names = []
    last_full_bu = []
    last_full_da = []
    last_inc_bu = []
    last_inc_da = []
    for j in i['backups']:
        name = re.split('vm-|D20[0-9]+', j['fileName'])[0]
        if "." in name:
            name = name.split(".")[0]
        names.append(name)
    dedup_names = list(set(names))
    # could replace this with the date sorting
    for d in dedup_names:
        full_temp = []
        inc_temp = []
        for k in i['backups']:
            if d in k['fileName']:
                if k['fileType'] == 'vbk':
                    full_temp.append(k)
                elif k['fileType'] == 'vib':
                    inc_temp.append(k)
        full_temp.sort(reverse=True, key= lambda x: parser.parse(x['creationTime']))
        inc_temp.sort(reverse=True, key= lambda x: parser.parse(x['creationTime']))
        last_full_bu.append(full_temp[0]['BackupSize'])
        last_full_da.append(full_temp[0]['DataSize'])
        if len(inc_temp) > 0:
            last_inc_bu.append(inc_temp[0]['BackupSize'])
            last_inc_da.append(inc_temp[0]['DataSize'])
    data = {
        "jobName": i['jobName'],
        "lastFullBu": sum(last_full_bu),
        "lastFullDa": sum(last_full_da),
        "lastIncBu": sum(last_inc_bu),
        "lastIncDa": sum(last_inc_da),
        "changeRateBu": str((round(sum(last_inc_bu) / sum(last_full_bu),4) * 100)) + "%",
        "changeRateDa": str((round(sum(last_inc_da) / sum(last_full_da),4) *100 )) + "%" 
    }
    new_averages.append(data)


with open('new_averages.json', 'w') as json_file:
    json.dump(new_averages, json_file, indent=4)
