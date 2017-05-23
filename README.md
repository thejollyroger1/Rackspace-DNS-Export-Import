# Rackspace-DNS-Export-Import
Exports domains in bind9 format and can import in to another Rackspace Cloud account 
 
The DNS-Export-Import script will export (in bind9 format) a list of DNS IDs or a single ID if specified. Otherwise it will export all domains from the source cloud account specified. Has the option to import them in to another cloud account if specified as well.
 
Usage Example WITHOUT IMPORTING domains (will export in bind9 only, will not delete source):
 
python dns_export_import.py --srcddi \<source ddi\> --srcuser \<source user\> --srcapikey \<source api key\> --domainid \<your domain id\>
 
Usage Example SPECIFYING specific domain (will export, delete source, and import one domain specified):
 
python dns_export_import.py --dstddi \<destination ddi\> --dstuser \<destination user\> --dstapikey \<destination api key\> --srcddi \<source ddi\> --srcuser \<source user\> --srcapikey \<source api key\> --domainid \<your domain id\> --importdomains
 
Usage Example WITH FILE and import (will export, delete source, and import domains inside file):
 
python dns_export_import.py --dstddi \<destination ddi\> --dstuser \<destination user\> --dstapikey \<destination api key\> --srcddi \<source ddi\> --srcuser \<source user\> --srcapikey \<source api key\> --dnsidfile \</path/to/file\> --importdomains
 
Real Example WITHOUT FILE (will export, delete source, and import all domains):
 
python dns_export_import.py --dstddi 123456 --dstuser bob1 --dstapikey zcf0ec12d0df4deb9de9e00a47c5113c --srcddi 654321 --srcuser bob2 --srcapikey a755bbe91fbd4629995eeddb8b072d4z --importdomains
 
The format for the DNS ID file must follow this format
 
123456 <br />
456789 <br />
789456 <br />
