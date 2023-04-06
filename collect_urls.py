#!/usr/bin/env python3
"""
The Collect Urls script allows to crawl Listing websites linking to many hosting companies. The script
collects all those urls and unifys them in style + deduplicates them. The result list can be exported
to be used as hosters.csv for scan_hosters.py.
"""

import requests
import csv
import os
import argparse
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from functions import *

# Define the argument parser
parser = argparse.ArgumentParser(description='Collect urls from listing sites and merge them into Hoster CSV file.')
parser.add_argument('--max-depth', type=int, default=500, help='The maximum number of links to follow for each listing site. Default is 50.')
parser.add_argument('--reset', action='store_true', help='Delete previous data and start from scratch')

parser.add_argument('--import-urls', nargs='?', default='', metavar='file', help='Text file containing urls (one url per line) that should be imported as well')
parser.add_argument('--listing-sites', nargs='?', default='', metavar='file', help='Text file containing all listing sites that should be crawled')
parser.add_argument('--blocked-url-endings', nargs='?', default='', metavar='file', help='Text file containing url endings (one string per line) that should be blocked from crawling')

parser.add_argument('--debug', action='store_true', help='Print debug information')
parser.add_argument('--print-errors', action='store_true', help='Print error information')
parser.add_argument('--print-sites', action='store_true', help='Print each current listing site name before crawling their index website')

parser.add_argument('--list-sites', action='store_true', help='Print all selected listing sites and exit')
args = parser.parse_args()

# Define the input file paths
LISTING_SITES_TXT = 'input/listing_sites.txt'
BLOCKED_URL_ENDINGS_TXT = 'input/blocked_url_endings.txt'

# Define the output file paths
ERROR_LOG = 'output/crawling_errors.log'
URLS_CRAWLED_TXT = 'output/listing_site_urls_crawled.txt'
URLS_WITH_ERRORS_TXT = 'output/listing_site_urls_with_errors.txt'
URLS_FOUND_TXT = 'output/possible_hoster_urls_found.txt'

# Number of links to crawl (default = 30)
num_links_to_crawl = args.max_depth
debug = args.debug
print_errors = debug or args.print_errors
print_sites = debug or args.print_sites
reset = args.reset

# List of listing website that should be crawled
listing_sites = []
urls_crawled = []
urls_with_errors = []
possible_hoster_urls = []
num_listing_sites_checked = 0
num_urls_crawled = 0
num_crawl_errors = 0
num_possible_hoster_urls_found = 0

# Make sure the output folder exists
if not os.path.exists('output'):
    os.makedirs('output')

if reset:
    deletefiles((URLS_CRAWLED_TXT, URLS_WITH_ERRORS_TXT, URLS_FOUND_TXT, ERROR_LOG))

# Change import files if specified by command line parameter
if args.listing_sites and os.path.exists(args.listing_sites):
    LISTING_SITES_TXT = args.listing_sites

if args.blocked_url_endings and os.path.exists(args.blocked_url_endings):
    BLOCKED_URL_ENDINGS_TXT = args.blocked_url_endings

# Load list of blocked url endings from text file
if os.path.exists(BLOCKED_URL_ENDINGS_TXT):
    with open(BLOCKED_URL_ENDINGS_TXT, 'r') as file:
        BLOCKED_URL_ENDINGS = tuple([line.strip().rstrip('/').lower() for line in file if line.strip()])

# Load list of listing sites from text file
if os.path.exists(LISTING_SITES_TXT):
    with open(LISTING_SITES_TXT, 'r') as file:
        listing_sites = [line.strip().rstrip('/').lower() for line in file if line.strip()]

# Print list of listing sites if --list-sites and exit
if args.list_sites:
    for listing_site_url in listing_sites:
        print(domain(listing_site_url), '(' + listing_site_url + ')')

    print()
    print('{:>7,}'.format(len(listing_sites)), 'listing sites imported from', LISTING_SITES_TXT)
    exit()

# Import crawled urls
if os.path.exists(URLS_CRAWLED_TXT):
    with open(URLS_CRAWLED_TXT, 'r') as urls_crawled_file:
        urls_crawled = urls_crawled_file.readlines()
        num_urls_crawled = len(urls_crawled)

# Import urls with errors
if os.path.exists(URLS_WITH_ERRORS_TXT):
    with open(URLS_WITH_ERRORS_TXT, 'r') as urls_with_errors_file:
        urls_with_errors = urls_with_errors_file.readlines()
        num_crawl_errors = len(urls_with_errors)

# Import urls with errors
if os.path.exists(URLS_FOUND_TXT):
    with open(URLS_FOUND_TXT, 'r') as urls_found_file:
        possible_hoster_urls = urls_found_file.readlines()
        num_possible_hoster_urls_found = len(possible_hoster_urls)

# Import list of hoster urls if specified
if args.import_urls and os.path.exists(args.import_urls):
    with open(args.import_urls, 'r') as import_urls_file:
        for line in import_urls_file.readlines():
            hoster_url = unifyurl(line)
            if hoster_url.startswith(URL_BEGINNING) and hoster_url not in possible_hoster_urls:
               possible_hoster_urls.append(hoster_url)

# Start crawling by looping over all hosting companies and downloading eaach website
for listing_site_url in listing_sites:

    # only crawl if hoster is within specified index range, is a real url and was not yet crawled or blocked
    if listing_site_url.startswith(URL_BEGINNING) and listing_site_url not in urls_crawled:
        parsed_listing_site_url = urlparse(listing_site_url).netloc
        listing_site_base_url = baseurl(listing_site_url)
        queue = [listing_site_url]
        urls_crawled_new = []
        urls_with_errors_new = []
        possible_hoster_urls_new = []
        visited = set()
        num_listing_sites_checked += 1

        if debug or print_sites:
            print(listing_site_url)

        # Loop over all pages of this website to crawl
        while queue and len(visited) < num_links_to_crawl:
            url = queue.pop(0)
            if url not in visited:
                visited.add(url)

                if debug:
                    print('      ', url)

                # Download page HTML
                try:
                    response = requests.get(url, allow_redirects = True, stream = False, timeout = HTTP_GET_TIMEOUT, headers = HTML_HEADER)
                except requests.exceptions.RequestException as e:
                    if print_errors:
                        print(f'Error downloading page {url} from {listing_site_url}: {e}')
                    urls_with_errors.append(url)
                    urls_with_errors_new.append(url)
                    num_crawl_errors += 1

                    # document error in error log file
                    with open(ERROR_LOG, 'a+') as error_file:
                        error_file.write(f"Error downloading page {url} from {listing_site_url}: {e}\n")

                    continue

                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # document that we crawled this url already
                urls_crawled.append(url)
                urls_crawled_new.append(url)
                num_urls_crawled += 1

                # also document if the response url is different than the initial one due to redirects
                response_url = unifyurl(response.url)
                response_base_url = baseurl(response_url)
                if (parsed_listing_site_url not in response_url) and (response_url not in urls_crawled):
                    urls_crawled.append(response_url)
                    urls_crawled_new.append(response_url)
                    num_urls_crawled += 1

                # Find possible hoster links and add links from same domain to the queue for further crawling
                for link in soup.find_all('a'):
                    link_url = link.get('href')
                    # Only crawl subpage if it belongs to the listing website and was not yet crawled
                    # only accept links starting with http(s):// and not ending with a media file extension
                    # remove the trailing slash for consistency and prevent duplicate crawls
                    # don't crawl blog articles since they don't really matter for this topic
                    if link_url is not None:
                        # take lower case url and remove trailing '/'
                        link_url = link_url.strip().rstrip('/').lower()
                        link_base_url = baseurl(link_url)
                        link_domain = domain(link_base_url)
                        if link_url.startswith(URL_BEGINNING) \
                            and (not link_url.endswith(BLOCKED_URL_ENDINGS)) \
                            and (not any(substring in link_url for substring in BLOCKED_URL_SUBSTRINGS)) \
                            and link_url not in visited \
                            and link_url not in queue:

                            # if url is from the same listing site, add to queue for crawling
                            if link_url.startswith((listing_site_base_url, response_base_url)):
                                queue.append(link_url)

                            # else add url as possible hoster url to result list if not already included
                            elif link_base_url not in possible_hoster_urls \
                                and (not any(link_domain in start_url for start_url in listing_sites)):
                                possible_hoster_urls.append(link_base_url)
                                possible_hoster_urls_new.append(link_base_url)
                                num_possible_hoster_urls_found += 1

        # Append all crawled urls to the crawler log file
        with open(URLS_CRAWLED_TXT, 'a+') as urls_crawled_file:
            for url in urls_crawled_new:
                urls_crawled_file.write(f"{url}\n")

        # Append all urls with errors to the error log file
        with open(URLS_WITH_ERRORS_TXT, 'a+') as urls_with_errors_file:
            for url in urls_with_errors_new:
                urls_with_errors_file.write(f"{url}\n")

        if len(possible_hoster_urls_new) > 0:
            # Append all found possible hoster urls to output text file
            with open(URLS_FOUND_TXT, 'a+') as urls_found_file:
                for url in possible_hoster_urls_new:
                    urls_found_file.write(f"{url}\n")

# --- end of crawling ---

if num_urls_crawled > 0 and num_crawl_errors > 0:
    perc_crawl_errors = '{:.1%}'.format(num_crawl_errors / num_urls_crawled)
else:
    perc_crawl_errors = '0.0%'

# Print general statistics
print('{:>7,}'.format(num_listing_sites_checked), 'listing sites crawled from', LISTING_SITES_TXT)
print('{:>7,}'.format(num_urls_crawled), 'URLs crawled and saved to', URLS_CRAWLED_TXT)
print('{:>7,}'.format(num_crawl_errors), 'URLs skipped (' + perc_crawl_errors + ') due to crawling errors and saved to', URLS_WITH_ERRORS_TXT)
print('{:>7,}'.format(num_possible_hoster_urls_found), 'possible Hoster URLs found and saved to', URLS_FOUND_TXT)
