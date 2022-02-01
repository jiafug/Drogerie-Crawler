import csv
import string
import sys
from datetime import datetime
from typing import List

import requests
from bs4 import BeautifulSoup
from bs4.element import ResultSet

BASE_URL = "https://www.rossmann.de"


def get_soup(url: str) -> ResultSet:
    # get content of main page
    soup = BeautifulSoup(requests.get(
        BASE_URL + url).content, features="html.parser")
    for s in soup.select("script"):
        s.extract()
    # get body content of main page
    main_body = soup.find("body")
    return(main_body)


def get_brands() -> List:
    brands_url = "/de/marken/c/brands"
    soup = get_soup(brands_url)
    results = soup.find_all("li", {"class": "rm-brand__container-list-item"})
    records = []
    for result in results:
        name = result.find(
            "a", {"class": "rm-brand__container-list-link"}).text.strip()
        link = result.find(
            "a", {"class": "rm-brand__container-list-link"})["href"]
        records.append((name, link))
    print("no. of brands:" + str(len(records))) 
    return records


def get_products(url: str, records: list):
    soup = get_soup(url)
    try:
        results = soup.find_all("div", {"class": "rm-category__products"})[0]
        results = results.find_all("div", {"class": "rm-grid__content"})
    except IndexError:
        return []
    for result in results:
        product_base = result.find("div", {"class": "rm-tile-product"})
        product_wrapper = result.find(
            "div", {"class": "rm-tile-product__wrapper--image"})
        product_id = product_base["data-product-id2"]
        product_brand = product_base["data-product-brand"]
        product_name = product_base["data-product-name"]
        product_price = product_base["data-product-price"]
        product_link = product_wrapper.find(
            "a", {"class": "rm-tile-product__image"})["href"]
        product_link = BASE_URL + product_link
        product_image = product_wrapper.find(
            "img", {"class": "rm-tile-product__image rm-lazy__image"})["data-src"]
        product_image = product_image.split("?")[0]
        records.append((product_id, product_brand, product_name,
                       product_price, product_link, product_image))
    # check for additional pages
    pages = soup.find_all("a", {"rel": "next"})
    if len(pages) != 0:
        next_url = pages[0]["href"]
        if "page=" in next_url:
            get_products(next_url, records)
        else:
            return records
    return records


def display_progress(name):
    """Display crawl progess"""
    sys.stdout.write('\r')
    sys.stdout.write("current search: " + str(name) + "                    ")
    sys.stdout.flush()


def alphanumerical_search(products_list):
    print("starting alphanumerical search...")
    numbers = list(range(0, 10))
    alphabet = list(string.ascii_lowercase)
    query_list = alphabet
    res = []
    counter = 0
    for q in query_list:
        display_progress(q)
        products = get_products("/de/search/?text=" + str(q), [])
        for id, brand, name, price, link, image in products:
            if id not in products_list:
                counter += 1
                res.append((id, brand, name, price, link, image))
    print("\nfound through alphanumerical search: " + str(counter))
    return res


def main():
    with open("./rossmann.csv", "w", newline="") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=";")
        # write csv header
        csv_writer.writerow(["id", "brand", "name", "price", "link", "image"])
        print("starting brands search...")
        brands_list = get_brands()
        products_list = []  # list of ids
        for name, link in brands_list:
            display_progress(name)
            products = get_products(link, [])
            csv_writer.writerows(products)
            products_list.extend([i[0] for i in products])
        print("\nproducts found: " + str(len(products_list)))
        more_products = alphanumerical_search(products_list)
        csv_writer.writerows(more_products)


if __name__ == "__main__":
    startTime = datetime.now()
    main()
    print("script run time:" + str(datetime.now() - startTime))
