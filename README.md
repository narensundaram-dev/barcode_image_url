## Setup:

- Install chrome-driver(for your chrome version) from https://chromedriver.chromium.org/downloads
- Extract the downloaded zip to ~/Documents/chromedriver
- Add the path to conf.ini under variable CHROME_DRIVER_PATH

## How to run:

- Add barcodes in `barcodes.txt`
- `python3.6 barcode_img_url.py -w "upcitemdb" -d "~/Documents/chromedriver"`

## For help:

- `python3.6 barcode_img_url.py -h`
