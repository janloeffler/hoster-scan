#!/usr/bin/env python3

"""
Functions
"""

import os
import csv

HTML_HEADER = { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36' }
HTTP_GET_TIMEOUT = 30 # max seconds before GET request timeout
URL_BEGINNING = ( 'https://', 'http://' )
BLOCKED_URL_ENDINGS = ( '.exe', '.zip', '.pdf', '.jpg', '.jpeg', '.png', '.ico', '.mp3', '.avi', '.mov', '.mp4', \
                        '.mpg', '.mpeg', '.xlsx', '.pptx', '.docx', '.doc' \
                        '/about', '/about-us', '/agb', '/api', '/blog', '/careers', '/cart.php','/company', '/contact', \
                        '/contact-us', '/cookies', '/datenschutz', '/docs', '/events', '/facebook', '/help', '/hilfe', \
                        '/history', '/impressum', '/instagram', '/kb', '/kontakt', '/jobs', '/legal', '/linkedin', \
                        '/login', '/our-team', '/privacy', '/privacy-policy', '/recruitment', '/team', '/terms', \
                        '/terms-conditions', '/terms-of-service', '/twitter', '/ueber-uns', '/unternehmen', \
                        '/warenkorb', '/wiki', '/wp-admin' )
BLOCKED_URL_SUBSTRINGS = ( '/blog', '/wp-admin', 'instagram', 'twitter', 'facebook', 'linkedin' )
BLOCKED_URLS = ('https://www.akamai.com', 'https://www.cloudflare.com', 'https://cpanel.net', 'https://plesk.com')

def unifyurl(url: str):
    """Return url in unifyied form: lowercase, without parameters, anchors or trailing slash"""
    return url.strip().split('?')[0].split('#')[0].rstrip('/').lower()

def baseurl(url: str):
    """Return domain name only for specified url including protocol but without trailing slash"""
    url = url.strip().lower()
    if url.startswith('https://'):
        return 'https://' + url.replace('https://', '').split('/')[0]
    elif url.startswith('http://'):
        return 'http://' + url.replace('http://', '').split('/')[0]
    else:
        return ''

def domain(url: str):
    """Return domain name only for specified url without protocol or trailing slash"""
    return url.strip().lower().replace('https://', '').replace('http://', '').split('/')[0]

def deletefiles(filenames):
    """Delete each specified file if it exists"""
    for filename in filenames:
        if os.path.exists(filename):
            os.remove(filename)

def write_list_to_file(filename: str, mode: str, list):
    """Write list with strings to file"""
    with open(filename, mode) as file:
        for string in list:
            file.write(f"{string}\n")

def write_csv_to_file(filename: str, mode: str, row):
    """Write list with strings to file"""
    with open(filename, mode, newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(row)
