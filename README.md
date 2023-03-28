# Hoster Scan #

Hoster Scan is a Web Crawler implemented in Python that crawls entire webpages of hosting companies and cloud service providers
including their sub pages to analyse which products or services they offer, promote or use.

Hoster Scan only follows valid and reasonable urls, so ignoring selected website parts like /blog or legal pages.
Product name variations are supported to find also websites that use different writings of a product or use it in a different language.

### Requirements ###

To run the Hoster Scan it is recommended to use a spare server and keep the process running (use "screen -r" to recover a session) since
depending on the input list of hosting companies and the crawl depth (number of subpages) it can take many hours to days to complete the
scan.

The environment has to support Python 3.6 or higher and the following Python module

    $ pip install argparse
    $ pip install bs4
    $ pip install prettytable

### How to run the scan? ###

To start the scan, make sure you have all hoster website urls in "input/hosters.csv" including the name and a hosterId of this hoster.

    $ ./check_hosting_products.py --help
    $ ./check_hosting_products.py --list-hosters
    $ ./check_hosting_products.py --list-products
    $ ./check_hosting_products.py --start-at 100 --stop-at 199 --max-depth 10

### Contribution guidelines ###

Feel free to help improving the Hoster Scan in everyway.

### Who do I talk to? ###

* Jan Loeffler, CTO at WebPros, jan.loeffler@webpros.com
