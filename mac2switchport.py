#!/usr/bin/env python3

###
### mac2switchport.py
### Bryan Ward, Dartmouth College
### bward@dartmouth.edu
###
### 2021-01-24 - Functional Release
### 2021-11-29 - Removed Debugging Code and added Usage information
###
###
### Requirements
###     Environment Variables
###         AKIPS_URL               URL of the AKIPS server, ex: "https://akips.example.edu"
###         AKIPS_API_RO_PASSWORD   Password for the Read-Only user of the AKIPS API
###     Files
###         ./akips.pem             Contains the certificate chain for the AKIPS HTTPS server
###                                 Example:
###
###                                     -----BEGIN CERTIFICATE-----
###                                     MIIHA...
###                                     -----END CERTIFICATE-----
###                                     -----BEGIN CERTIFICATE-----
###                                     MIIEs...
###                                     -----END CERTIFICATE-----
###                                     -----BEGIN CERTIFICATE-----
###                                     MIIDx...
###                                     -----END CERTIFICATE-----
###                                 You can get this file by going to the AKIPS GUI in Firefox, viewing the certificate details, and clicking the "PEM (chain)" link in the Miscellaneous section
###     Python Libraries:
###         requests
###         certifi
###
### Usage:
###     Specify MAC address via argument
###         ./mac2switchport.py --mac aa:bb:cc:dd:ee:ff
###         {"mac": "aa:bb:cc:dd:ee:ff", "vendor": "OUI-Vendor-Name", "switch": "switch-name", "port": "Gi0/23", "vlan": "vlan-name", "ipaddress": "10.1.2.3"}
###
###     Specify MAC address via STDIN
###         echo aa:bb:cc:dd:ee:ff | ./mac2switchport.py
###         {"mac": "aa:bb:cc:dd:ee:ff", "vendor": "OUI-Vendor-Name", "switch": "switch-name", "port": "Gi0/23", "vlan": "vlan-name", "ipaddress": "10.1.2.3"}
###
###     Specify MAC address in JSON via STDIN
###         echo '{"mac": "aa:bb:cc:dd:ee:ff"}' | ./mac2switchport.py
###         {'mac': 'aa:bb:cc:dd:ee:ff', 'vendor': 'OUI-Vendor-Name', 'switch': 'switch-name', 'port': 'Gi0/23', 'vlan': 'vlan-name', 'ipaddress': '10.1.2.3'}
###
###     This script returns JSON as output by default.  If the MAC address cannot be located by AKIPS, the script returns an empty list [].
###     If you wish to have the output in CSV format, use the --raw option
###         ./mac2switchport.py --mac aa:bb:cc:dd:ee:ff
###         "aa:bb:cc:dd:ee:ff,OUI-Vendor-Name,switch-name,Gi0/23,vlan-name,10.1.2.3\n"
###     If the MAC address cannot be located by AKIPS and the --raw option is used, the script returns the error message as provided by the AKIPS API.
###         "Can't resolve mac address f8:66:f2:1d:39:f5\n"
###

import os
import sys
import time
import json
import re
import certifi
import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not os.environ.get("AKIPS_URL"):
    raise Exception("AKIPS_URL environment variable is not set!")
else:
    AKIPS_URL = os.environ.get("AKIPS_URL")

if not os.environ.get("AKIPS_API_RO_PASSWORD"):
    raise Exception("AKIPS_API_RO_PASSWORD environment variable is not set!")
else:
    AKIPS_API_RO_PASSWORD = os.environ.get("AKIPS_API_RO_PASSWORD")


def format_mac(mac: str) -> str:
    mac = re.sub('[.:-]', '', mac).lower()  # remove delimiters and convert to lower case
    mac = ''.join(mac.split())  # remove whitespaces
    assert len(mac) == 12  # length should be now exactly 12 (eg. aabbccddeeff)
    assert mac.isalnum()  # should only contain letters and numbers
    # convert mac in canonical form (eg. aa:bb:cc:dd:ee:ff)
    mac = ":".join(["%s" % (mac[i:i+2]) for i in range(0, 12, 2)])
    return mac


def mac2switchport(mac, raw=False):
    logger.debug("mac2switchport entry")
    #assert len(format_mac(mac)) == 17, "MAC Address must be 17 characters"
    r = requests.get(AKIPS_URL + "/api-spm?username=api-ro;password=" + AKIPS_API_RO_PASSWORD + ";mac=" + format_mac(mac), verify="akips.pem")
    logger.debug(r)
    if raw:
        return r.text
    else:
        retval = []
        for j in r.text.split('\n'):
            i = j.split(',')
            if len(i) == 6:
                retval.append({"mac": format_mac(i[0]), "vendor": i[1], "switch": i[2], "port": i[3], "vlan": i[4], "ipaddress": i[5]})
        return retval[0] if len(retval) == 1 else retval


def main():
    ''' Main Function when called directly from CLI '''
    if len(sys.argv) == 1:
        stdin = sys.stdin.read()
        try:
            #Was JSON passed in?
            for line in stdin.split('\n'):
                if len(line) == 0:
                    continue
                json_in = json.loads(line)
                logger.debug(json_in)
                if type(json_in) is dict:
                    print(mac2switchport(json_in['mac'], False))
                    sys.stdout.flush()
                elif type(json_in) is list:
                    retval = []
                    for ele in json_in:
                        retval.append(mac2switchport(ele['mac'], False))
                    print(json.dumps(retval))
                    sys.stdout.flush()
        except json.decoder.JSONDecodeError:
            logger.debug("STDIN is not JSON")
            #Something was passed in, but it's not JSON... Let's assume it's a MAC address (or a \n separated list of MAC addresses)
            try:
                for line in stdin.split('\n'):
                    if len(line) == 0:
                        continue
                    #ToDo: Make this return a json list [] by saving results to retval and then outputting that.
                    print(json.dumps(mac2switchport(line, False)))
                    sys.stdout.flush()
            except BrokenPipeError:
                pass
            except:
                raise
        except:
            raise

    else:
        import argparse
        parser = argparse.ArgumentParser(description='Fetch switchports where AKIPS has seen this MAC Address')
        parser.add_argument("--mac", help="The MAC Address you'd like to query.  No punctuation, case-insensitive.", type=str, required=True)
        parser.add_argument("--raw", help="Output raw results from API", action="store_true")
        parser.add_argument("--debug", help="Run and show debugging information", action="store_true")
        args = parser.parse_args()

        if (args.debug):
            logger.setLevel(logging.DEBUG)
        logger.debug("Loaded")

        print(json.dumps(mac2switchport(args.mac, args.raw)))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
