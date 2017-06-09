#/bin/python

import argparse
import json
import os
import requests
import time

from requests.adapters import HTTPAdapter

class Auth:

    auth_url = "https://identity.api.rackspacecloud.com/v2.0/tokens"
    auth_headers = {'Content-type': 'application/json'}

    def __init__(self, user, api_key):
        self.user = user
        self.api_key = api_key

    def auth_call(self):
        self.auth_data = json.dumps({"auth": {'RAX-KSKEY:apiKeyCredentials': {'username': self.user, 'apiKey': self.api_key}}})
        self.auth_request = s.post(self.auth_url, data=self.auth_data, headers=self.auth_headers)
        self.token_raw = self.auth_request.json()['access']['token']['id']
        self.token = str(self.token_raw)
        return self.token
        
class RetryHTTPAdapter(HTTPAdapter):

    SECONDS_BETWEEN_RETRIES = 10

    def __init__(self, retry_time=120, *args, **kwargs):
        self.retry_time = retry_time
        super(RetryHTTPAdapter, self).__init__(*args, **kwargs)

    def send(self, *args, **kwargs):
        for _ in range(int(self.retry_time / self.SECONDS_BETWEEN_RETRIES)):
            response = super(RetryHTTPAdapter, self).send(*args, **kwargs)
            if response.status_code in (200, 201, 202, 203, 204):
                break
            time.sleep(self.SECONDS_BETWEEN_RETRIES)
        return response

s = requests.Session()
s.mount('http://', RetryHTTPAdapter(retry_time=60))
s.mount('https://', RetryHTTPAdapter(retry_time=60))

#EXAMPLE USAGE
#s.get('http://example.com')
        
def dns_export_import_single(srcddi, srctoken, dstddi, dsttoken, custom_dns_id):
    #Export the Domain
    export_dns_endpoint = 'https://dns.api.rackspacecloud.com/v1.0/%s/domains/%s/export' % (srcddi, custom_dns_id)
    export_dns_headers = {'X-Auth-Token': srctoken}
    export_dns_get = s.get(export_dns_endpoint, headers=export_dns_headers)
    export_dns_joburlraw = export_dns_get.json()['callbackUrl']
    export_job_check = s.get(export_dns_joburlraw, headers=export_dns_headers)
    #Check Export Job
    while str(export_job_check.json()['status']) == 'RUNNING':
        time.sleep(5)
        export_job_check = s.get(export_dns_joburlraw, headers=export_dns_headers)
        
    if str(export_job_check.json()['status']) != 'COMPLETED':
        print "There was a problem with the export job for domain ID : " + str(custom_dns_id)
        print str(export_job_check.text)
        quit()
    
    #Now that the job is completed move on to importing the domain
    export_dns_joburl = str(export_dns_joburlraw) + '?showDetails=true'
    export_dns_bind9_request = s.get(export_dns_joburl, headers=export_dns_headers)
    export_dns_bind9_text = ''
    for line in export_dns_bind9_request.json()['response']['contents'].splitlines():
        if 'ipadmin.stabletransit.com.' in line:
            bind_line_list = line.split()
            export_dns_bind9_text += bind_line_list[0] + '\t\t' + bind_line_list[1] + '\tIN\tSOA\t' + 'ns.rackspace.com. ' + admin_email + ' ' + bind_line_list[6] + ' ' + bind_line_list[7] + ' ' + bind_line_list[8] + ' ' + bind_line_list[9] + ' ' + bind_line_list[10] + '\n'
        if 'dns1.stabletransit.com.' in line:
            continue
        if 'dns2.stabletransit.com.' in line:
            continue
        else:
            export_dns_bind9_text += line + '\n'
    export_dns_bind9_json = json.dumps(export_dns_bind9_text)
    if export_dns_bind9_text == "":
        print "\nNo records found to import for this domain, quitting..."
        quit()
    if import_option != True:
        print "\nImport option not used, printing Bind9 export below quitting:\n"
        print export_dns_bind9_json
        quit()
    dns_import_data = '{"domains" : [ {"contentType" : "BIND_9", "contents" : %s} ]}' % export_dns_bind9_json
    #Before we import this domain we need to remove it from the origin account
    print "\nPreparing to remove domain ID : " + str(custom_dns_id) + " from source account"
    print "\nHere is the raw json formated Bind9 output if the import fails and has to be manually retried via the API:\n"
    print str(dns_import_data)
    remove_domain_url = 'https://dns.api.rackspacecloud.com/v1.0/%s/domains?id=%s' % (srcddi, custom_dns_id)
    remove_domain_request = s.delete(remove_domain_url, headers=export_dns_headers)
    remove_domain_job = remove_domain_request.json()['callbackUrl']
    remove_domain_job_url = str(remove_domain_job) + '?showDetails=true'
    remove_domain_check = s.get(remove_domain_job_url, headers=export_dns_headers)
    while str(remove_domain_check.json()['status']) == 'RUNNING':
        time.sleep(5)
        remove_domain_check = s.get(remove_domain_job_url, headers=export_dns_headers)

    if str(remove_domain_check.json()['status']) != 'COMPLETED':
        print "\nThere was a problem with the delete job for domain ID : " + str(custom_dns_id)
        print "\nStatus: " + str(remove_domain_check.json()['status'])
        if str(remove_domain_check.json()['status']) == 'ERROR':
            print '\nError Message : ' + str(remove_domain_check.json()['error'])

    if str(remove_domain_check.json()['status']) == 'COMPLETED':
        print "\nDomain removal successful, preparing to import domain to destination account"
        time.sleep(10)
        
        import_dns_endpoint = 'https://dns.api.rackspacecloud.com/v1.0/%s/domains/import' % dstddi
        import_dns_headers = {'X-Auth-Token': dsttoken, 'Accept': 'application/json', 'Content-Type': 'application/json'}
        import_dns_request = s.post(import_dns_endpoint, data=dns_import_data, headers=import_dns_headers)
        print "\nImport DNS response : " + str(import_dns_request.text)
        import_dns_job = import_dns_request.json()['callbackUrl']
        import_dns_job_url = str(import_dns_job) + '?showDetails=true'
        print "\nImport dns job URL : " + str(import_dns_job_url)
        import_job_headers = {'X-Auth-Token': dsttoken}
        import_job_check = s.get(import_dns_job_url, headers=import_job_headers)
        time.sleep(2)

        while str(import_job_check.json()['status']) == 'RUNNING':
            time.sleep(5)
            import_job_check = s.get(import_dns_job_url, headers=import_job_headers)

        if str(import_job_check.json()['status']) not in ('COMPLETED', 'RUNNING'):
            print "\nThere was a problem with the import job for domain ID : " + str(custom_dns_id)
            print "\nStatus: " + str(import_job_check.json()['status'])
            if str(import_job_check.json()['status']) == 'ERROR':
                print '\nError Message : ' + str(import_job_check.json()['error'])

        if str(import_job_check.json()['status']) == 'COMPLETED':
            print "\nImport Job Output: " + str(import_job_check.text)
            print "\nImport appears to have been successful for domain ID : " + str(custom_dns_id)

def dns_export_import(srcddi, srctoken, dstddi, dsttoken):
    id_list = []
    if dns_id_file:
        print "Domain ID file specified, gathering ID list...\n"
        if os.path.isfile(dns_id_file) == True:
            with open(dns_id_file) as file:
                content = [x.strip('\n') for x in file.readlines()]
                for dns_id in content:
                   id_list.append(dns_id)
            print "Script will run against the following IDs: \n"
            print id_list
        else:
            print "\nDNS ID file not found! Quitting..."
            quit()
    else:
        print "\nNo specific domain or DNS file provided, script will run against all domains on account"
        src_dns_endpoint = 'https://dns.api.rackspacecloud.com/v1.0/%s/domains' % srcddi
        dns_headers = {'X-Auth-Token': srctoken}
        dns_get = s.get(src_dns_endpoint, headers=dns_headers)
        dns_return = dns_get.text
        dns_domains = json.loads(dns_return)['domains']
        for domain in dns_domains:
            id_list.append(domain['id'])
    
    for dns_id in id_list:
        #Export the Domain
        export_dns_endpoint = 'https://dns.api.rackspacecloud.com/v1.0/%s/domains/%s/export' % (srcddi, dns_id)
        export_dns_headers = {'X-Auth-Token': srctoken}
        export_dns_get = s.get(export_dns_endpoint, headers=export_dns_headers)
        export_dns_joburlraw = export_dns_get.json()['callbackUrl']
        export_job_check = s.get(export_dns_joburlraw, headers=export_dns_headers)
        #Check Export Job
        while str(export_job_check.json()['status']) == 'RUNNING':
            time.sleep(5)
            export_job_check = s.get(export_dns_joburlraw, headers=export_dns_headers)
            
        if str(export_job_check.json()['status']) != 'COMPLETED':
            print "\nThere was a problem with the export job for domain ID : " + str(dns_id)
            print str(export_job_check.text)
            quit()
        
        #Now that the job is completed move on to importing the domain
        export_dns_joburl = str(export_dns_joburlraw) + '?showDetails=true'
        export_dns_bind9_request = s.get(export_dns_joburl, headers=export_dns_headers)
        export_dns_bind9_text = ''
        for line in export_dns_bind9_request.json()['response']['contents'].splitlines():
            if 'ipadmin.stabletransit.com.' in line:
                bind_line_list = line.split()
                export_dns_bind9_text += bind_line_list[0] + '\t\t' + bind_line_list[1] + '\tIN\tSOA\t' + 'ns.rackspace.com. ' + admin_email + ' ' + bind_line_list[6] + ' ' + bind_line_list[7] + ' ' + bind_line_list[8] + ' ' + bind_line_list[9] + ' ' + bind_line_list[10] + '\n'
            if 'dns1.stabletransit.com.' in line:
                continue
            if 'dns2.stabletransit.com.' in line:
                continue
            else:
                export_dns_bind9_text += line + '\n'
        export_dns_bind9_json = json.dumps(export_dns_bind9_text)
        if export_dns_bind9_text == "":
            print "\nNo records found for domain ID : " + str(dns_id)
            continue
        if import_option != True:
            print "\nImport option not used, printing Bind9 export below and continuing: \n"
            print export_dns_bind9_json
            time.sleep(1)
            continue
        #Only 10 deletes/min allowed by default so addding 6 second sleep
        time.sleep(6)
        dns_import_data = '{"domains" : [ {"contentType" : "BIND_9", "contents" : %s} ]}' % export_dns_bind9_json
        #Before we import this domain we need to remove it from the origin account
        print "\nPreparing to remove domain ID : " + str(dns_id) + " from source account"
        print "\nHere is the raw json formated Bind9 output if the import fails and has to be manually retried via the API:\n"
        print str(dns_import_data)
        remove_domain_url = 'https://dns.api.rackspacecloud.com/v1.0/%s/domains?id=%s' % (srcddi, dns_id)
        remove_domain_request = s.delete(remove_domain_url, headers=export_dns_headers)
        remove_domain_job = remove_domain_request.json()['callbackUrl']
        remove_domain_job_url = str(remove_domain_job) + '?showDetails=true'
        remove_domain_check = s.get(remove_domain_job_url, headers=export_dns_headers)
        while str(remove_domain_check.json()['status']) == 'RUNNING':
            time.sleep(5)
            remove_domain_check = s.get(remove_domain_job_url, headers=export_dns_headers)
    
        if str(remove_domain_check.json()['status']) != 'COMPLETED':
            print "\nThere was a problem with the delete job for domain ID : " + str(dns_id)
            print "\nStatus: " + str(remove_domain_check.json()['status'])
            if str(remove_domain_check.json()['status']) == 'ERROR':
                print '\nError Message : ' + str(remove_domain_check.json()['error'])
    
        if str(remove_domain_check.json()['status']) == 'COMPLETED':
            print "\nDomain removal successful, preparing to import domain to destination account"
            import_dns_endpoint = 'https://dns.api.rackspacecloud.com/v1.0/%s/domains/import' % dstddi
            import_dns_headers = {'X-Auth-Token': dsttoken, 'Accept': 'application/json', 'Content-Type': 'application/json'}
            import_dns_request = s.post(import_dns_endpoint, data=dns_import_data, headers=import_dns_headers)
            print "\nImport DNS response : " + str(import_dns_request.text)
            import_dns_job = import_dns_request.json()['callbackUrl']
            import_dns_job_url = str(import_dns_job) + '?showDetails=true'
            print "\nImport dns job URL : " + str(import_dns_job_url)
            import_job_headers = {'X-Auth-Token': dsttoken}
            import_job_check = s.get(import_dns_job_url, headers=import_job_headers)
            #Only 20 POSTs/min so adding 3 second sleep
            time.sleep(3)
            
            while str(import_job_check.json()['status']) == 'RUNNING':
                time.sleep(5)
                import_job_check = s.get(import_dns_job_url, headers=import_job_headers)
    
            if str(import_job_check.json()['status']) not in ('COMPLETED', 'RUNNING'):
                print "\nThere was a problem with the import job for domain ID : " + str(dns_id)
                print "\nStatus: " + str(import_job_check.json()['status'])
                if str(import_job_check.json()['status']) == 'ERROR':
                    print '\nError Message : ' + str(import_job_check.json()['error'])
    
            if str(import_job_check.json()['status']) == 'COMPLETED':
                print "\nImport Job Output: " + str(import_job_check.text)
                print "\nImport appears to have been successful for domain ID : " + str(dns_id)
        
        #prevent API call limit issues
        time.sleep(1)

parser = argparse.ArgumentParser()

parser.add_argument('--srcddi',
required=True,
default=None,
help='The account number or DDI for the source account')

parser.add_argument('--srcuser',
required=True,
default=None,
help='The user for the source account')

parser.add_argument('--srcapikey',
required=True,
default=None,
help='Source account apikey')

parser.add_argument('--dstddi',
required=False,
default=None,
help='The account number or DDI for the destination account')

parser.add_argument('--dstuser',
required=False,
default=None,
help='The user for the destination account')

parser.add_argument('--dstapikey',
required=False,
default=None,
help='Destination account apikey')

parser.add_argument('--domainid',
required=False,
default=None,
help='Choose a specific domain to export and import')

parser.add_argument('--importdomains',
action='store_true',
required=False,
default=None,
help='Option to import the domain(s) after exporting, will delete the source')

parser.add_argument('--dnsidfile',
required=False,
default=None,
help='A file containing DNS IDs that you want to export or transfer')

parser.add_argument('--email',
required=True,
default=None,
help='The administrative email address to be inserted to the SOA record if it has to be generated manually, must be formatted email.domain.com.')

args = parser.parse_args()

srcuser = args.srcuser
dstuser = args.dstuser

user = args.srcuser
api_key = args.srcapikey
srcddi = args.srcddi
srctoken_return = Auth(user,api_key)
srctoken = srctoken_return.auth_call()
custom_dns_id = args.domainid
import_option = args.importdomains
dns_id_file = args.dnsidfile
admin_email = args.email

if import_option != True:
    #don't set dst variables since they don't exist
    dstddi = srcddi
    dsttoken = srctoken
    
else:
    user = args.dstuser
    api_key = args.dstapikey
    dstddi = args.dstddi
    dsttoken_return = Auth(user,api_key)
    dsttoken = dsttoken_return.auth_call()

if __name__ == '__main__':
    if custom_dns_id:
        print "\n Single domain ID detected, running script for just this domain ID : " + str(custom_dns_id)
        dns_export_import_single(srcddi, srctoken, dstddi, dsttoken, custom_dns_id)
    else:
        dns_export_import(srcddi, srctoken, dstddi, dsttoken)
