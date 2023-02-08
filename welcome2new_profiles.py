import os, sys
import requests
import urllib.parse
import json
import csv
import math
import datetime
from IPython.display import clear_output

#script checks log of previously sent messages, so updating <start_before> to the current date should suffice
#<start_before> en <start_after> are compared to the earliest startdate in the person's affiliations.
#<lim_created_dt> limits selection to profiles created after this date.
#(yyyy-m-d)

lim_created_dt = datetime.datetime(2021, 2, 1)
start_before = datetime.datetime(2023, 2, 8)
start_after = datetime.datetime(2022, 2, 4)

exclude_jobtitles = ['visitingfellow', 'visitingprofessor', 'externalphdcandidate']

file_dir = sys.path[0]
addressees_file = 'addressees.csv'
addressees_arch = 'addressees_archive.csv'

#def url en parameters Pure API
url_pure_person = 'https://research.vu.nl/ws/api/524/persons/active?'
key_pure = input("enter pure API-key with access to persons-endpoint: ")
size = 100
offset = 0

#STAP 1: Persoonsgegevens 'active staff' ophalen uit Pure

#aantal records en cycli vaststellen
response = requests.get(url_pure_person, headers={'Accept': 'application/json'},params={'size': size, 'offset':offset, 'apiKey':key_pure})
no_records = (response.json()['count'])
cycles = (math.ceil(no_records/size))

pure_persons = {}
errors = {}

for request in range (cycles)[0:]:
    offset += size
    response_pure = requests.get(url_pure_person, headers={'Accept': 'application/json'},params={'size': size, 'offset':offset, 'apiKey':key_pure})
    
    clear_output('wait')   
    print ('getting Person data from Pure:',request+1, 'of', cycles, 'x',size,'records')
    
    #loop door individuele persoonsrecords in response
    for count,item in enumerate(response_pure.json()['items'][0:]):  
        list_ids=[]        
        acta_person = 'false'
        
        try:           
            item_created_dt = datetime.datetime.strptime(item['info']['createdDate'][:10], '%Y-%m-%d')
            if 'prettyURLIdentifiers' in item['info']:
                pretty_url = item['info']['prettyURLIdentifiers'][0]
            if 'externalId' in item:
                external_id = item['externalId']
            visibility = item['visibility']['key']
                        
            #bepaal datumbereik aanstellingen
            max_end_dt = datetime.datetime(1900, 1, 1)
            min_start_dt = datetime.datetime(9999, 12, 31)
            job_title = ''
                        
            for affil in item['staffOrganisationAssociations']:
                if affil['organisationalUnit']['externalId'][:3] == 'P06':
                 acta_person = 'true'
                if 'endDate' in affil['period']:
                    affil_end_dt = datetime.datetime.strptime(affil['period']['endDate'][:10], '%Y-%m-%d')
                else: affil_end_dt = datetime.datetime.now() #veld is leeg bij aanstelling voor onbepaalde tijd                    if affil_end_dt > max_end_dt: max_end_dt = affil_end_dt
                if affil_end_dt > max_end_dt:
                    max_end_dt = affil_end_dt
                    job_title = affil['jobTitle']['uri'][affil['jobTitle']['uri'].rfind("/")+1:]
                    email = affil['emails'][0]['value']['value']
                
                affil_start_dt = datetime.datetime.strptime(affil['period']['startDate'][:10], '%Y-%m-%d')
                if affil_start_dt < min_start_dt: min_start_dt = affil_start_dt
                
                                    
            #haal scopus-IDs op 
            if 'ids' in item:
                for countid, extid in enumerate((item['ids'])):
                    if extid['type']['term']['text'][0]['value'] == 'Scopus Author ID':    
                        list_ids.append (extid['value']['value'])

            url_pp = f"https://research.vu.nl/en/persons/{pretty_url}"
            if acta_person == 'false':
                url_vunl = f"https://vu.nl/en/research/scientists/{pretty_url}"
            else:
                url_vunl = f"https://acta.nl/en/research/scientists/{pretty_url}"
                
            pure_persons [item['uuid']] = {'url_pp':url_pp,'url_vunl':url_vunl, 'firstname':item['name']['firstName'], 'lastname':item['name']['lastName'],'au-id':list_ids,'vuid':external_id, 'crtd_dt':item_created_dt,'start_dt':min_start_dt,'end_dt':max_end_dt, 'job_title':job_title,'visibility':visibility, 'email':email}
        
        except Exception as error:
            errors [item['uuid']] = error
    
print('errors:',errors)
           
#STAP 2

#open archive of uuids of persons that already received an e-mail
#with open (addressees_archive, 'r') as arch:

arch_list = []

with open (os.path.join(file_dir, addressees_arch), 'r') as archive:
    read_archive = csv.reader(archive, delimiter=',')
    next(read_archive) #skips header
    for row in read_archive:
        arch_list.append(row[0])
    
with open (os.path.join(file_dir, addressees_file), 'w', newline='', encoding='utf-8') as addressees, open (os.path.join(file_dir, addressees_arch), 'a', newline='') as archive:
    write_adressees = csv.writer(addressees, delimiter=';', escapechar=' ', quoting=csv.QUOTE_NONE, lineterminator='\r\n')
    write_adressees.writerow(['uuid','url_pp','url_vunl', 'vunetid', 'email', 'scopusids', 'jobtitle','visibility'])
    write_archive = csv.writer(archive, delimiter=',', escapechar=' ', quoting=csv.QUOTE_NONE, lineterminator='\r\n')
         
    for au_uuid in pure_persons:
        if start_after < pure_persons[au_uuid]['start_dt'] <= start_before and pure_persons[au_uuid]['job_title'] not in exclude_jobtitles and pure_persons[au_uuid]['visibility'] == 'FREE':
            if au_uuid not in arch_list:
                write_adressees.writerow([au_uuid,pure_persons[au_uuid]['url_pp'],pure_persons[au_uuid]['url_vunl'],pure_persons[au_uuid]['vuid'],pure_persons[au_uuid]['email'],pure_persons[au_uuid]['au-id'],pure_persons[au_uuid]['job_title'],pure_persons[au_uuid]['visibility']])
                write_archive.writerow([au_uuid])
            else: continue




