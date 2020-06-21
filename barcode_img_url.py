import os
import json
import shutil
import logging
import argparse
import traceback
from datetime import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC

log = logging.getLogger(__file__.split('/')[-1])


def config_logger():
    log_level = logging.DEBUG
    log.setLevel(log_level)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter('%(levelname)s: %(asctime)s - %(name)s:%(lineno)d - %(message)s')
    log_handler.setFormatter(log_formatter)
    log.addHandler(log_handler)
config_logger()


BLOOKUP = "barcodelookup"
BSPIDER = "barcodespider"
UPCDB = "upcitemdb"
UPCZILLA = "upczilla"


websites = {
    BLOOKUP: "https://www.barcodelookup.com/{}",
    BSPIDER: "https://www.barcodespider.com/{}",
    UPCDB: "https://www.upcitemdb.com/upc/{}",
    UPCZILLA: "https://www.upczilla.com/item/{}"
}
dir_data = "data"
barcodes_done = []
file_barcodes = "barcodes.txt"
file_barcode_pending = "barcodes_pending.txt"
resumer = False
data = []


with open("settings.json", "r") as f:
    settings = json.load(f)


def scrape_blookup(chrome, url):
    chrome.get(url)
    return "NotImplemented"


def scrape_bspider(chrome, url):
    chrome.get(url)
    try:
        wait = settings["page_load_timeout"]["value"]
        WebDriverWait(chrome, wait).until(EC.presence_of_element_located((By.CLASS_NAME, 'thumb-image')))
        soup = BeautifulSoup(chrome.page_source, "html.parser")
        image_url = soup.find("div", class_="thumb-image").find("img").attrs["src"]

    except Exception as e:
        log.info("Error on getting the image_url from {}. Skipped".format(url))
        image_url = "skipped"

    return image_url


def scrape_upcdb(chrome, url):
    chrome.get(url)
    try:
        wait = settings["page_load_timeout"]["value"]
        WebDriverWait(chrome, wait).until(EC.presence_of_element_located((By.CLASS_NAME, 'main-img')))
        soup = BeautifulSoup(chrome.page_source, "html.parser")
        image_url = soup.find("img", class_="product").attrs["src"]

    except Exception as e:
        log.info("Error on getting the image_url from {}. Skipped".format(url))
        image_url = "skipped"

    return image_url


def scrape_upczilla(chrome, url):
    chrome.get(url)
    try:
        wait = settings["page_load_timeout"]["value"]
        WebDriverWait(chrome, wait).until(EC.presence_of_element_located((By.CLASS_NAME, 'imgdiv')))
        soup = BeautifulSoup(chrome.page_source, "html.parser")
        image_url = soup.find("div", class_="imgdiv").find("img").attrs["src"]

    except Exception as e:
        log.info("Error on getting the image_url from {}. Skipped".format(url))
        image_url = "skipped"

    return image_url


def get_image_url(args, barcode):
    log.info("Getting image for barcode: " + barcode)
    chrome = webdriver.Chrome(args.driver_path)

    if args.website == BLOOKUP:
        url = websites[BLOOKUP].format(barcode)
        image_url = scrape_blookup(chrome, url)

    elif args.website == BSPIDER:
        url = websites[BSPIDER].format(barcode)
        image_url = scrape_bspider(chrome, url)

    elif args.website == UPCDB:
        url = websites[UPCDB].format(barcode)
        image_url = scrape_upcdb(chrome, url)

    else:
        url = websites[UPCZILLA].format(barcode)
        image_url = scrape_upczilla(chrome, url)

    chrome.close()
    return barcode, image_url


def get(args):
    futures = []
    workers = settings["workers"]["value"]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        with open(file_barcode_pending) as f:
            for line in f.readlines():
                barcode = line.strip()
                ft = executor.submit(fn=get_image_url, args=args, barcode=barcode)
                futures.append(ft)

    for future in as_completed(futures):
        barcode, image_url = future.result()
        detail = {"barcode": barcode, "image_url": image_url}
        data.append(detail)
        barcodes_done.append(barcode)


def save(args):
    fp = os.path.join(os.getcwd(), dir_data, "{}.xlsx".format(args.website))
    df = pd.DataFrame(data)
    df.to_excel(fp, index=False)
    log.info("Fetched data has been stored in {} file".format(fp))


def setup():
    shutil.rmtree(dir_data, ignore_errors=True)
    os.makedirs(dir_data)

    if not os.path.exists(file_barcodes):
        log.error("Error: " + file_barcodes + " doesn't exist. Please have the file in the script directory.")

    if not os.path.exists(file_barcode_pending):
        log.info(file_barcode_pending + " not found. Will continue to read all the barcodes in " + file_barcodes)
        shutil.copyfile(file_barcodes, file_barcode_pending)
    else:
        log.info(file_barcode_pending + " found! Resuming with the existing barcodes... Please ensure you took up the backup.")
        print("To continue, enter 'yes': ")
        user_input = input().lower().strip()
        global resumer
        resumer = True
        if user_input != "yes":
            print("User confirmation failed... Exited.")
            exit(1)


def cleanup():
    shutil.rmtree(dir_data, ignore_errors=True)
    if os.path.exists(file_barcode_pending):
        os.remove(file_barcode_pending)


def get_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-w', "--website", type=str, choices=(UPCZILLA, BSPIDER, UPCDB), required=True)
    arg_parser.add_argument('-d', "--driver_path", type=str, help="Enter the chromedriver path", required=True)
    arg_parser.add_argument('--cleanup', "--cleanup", action="store_true", default=False)
    arg_parser.add_argument('-log-level', '--log_level', type=str, choices=("INFO", "DEBUG"),
                            default="INFO", help='Where do you want to post the info?')
    return arg_parser.parse_args()


def main():
    args = get_args()
    if args.cleanup:
        cleanup()

    setup()
    get(args)
    save(args)


if __name__ == "__main__":
    start = dt.now()
    log.info("Script starts at: {}".format(start.strftime("%d-%m-%Y %H:%M:%S %p")))

    try:
        main()
    except Exception as e:
        log.error("Error: " + str(e))
        traceback.print_exc()
        exit(1)
    finally:
        log.info("Backing up the pending barcodes to be done ...")

        fp_barcode = file_barcodes if not resumer else file_barcode_pending
        with open(fp_barcode, "r") as f:
            content = f.read().strip()
            barcodes = content.split("\n")

        with open(file_barcode_pending, "w+") as fp:
            barcodes_pending = set(barcodes) - set(barcodes_done)
            fp.write("\n".join(list(barcodes_pending)))

    end = dt.now()
    log.info("Script ends at: {}".format(end.strftime("%d-%m-%Y %H:%M:%S %p")))
    elapsed = round(((end - start).seconds / 60), 4)
    log.info("Time Elapsed: {} minutes".format(elapsed))
