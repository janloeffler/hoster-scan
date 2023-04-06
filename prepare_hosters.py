#!/usr/bin/env python3
"""
Import and merge all known urls and prepare the hosters.csv input file as source for the
scan_hosters.py script.
"""

import csv
import os
import argparse
import validators
from functions import *

# Define the input file paths
HOSTERS_CSV = 'input/hosters.csv'
CPANEL_HOSTERS_CSV = 'input/cpanel_hosters.csv'
SALESFORCE_ACCOUNTS_CSV = 'input/salesforce_accounts.csv'
WHMCS_USERS_CSV = 'input/whmcs_users.csv'
URLS_TXT = 'input/url.txt'
URLS_FOUND_TXT = 'output/possible_hoster_urls_found.txt'
URLS_CRAWLED_TXT = 'output/urls_crawled.txt'

# Define the output file paths
OUTPUT_CSV = 'input/hosters_to_be_crawled.csv'

# Store all urls as key and [CompanyName, HosterId] as value if specified
output_dict = {}

num_urls_imported = 0
num_urls_with_company_imported = 0
num_urls_final = 0
num_urls_with_company_final = 0

companies = set()
hoster_ids = set()

# Loop over all known files that contain urls to be crawled
for file in (HOSTERS_CSV, CPANEL_HOSTERS_CSV, SALESFORCE_ACCOUNTS_CSV, URLS_TXT, URLS_FOUND_TXT, URLS_CRAWLED_TXT, WHMCS_USERS_CSV):
    if os.path.exists(file):
        print('Import urls from', file)

        # Import and merge CSV files
        if file.lower().endswith('.csv'):
            with open(file, 'r') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row and len(row) > 0:
                        if file.endswith('input/hosters.csv'):
                            url = unifyurl(row[2])
                            hoster_name = row[1].strip()
                            hoster_id = row[0].strip()
                        else:
                            url = unifyurl(row[0])
                            hoster_name = row[1].strip() if len(row) > 1 else ''
                            hoster_id = ''

                        if url and validators.url(url):
                            num_urls_imported += 1
                            if hoster_name == '-':
                                hoster_name = ''

                            if hoster_name:
                                num_urls_with_company_imported += 1

                            d = domain(url)
                            if d not in output_dict:

                                # use the base url without subfolders except the url contains '/en' for english
                                if '/' in url and not '/en' in url:
                                    url = baseurl(url)

                                output_dict[d] = [url, hoster_name, hoster_id]
                                num_urls_final += 1
                                if hoster_name:
                                    num_urls_with_company_final += 1
                                if hoster_name and hoster_name not in companies:
                                    companies.add(hoster_name)
                                if hoster_id and hoster_id not in hoster_ids:
                                    hoster_ids.add(hoster_id)

        # Import and merge text files containing only one url per line
        else:
            with open(file, 'r') as url_file:
                for url in url_file.readlines():
                    url = unifyurl(url)
                    if url and validators.url(url):
                        num_urls_imported += 1
                        d = domain(url)
                        if d not in output_dict:

                            # use the base url without subfolders except the url contains '/en' for english
                            if '/' in url and not '/en' in url:
                                url = baseurl(url)

                            output_dict[d] = [url, '', '']
                            num_urls_final += 1

# Write to output CSV
with open(OUTPUT_CSV, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['URL', 'CompanyName', 'HosterID'])
    for url, data in output_dict.items():
        writer.writerow([data[0], data[1], data[2]])

print('{:>7,}'.format(num_urls_imported), 'urls imported in total')
print('{:>7,}'.format(num_urls_with_company_imported), 'urls imported mentioned a company name')
print()
print('{:>7,}'.format(len(output_dict.keys())), 'urls exported in total')
print('{:>7,}'.format(num_urls_with_company_final), 'urls exported mentioned a company name')
print('{:>7,}'.format(len(companies)), 'companies exported in total')
print('{:>7,}'.format(len(hoster_ids)), 'companies exported having a hosterID in total')
