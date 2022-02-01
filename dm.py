import csv
import json
import logging
import math
import os
import string
import sys
import urllib
from datetime import datetime

# [pip3 install requests], if not already installed
import requests


def main():
    with open(d + '/dm.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=';')
        # write csv header
        csv_writer.writerow(['id', 'brand', 'name', 'price', 'link', 'image'])
        api_base_url = 'https://product-search.services.dmtech.com/de/search/?pageSize=1000&sort=new&brandName='
        # look for brands
        s_brands = get_brand_names_from_search_api(csv_writer)
        w_brands = get_brand_names_from_brands_page()
        a_brands = get_brands_from_alphanumerical_search(csv_writer)
        # combine brand lists and remove duplicates
        brands = combine_brand_lists(s_brands, w_brands, a_brands)
        logging.info('found ' + str(global_product_counter) +
                     ' products so far...')
        logging.info('finding more products through brand names...')
        # look for products of a band
        for brand in brands:
            search_url = api_base_url + brand
            json_file = json.loads(requests.get(search_url).text)
            total_pages = json_file['totalPages']
            # if there are more than 1000 products of one brand load next page
            for page in range(0, total_pages):
                # this check prevents unnecessary http requests in case that there is only one page
                if total_pages != 1:
                    json_file = json.loads(requests.get(
                        search_url + '&currentPage=' + str(page)).text)
                # products of a brand
                products_json = json_file['products']
                write_line_to_csv(csv_writer, products_json, False)
            # statistical purpose only
            if json_file['count'] == 0:
                brands_without_products.append(
                    urllib.parse.unquote_plus(str(brand)))
        # find alt names of brands
        find_alt_brand_names(csv_writer)


def get_brand_names_from_brands_page():
    """Return brand names form the brands page: https://www.dm.de/marken"""
    brands = []
    alphabet = list(string.ascii_uppercase)
    reference_list = ['0-9'] + alphabet
    page = json.loads(requests.get(
        "https://content.services.dmtech.com/rootpage-dm-shop-de-de/marken?json").text)
    for dict in page['mainData']:
        try:
            if dict['data']['text']['childNodes'][0]['childNodes'][0] in reference_list:
                node_list = dict['data']['text']['childNodes'][1]
                for entry in node_list['childNodes']:
                    brand = entry['childNodes'][0]['childNodes'][0]
                    brands.append(urllib.parse.quote_plus(str(brand)))
        except KeyError:
            pass
    logging.info('found ' + str(len(brands)) + ' brands on the brands webpage')
    return brands


def get_brand_names_from_search_api(csv_writer):
    """Return brand names form the search api: https://product-search.services.dmtech.com/de/search/"""
    brands = []
    for i in range(0, 4):
        if i == 0:
            page = json.loads(requests.get(
                'https://product-search.services.dmtech.com/de/search/?pageSize=1000').text)
        elif i == 1:
            page = json.loads(requests.get(
                'https://product-search.services.dmtech.com/de/search/?sort=new&pageSize=1000').text)
        elif i == 2:
            page = json.loads(requests.get(
                'https://product-search.services.dmtech.com/de/search/?sort=price_asc&pageSize=1000').text)
        elif i == 3:
            page = json.loads(requests.get(
                'https://product-search.services.dmtech.com/de/search/?sort=price_desc&pageSize=1000').text)
        for element in page['products']:
            brand = element['brandName']
            brands.append(urllib.parse.quote_plus(str(brand)))
        write_line_to_csv(csv_writer, page['products'], True)
    brands = list(set(brands))
    logging.info('found ' + str(len(brands)) + ' brands in the search api')
    return brands


def combine_brand_lists(list_a, list_b, list_c):
    """Return list of brands from both the brands page and the search api"""
    joinedlist = list_a + list_b + list_c
    brands = list(set(joinedlist))
    brands.sort()
    logging.info("-> total no. of unique brands found: " + str(len(brands)))
    return brands


def write_line_to_csv(csv_writer, products_json, alt_search):
    """Write products to a csv file for each brand"""
    global global_product_counter
    for p in products_json:
        # standard transforamtion for all images
        transformation = 'f_auto,q_auto,c_fit,w_320,h_320'
        try:
            # always uses the first image
            product_img_url = p['imageUrlTemplates'][0]
            product_img_url_transformed = str(product_img_url).replace(
                '{transformations}', transformation)
        except KeyError:
            # sometimes there is no image for a product
            product_img_url_transformed = ""
        # check prevents multiple insertions of the same product
        if p['gtin'] not in id_index:
            # write to csv file
            try:
                brand_name = p['brandName']
            except KeyError:
                # sometimes a product has no brand
                brand_name = ''
            csv_writer.writerow([p['gtin'], brand_name, p['title'], p['price']['value'],
                                'https://dm.de' + p['relativeProductUrl'],  product_img_url_transformed])
            id_index.append(p['gtin'])
            # statistical purpose only
            global_product_counter += 1
        if not alt_search:
            display_crawl_progress(21469)


def display_crawl_progress(max):
    """Display crawl progess"""
    progress = int((global_product_counter / max) * 20)
    sys.stdout.write('\r')
    sys.stdout.write("[%-20s] %d%%" % ('='*progress, 5*progress))
    sys.stdout.flush()


def find_alt_brand_names(csv_writer):
    """Some brands have different names than those listed on the brands page making them difficult to find..."""
    sys.stdout.write('\n')
    logging.info(
        'trying to find alternative brand names and their products...')
    global brands_without_products
    url = 'https://product-search.services.dmtech.com/de/search?pageSize=1000&query='
    for item in brands_without_products:
        # use the search api
        json_file = json.loads(requests.get(url + item).text)
        write_line_to_csv(csv_writer, json_file['products'], True)


def get_brands_from_alphanumerical_search(csv_writer):
    url = "https://product-search.services.dmtech.com/de/search?pageSize=1000&sort=price_asc&query="
    numbers = list(range(0, 10))
    alphabet = list(string.ascii_lowercase)
    cross_alpha = [x+y for x in alphabet for y in alphabet]
    number_alpha = [str(x)+y for x in numbers for y in alphabet]
    alpha_number = [x + str(y) for x in alphabet for y in numbers]
    search_query = numbers + number_alpha + alpha_number + cross_alpha
    product_count = 0
    brands = []
    logging.info('searching for more brands through alphanumerical search...')
    for query in search_query:
        page = json.loads(requests.get(url + str(query)).text)
        product_count += int(page['count'])
        navigate_pages(page, csv_writer, str(query), brands)
        sys.stdout.write('\r')
        sys.stdout.write('searching: ' + str(query))
        sys.stdout.flush()
    brands = list(dict.fromkeys(brands))
    sys.stdout.write('\n')
    logging.info('found ' + str(len(brands)) +
                 ' brands through alphanumerical search')
    return brands


def navigate_pages(page, csv_writer, query, brands):
    brand_list = []
    count = page['count']
    for i in range(0, int(math.ceil(count / 1000.0))):
        if i == 1:
            url = "https://product-search.services.dmtech.com/de/search?pageSize=1000&sort=price_desc&query="
            page = json.loads(requests.get(url + query).text)
        elif i == 2:
            url = "https://product-search.services.dmtech.com/de/search?pageSize=1000&sort=new&query="
            page = json.loads(requests.get(url + query).text)
        elif i == 3:
            url = "https://product-search.services.dmtech.com/de/search?pageSize=1000&query="
            page = json.loads(requests.get(url + query).text)
        elif i >= 4:
            break
        for pro in page['products']:
            try:
                brand_list.append(pro['brandName'])
            except KeyError:
                pass
        write_line_to_csv(csv_writer, page['products'], True)
    extract_brands(brand_list, brands)


def extract_brands(json_array, brands):
    array = list(set(json_array))
    for brand in array:
        brands.append(urllib.parse.quote_plus(brand))


global_product_counter = 0
brands_without_products = []
id_index = []
d = os.path.dirname(__file__)

if __name__ == "__main__":
    startTime = datetime.now()
    logging.basicConfig(level=logging.INFO)
    main()
    logging.info('-> total of ' +
                 str(global_product_counter) + ' products found')
    logging.info('result file location: ' + d + '/dm.csv')
    logging.info('script run time: ' + str(datetime.now() - startTime))
