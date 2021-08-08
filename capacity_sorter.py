import re

import dateutil.parser as parser

def capacity_sorter(json_data):
    new_averages = []
    for i in json_data:
        names = []
        last_full_bu = []
        last_full_da = []
        last_inc_bu = []
        last_inc_da = []
        if len(i['backups']) > 0:
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
                "lastFullBu": round(sum(last_full_bu),4),
                "lastFullDa": round(sum(last_full_da),4),
                "lastIncBu": round(sum(last_inc_bu),4),
                "lastIncDa": round(sum(last_inc_da),4),
                "changeRateBu": round(((sum(last_inc_bu) / sum(last_full_bu)) * 100),4),
                "changeRateDa": round(((sum(last_inc_da) / sum(last_full_da)) * 100), 4)
            }
            new_averages.append(data)
    return new_averages
