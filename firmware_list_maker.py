#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from bcf.firmware.GithubApi import GithubApi
import yaml
import json
from pprint import pprint
from datetime import datetime
import os

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logging.getLogger("urllib3").setLevel(logging.WARNING)

save_path = os.environ.get('SAVE_PATH', '/var/www/firmware')

logging.info("Save path: %s", save_path)

ga = GithubApi(oauth_token=os.environ.get('GIT_OAUTH_TOKEN', None))

# pprint(ga.make_firmware_list_from_repo("hardwario/twr-radio-push-button")); exit()

def sort_firmware_key(firmware):
    name = firmware['name']
    for i, k in enumerate(('radio-dongle', 'gateway-usb-dongle', 'radio', "lora", "nbiot", "sigfox")):
        if k in name:
            return str(i) + name
    return name

firmware_list = ga.make_firmware_list_for_owner("hardwario", ignore_empty=True)

logging.info("Sort")
firmware_list.sort(key=sort_firmware_key)

for firmware in firmware_list:
    if firmware['name'] == "hardwario/bcf-gateway-usb-dongle":
        firmware["images"] = [{
            "title": "",
            "url": "https://cdn.myshoptet.com/usr/shop.bigclown.com/user/shop/detail_alt_1/159-2.png?5a1af76a"
        }]


payload = {
    "list": firmware_list,
    "date": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "version": 0
}

filename = os.path.join(save_path, 'yml')
logging.info("Save to: %s", filename)
with open(filename, 'w') as f:
    yaml.safe_dump(payload, f, indent=2, default_flow_style=False)

filename = os.path.join(save_path, 'json')
logging.info("Save to: %s", filename)
with open(filename, 'w') as f:
    json.dump(payload, f, indent=2)

