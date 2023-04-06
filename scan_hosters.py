#!/usr/bin/env python3
"""
Hoster Scan is a python script that researches which products or services are offered by cloud service providers / web hosting companies (aka hosters).
The crawler downloads all websites of hosters including sub pages up to a defined maximum and checks for pre-selected keywords.
The output is a list of hosting companies including the offered/used services/products and some statistics.
"""

import requests
import csv
import os
import operator
import argparse
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from prettytable import PrettyTable
from functions import *

# Define the argument parser
parser = argparse.ArgumentParser(description='Check for products in hosting websites.')
parser.add_argument('--max-depth', type=int, default=50, help='The maximum number of links to follow for each hoster. Default is 50.')
parser.add_argument('--max-hosters', type=int, default=5, help='The maximum number of hosters printed as example in result table. Default is 5.')
parser.add_argument('--start-at', type=int, default=0, help='Start at hoster with specified index. Default is 0.')
parser.add_argument('--stop-at', type=int, default=10000, help='Stop at hoster with specified index. Default is 10000.')
parser.add_argument('--reset', action='store_true', help='Delete previous data and start from scratch')
parser.add_argument('--full-scan', action='store_true', help='Crawl up to 100 pages of each website')

parser.add_argument('--hosters', nargs='?', default='', metavar='file', help='CSV file containing all urls that should be crawled with HosterName in 2nd column and HosterID in 3rd')
parser.add_argument('--products', nargs='?', default='', metavar='file', help='CSV file containing all products (1st column) followed by all their spelling variations')
parser.add_argument('--blocked-url-endings', nargs='?', default='', metavar='file', help='Text file containing url endings (one string per line) that should be blocked from crawling')

parser.add_argument('--debug', action='store_true', help='Print debug information')
parser.add_argument('--print-errors', action='store_true', help='Print error information')
parser.add_argument('--print-hosters', action='store_true', help='Print each current hoster name before crawling their website')

parser.add_argument('--list-products', action='store_true', help='Print all selected products and exit')
parser.add_argument('--list-hosters', action='store_true', help='Print all selected hosters and exit')
args = parser.parse_args()

# Define the input file paths
HOSTERS_CSV = 'input/hosters_to_be_crawled.csv'
PRODUCTS_CSV = 'input/products.csv'
BLOCKED_HOSTERS_TXT = 'input/blocked_hosters.txt'
BLOCKED_URL_ENDINGS_TXT = 'input/blocked_url_endings.txt'

# Define the output file paths
OUTPUT_CSV = 'output/products_mentioned_by_hosters.csv'
ERROR_LOG = 'output/crawling_errors.log'
PRODUCTS_TXT = 'output/products.txt'
KEYWORDS_TXT = 'output/keywords.txt'
HOSTERS_WITH_KEYWORDS_CSV = 'output/hosters_with_keywords.csv'
URLS_CRAWLED_WITH_KEYWORDS_CSV = 'output/urls_crawled_with_keywords.csv'
URLS_CRAWLED_TXT = 'output/urls_crawled.txt'
URLS_WITH_ERRORS_TXT = 'output/urls_with_errors.txt'
STATISTICS_TXT = 'output/statistics.txt'

# Number of links to crawl (default = 30)
num_links_to_crawl = args.max_depth
debug = args.debug
print_errors = debug or args.print_errors
print_hosters = debug or args.print_hosters
start_at = args.start_at
stop_at = args.stop_at
reset = args.reset
top_user_limit = args.max_hosters

if args.full_scan:
    num_links_to_crawl = 100

# Make sure the output folder exists
if not os.path.exists('output'):
    os.makedirs('output')

# Change import files if specified by command line parameter
if args.hosters and os.path.exists(args.hosters):
    HOSTERS_CSV = args.hosters

if args.products and os.path.exists(args.products):
    PRODUCTS_CSV = args.products

if args.blocked_url_endings and os.path.exists(args.blocked_url_endings):
    BLOCKED_URL_ENDINGS_TXT = args.blocked_url_endings

# Load list of blocked hoster urls from text file
if os.path.exists(BLOCKED_HOSTERS_TXT):
    with open(BLOCKED_HOSTERS_TXT, 'r') as file:
        BLOCKED_URLS = tuple([line.strip().rstrip('/').lower() for line in file if line.strip()])

# Load list of blocked url endings from text file
if os.path.exists(BLOCKED_URL_ENDINGS_TXT):
    with open(BLOCKED_URL_ENDINGS_TXT, 'r') as file:
        BLOCKED_URL_ENDINGS = tuple([line.strip().rstrip('/').lower() for line in file if line.strip()])

# Load list of hosting companies and their URLs from CSV file
# Exclude entries without a url and hosters that are on the block list
hosters = []
hoster_dict = {} # hoster_dict contains all hoster entries with the hoster id as key
urls_added = set()
with open(HOSTERS_CSV, 'r') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        hoster_url = row[0].strip().rstrip('/').lower()
        hoster_name = row[1].strip().replace(',','').replace('"','').replace('\'','')
        hoster_id = row[2].strip().lower()
        if hoster_url.startswith(URL_BEGINNING) \
            and hoster_url not in BLOCKED_URLS \
            and hoster_url not in urls_added:

            if not hoster_id:
                hoster_id = domain(hoster_url).replace('www.', '').replace('.', '')
            if not hoster_name:
                hoster_name = domain(hoster_url).replace('www.', '')

            hosters.append([hoster_url, hoster_name, hoster_id])
            hoster_dict[hoster_id] = hoster_name
            urls_added.add(hoster_url)

num_hosters = len(hosters)

# Print list of hosters if --list-hosters and exit
if args.list_hosters:
    for i, hoster in enumerate(hosters):
        if i >= start_at and i <= stop_at:
            print(hoster[1], '(' + domain(hoster[0]) + ')')

    print()
    print('{:>7,}'.format(num_hosters), 'hosters imported from', HOSTERS_CSV)
    exit()

# products is a string list containing only the official name of each product
products = []

# keywords is a string list containing all keywords to search
keywords = []

# product_to_variations_dict contains all official names as key and its variations as string list as value
product_to_variations_dict = {}

# keyword_to_product_dict is a mapping with each keyword as key and the related parent product as value
keyword_to_product_dict = {}

# Import list of products and their variations from csv file
with open(PRODUCTS_CSV, 'r') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        product = row[0].strip()
        if product and product not in products:
            products.append(product)
            variations = []
            for keyword in row:
                if keyword and keyword not in keywords:
                    keywords.append(keyword)
                    keyword_to_product_dict[keyword] = product
                    if keyword != product:
                        variations.append(keyword)
            product_to_variations_dict[product] = variations

# Generate products.txt and keywords.txt files
write_list_to_file(PRODUCTS_TXT, 'w', products)
write_list_to_file(KEYWORDS_TXT, 'w', keywords)

# Print list of products if --list-products and exit
if args.list_products:
    for i, product in enumerate(products):
        if i >= start_at and i <= stop_at:
            variations = product_to_variations_dict[product]
            if len(variations) == 0:
                print(product)
            else:
                print(product, '(' + ', '.join(variations).rstrip(', ') + ')')

    print()
    print('{:>7,}'.format(len(products)), 'products in', PRODUCTS_CSV)
    print('{:>7,}'.format(len(keywords)), 'search terms for those products in total')
    exit()

# Initialize dictionary and counters to store results
results = {}
urls_crawled = []
urls_with_errors = []
num_hosters_checked = 0
num_hosters_with_products = 0
num_hosters_with_products_last = 0
num_urls_crawled = 0
num_crawl_errors = 0

# Write CSV header to CSV file if it does not yet exist
if reset or not os.path.exists(OUTPUT_CSV):
    write_csv_to_file(OUTPUT_CSV, 'w', ['URL', 'Company Name', 'HosterID', 'Number of Matched Technologies'] + keywords)

    if reset:
        deletefiles((URLS_CRAWLED_TXT, URLS_WITH_ERRORS_TXT, ERROR_LOG, HOSTERS_WITH_KEYWORDS_CSV, URLS_CRAWLED_WITH_KEYWORDS_CSV))

# Import existing data set
else:
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

    # Import results from output csv
    with open(OUTPUT_CSV, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            hoster_url = row[0].strip().rstrip('/').lower()
            if hoster_url.startswith(URL_BEGINNING):
                hoster_name = row[1]
                hoster_id = row[2]
                num_matched = row[3]
                num_hosters_checked += 1

                if hoster_url not in urls_crawled:
                    urls_crawled.append(hoster_url)
                    num_urls_crawled +=1

                # Initialize list to store matches for this hoster
                matches = [0] * len(keywords)

                # Import existing results
                for j, keyword in enumerate(keywords):
                    if (j + 4) < len(row):
                        matches[j] = int(row[j + 4])

                # Add hoster to results dictionary
                results[hoster_id] = matches
                if sum(matches) > 0:
                    num_hosters_with_products += 1

# Function to sum up mentions for a product incl. its variations for specified matches
def check_matches(product: str, matches):
    mentions = 0
    variations = product_to_variations_dict[product]
    for i, keyword in enumerate(keywords):
        if keyword == product or keyword in variations and matches[i] > 0:
            mentions += matches[i]
    return mentions

# Function to get hosters sorted by their mentions of a product
def get_top_users(product: str, limit: int = 5):
    hosters_mentioning_it = {}
    for hoster_id, matches in results.items():
        mentions = check_matches(product, matches)
        if mentions > 0:
            hoster_name = hoster_dict[hoster_id]
            hosters_mentioning_it[hoster_name] = mentions

    top_hosters = dict(sorted(hosters_mentioning_it.items(), key=operator.itemgetter(1), reverse=True))
    top = []
    i = 0
    for hoster in top_hosters.keys():
        if i < limit:
            i += 1
            top.append(hoster)
        else:
            break

    return top

def print_statistics(to_shell=False):
    """Print statistics with summary table for keywords and products as well as metrics summary"""

    stats = []

    # --- print keyword summary table ---
    table = PrettyTable(field_names=['Keyword', 'Hosters', '%'])
    #table.field_names = ['Keyword', 'Hosters', '%']
    table.align['Keyword'] = 'l'
    table.align['Hosters'] = 'r'
    table.align['%'] = 'c'

    # Calculate how many hosters use each keyword and their percentage
    for i, keyword in enumerate(keywords):
        # Count number of hosters mentioning this keyword
        num_hosters_with_this_keyword = sum([1 for matches in results.values() if matches[i] > 0])

        # Only add a keyword to the table if there is at least one hoster mentioning it
        if num_hosters_with_this_keyword > 0:
            percentage = '{:.1%}'.format(num_hosters_with_this_keyword / num_hosters_with_products)
            table.add_row([keyword, num_hosters_with_this_keyword, percentage])

    # Sort and print table
    stats.append(table.get_string(sortby='Hosters', reversesort=True))
    stats.append('')

    # --- print product summary table ---
    table = PrettyTable(field_names=['Product', 'Hosters', '%', 'Examples'])
    #table.field_names = ['Product', 'Hosters', '%', 'Examples']
    table.align['Product'] = 'l'
    table.align['Hosters'] = 'r'
    table.align['%'] = 'c'
    table.align['Examples'] = 'l'

    # Calculate how many hosters use each product and their percentage
    for product in products:
        # Count number of hosters mentioning this product
        num_hosters_with_this_product = sum([1 for matches in results.values() if check_matches(product, matches) > 0])
        top_hosters_with_this_product = get_top_users(product, top_user_limit)

        # Only add a product to the table if there is at least one hoster mentioning it
        if num_hosters_with_this_product > 0:
            percentage = '{:.1%}'.format(num_hosters_with_this_product / num_hosters_with_products)
            table.add_row([product, num_hosters_with_this_product, percentage, ', '.join(top_hosters_with_this_product).rstrip(', ')])

    # Sort and print table
    stats.append(table.get_string(sortby='Hosters', reversesort=True))
    stats.append('')

    # Calculate percentage values
    if num_hosters > 0 and num_hosters_checked > 0 and num_hosters_with_products > 0:
        perc_hosters_checked = '{:.1%}'.format(num_hosters_checked / num_hosters)
        perc_hosters_with_products = '{:.1%}'.format(num_hosters_with_products / num_hosters_checked)
    else:
        perc_hosters_checked = '0.0%'
        perc_hosters_with_products = '0.0%'

    if num_urls_crawled > 0 and num_crawl_errors > 0:
        perc_crawl_errors = '{:.1%}'.format(num_crawl_errors / num_urls_crawled)
    else:
        perc_crawl_errors = '0.0%'

    # Print general statistics
    stats.append('{:>7,}'.format(len(products)) + ' products in ' + PRODUCTS_CSV)
    stats.append('{:>7,}'.format(len(keywords)) + ' search terms for those products in total')
    stats.append('')
    stats.append('{:>7,}'.format(num_hosters) + ' hosters imported from ' + HOSTERS_CSV)
    stats.append('{:>7,}'.format(num_hosters_checked) + ' hosters checked (' + perc_hosters_checked + ')')
    stats.append('{:>7,}'.format(num_hosters_with_products) + ' hosters mentioning at least one of the products (' + perc_hosters_with_products + ') saved to ' + OUTPUT_CSV)
    stats.append('')
    stats.append('{:>7,}'.format(num_urls_crawled) + ' URLs crawled saved to ' + URLS_CRAWLED_TXT)
    stats.append('{:>7,}'.format(num_crawl_errors) + ' URLs skipped due to crawling errors (' + perc_crawl_errors + ') saved to ' + URLS_WITH_ERRORS_TXT)

    write_list_to_file(STATISTICS_TXT, 'w', stats)

    if to_shell:
        for line in stats:
            print(line)

# Start crawling by looping over all hosting companies and downloading eaach website
for i, hoster in enumerate(hosters):
    hoster_url = unifyurl(hoster[0])

    # only crawl if hoster is within specified index range, is a real url and was not yet crawled or blocked
    if i >= start_at and i <= stop_at \
        and hoster_url.startswith(URL_BEGINNING) \
        and hoster_url not in urls_crawled \
        and hoster_url not in BLOCKED_URLS:

        hoster_name = hoster[1]
        hoster_id = hoster[2]
        parsed_hoster_url = urlparse(hoster_url).netloc
        queue = [hoster_url]
        urls_crawled_new = []
        urls_crawled_new_with_keywords = []
        urls_with_errors_new = []
        keywords_for_this_hoster = set()
        visited = set()
        num_hosters_checked += 1

        # Initialize list to store matches for this hoster
        matches = [0] * len(keywords)

        if debug or print_hosters:
            print(hoster_name, '(' + hoster_url + ')')

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
                        print(f'Error downloading page {url} from {hoster_name}: {e}')
                    urls_with_errors.append(url)
                    urls_with_errors_new.append(url)
                    num_crawl_errors += 1

                    # document error in error log file
                    with open(ERROR_LOG, 'a+') as error_file:
                        error_file.write(f"Error downloading page {url} from {hoster_name}: {e}\n")

                    continue

                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # document that we crawled this url already
                urls_crawled.append(url)
                urls_crawled_new.append(url)
                num_urls_crawled += 1

                # also document if the response url is different than the initial one due to redirects
                response_url = unifyurl(response.url)
                if (parsed_hoster_url not in response_url) and (response_url not in urls_crawled):
                    urls_crawled.append(response_url)
                    urls_crawled_new.append(response_url)
                    num_urls_crawled += 1

                # Search for matches in page text
                keywords_for_this_url = set()
                text = soup.get_text().lower()
                for j, keyword in enumerate(keywords):
                    if keyword.lower() in text:
                        matches[j] += 1
                        if keyword not in keywords_for_this_url:
                            keywords_for_this_url.add(keyword)
                        if debug:
                            print('      ', keyword, 'at', hoster_name, '(' + response_url + ')')

                # document keywords for specific url
                if len(keywords_for_this_url) > 0:
                    for keyword in keywords_for_this_url:
                        if keyword not in keywords_for_this_hoster:
                            keywords_for_this_hoster.add(keyword)
                    urls_crawled_new_with_keywords.append(response_url + ',' + hoster_name + ',' + ','.join(keywords_for_this_url).rstrip(','))

                # Add links to the queue for further crawling
                for link in soup.find_all('a'):
                    link_url = link.get('href')
                    # Only crawl subpage if it belongs to the hosters website and was not yet crawled
                    # only accept links starting with http(s):// and not ending with a media file extension
                    # remove the trailing slash for consistency and prevent duplicate crawls
                    # don't crawl blog articles since they don't really matter for this topic
                    if link_url is not None:
                        # take lower case url and remove everything after '?' or '#' as well as trailing '/'
                        link_url = unifyurl(link_url)
                        if link_url.startswith(URL_BEGINNING) \
                            and link_url.startswith((hoster_url, response_url)) \
                            and (not link_url.endswith(BLOCKED_URL_ENDINGS)) \
                            and (not any(substring in link_url for substring in BLOCKED_URL_SUBSTRINGS)) \
                            and link_url not in visited \
                            and link_url not in queue:
                            queue.append(link_url)

        # Add hoster to results dictionary
        results[hoster_id] = matches
        if sum(matches) > 0:
            num_hosters_with_products += 1

        # Append values to output CSV file with matrix
        write_csv_to_file(OUTPUT_CSV, 'a+', [hoster_url, hoster_name, hoster_id, sum(matches)] + matches)

        # Append all crawled urls to the crawler log file
        write_list_to_file(URLS_CRAWLED_TXT, 'a+', urls_crawled_new)

        # Append all urls with errors to the error log file
        write_list_to_file(URLS_WITH_ERRORS_TXT, 'a+', urls_with_errors_new)

        # if at least one keyword was found for this hoster
        if len(keywords_for_this_hoster) > 0:
            # Append hoster with list of keywords to CSV file
            write_csv_to_file(HOSTERS_WITH_KEYWORDS_CSV, 'a+', [hoster_url, hoster_name, hoster_id] + list(keywords_for_this_hoster))

            # Append all crawled urls including the found keywords to a csv file
            write_list_to_file(URLS_CRAWLED_WITH_KEYWORDS_CSV, 'a+', urls_crawled_new_with_keywords)

            # only print statistics after each 10 crawled hosters that mentioned at least one keyword
            if num_hosters_with_products >= (num_hosters_with_products_last + 10):
                num_hosters_with_products_last = num_hosters_with_products
                print_statistics()

# --- end of crawling ---

print_statistics(True)
