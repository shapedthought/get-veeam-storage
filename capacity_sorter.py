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
        last_vbk_files = []
        last_vib_files = []
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
                if len(full_temp) > 0:
                    last_full_bu.append(full_temp[0]['BackupSize'])
                    last_full_da.append(full_temp[0]['DataSize'])
                    file_data = {
                        "fileName": full_temp[0]['fileName'],
                        "creationTime": full_temp[0]['creationTime']
                    }
                    last_vbk_files.append(file_data)
                if len(inc_temp) > 0:
                    last_inc_bu.append(inc_temp[0]['BackupSize'])
                    last_inc_da.append(inc_temp[0]['DataSize'])
                    file_data = {
                        "fileName": inc_temp[0]['fileName'],
                        "creationTime": inc_temp[0]['creationTime']
                    }
                    last_vbk_files.append(file_data)
            crbu = round(((sum(last_inc_bu) / sum(last_full_bu)) * 100),4) if len(last_full_bu) > 0 else 0
            crda = round(((sum(last_inc_da) / sum(last_full_da)) * 100), 4) if len(last_full_da) > 0 else 0
            data = {
                "jobName": i['jobName'],
                "lastFullBu": round(sum(last_full_bu),4),
                "lastFullDa": round(sum(last_full_da),4),
                "lastIncBu": round(sum(last_inc_bu),4),
                "lastIncDa": round(sum(last_inc_da),4),
                "changeRateBu": crbu,
                "changeRateDa": crda,
                "lastVBKs": last_vbk_files,
                "lastVIBs": last_vib_files
            }
            new_averages.append(data)
    return new_averages
