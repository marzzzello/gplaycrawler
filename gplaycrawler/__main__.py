#!/usr/bin/env python

# set env vars (optional):
# export GPAPI_TOKEN='ya29.fooooo'
# export GPAPI_GSFID='1234567891234567890'
# export HTTP_PROXY='http://localhost:8080'
# export HTTPS_PROXY='http://localhost:8080'
# export CURL_CA_BUNDLE='/usr/local/myproxy_info/cacert.pem'


import sys
import os

file_path = (
    '/home/marcel/rub/BA/2020-cross-platform-pps/code/downloader-marcel/google-playstore/gplay_crawler/gplaycrawler'
)
sys.path.append(os.path.dirname(file_path))

from gplaycrawler.main import main


if __name__ == '__main__':
    main()
