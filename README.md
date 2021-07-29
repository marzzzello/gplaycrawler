![](https://forthebadge.com/images/badges/built-with-love.svg)
![](https://forthebadge.com/images/badges/fuck-it-ship-it.svg)
![](https://forthebadge.com/images/badges/contains-Cat-GIFs.svg)

[![Repo on GitLab](https://img.shields.io/badge/repo-GitLab-fc6d26.svg?style=for-the-badge&logo=gitlab)](https://gitlab.com/marzzzello/gplaycrawler)
[![Repo on GitHub](https://img.shields.io/badge/repo-GitHub-4078c0.svg?style=for-the-badge&logo=github)](https://github.com/marzzzello/gplaycrawler)
[![license](https://img.shields.io/github/license/marzzzello/gplaycrawler.svg?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIHN0eWxlPSJmaWxsOiNkZGRkZGQiIGQ9Ik03IDRjLS44MyAwLTEuNS0uNjctMS41LTEuNVM2LjE3IDEgNyAxczEuNS42NyAxLjUgMS41UzcuODMgNCA3IDR6bTcgNmMwIDEuMTEtLjg5IDItMiAyaC0xYy0xLjExIDAtMi0uODktMi0ybDItNGgtMWMtLjU1IDAtMS0uNDUtMS0xSDh2OGMuNDIgMCAxIC40NSAxIDFoMWMuNDIgMCAxIC40NSAxIDFIM2MwLS41NS41OC0xIDEtMWgxYzAtLjU1LjU4LTEgMS0xaC4wM0w2IDVINWMwIC41NS0uNDUgMS0xIDFIM2wyIDRjMCAxLjExLS44OSAyLTIgMkgyYy0xLjExIDAtMi0uODktMi0ybDItNEgxVjVoM2MwLS41NS40NS0xIDEtMWg0Yy41NSAwIDEgLjQ1IDEgMWgzdjFoLTFsMiA0ek0yLjUgN0wxIDEwaDNMMi41IDd6TTEzIDEwbC0xLjUtMy0xLjUgM2gzeiIvPjwvc3ZnPgo=)](LICENSE.md)
[![commit-activity](https://img.shields.io/github/commit-activity/m/marzzzello/gplaycrawler.svg?style=for-the-badge)](https://img.shields.io/github/commit-activity/m/marzzzello/gplaycrawler.svg?style=for-the-badge)
[![Mastodon Follow](https://img.shields.io/mastodon/follow/103207?domain=https%3A%2F%2Fsocial.tchncs.de&logo=mastodon&style=for-the-badge)](https://social.tchncs.de/@marzzzello)

# gplaycrawler

Discover apps by different methods. Mass download app packages and metadata.

## Setup

Install protobuf:

Using apt:

```sh
$ sudo apt install protobuf-compiler
```

Using pacman:

```sh
$ sudo pacman -S protobuf
```

Check version:

```sh
$ protoc --version  # Ensure compiler version is 3+
```

Install gplaycrawler using pip:

```sh
$ pip install gplaycrawler
```

## Usage

set env vars (optional):

```sh
export PLAYSTORE_TOKEN='ya29.fooooo'
export PLAYSTORE_GSFID='1234567891234567890'
export HTTP_PROXY='http://localhost:8080'
export HTTPS_PROXY='http://localhost:8080'
export CURL_CA_BUNDLE='/usr/local/myproxy_info/cacert.pem'
```

```
usage: gplaycrawler [-h] [-v {warning,info,debug}]
                    {help,usage,charts,search,related,metadata,packages} ...

Crawl the Google PlayStore

positional arguments:
  {help,usage,charts,search,related,metadata,packages}
                        Desired action to perform
    help                Print this help message
    usage               Print full usage
    charts              parallel downloading of all cross category app charts
    search              parallel searching of apps via search terms
    related             parallel searching of apps via related apps
    metadata            parallel scraping of app metadata
    packages            parallel downloading app packages

optional arguments:
  -h, --help            show this help message and exit
  -v {warning,info,debug}, --verbosity {warning,info,debug}
                        Set verbosity level (default: info)


All commands in detail:


Common optional arguments for related, search, metadata, packages:
  --locale LOCALE      (default: en_US)
  --timezone TIMEZONE  (default: UTC)
  --device DEVICE      (default: px_3a)
  --delay DELAY        Delay between every request in seconds (default: 0.51)
  --threads THREADS    Number of parallel workers (default: 2)


related:
usage: gplaycrawler related [-h] [--locale LOCALE] [--timezone TIMEZONE]
                            [--device DEVICE] [--delay DELAY]
                            [--threads THREADS] [--output OUTPUT]
                            [--level LEVEL]
                            input

parallel searching of apps via related apps

positional arguments:
  input                name of the input file (default: charts.json)

optional arguments:
  --output OUTPUT      base name of the output files (default: ids_related)
  --level LEVEL        How deep to crawl (default: 3)


search:
usage: gplaycrawler search [-h] [--locale LOCALE] [--timezone TIMEZONE]
                           [--device DEVICE] [--delay DELAY]
                           [--threads THREADS] [--output OUTPUT]
                           [--length LENGTH]

parallel searching of apps via search terms

optional arguments:
  --output OUTPUT      name of the output file (default: ids_search.json)
  --length LENGTH      length of strings to search (default: 2)


metadata:
usage: gplaycrawler metadata [-h] [--locale LOCALE] [--timezone TIMEZONE]
                             [--device DEVICE] [--delay DELAY]
                             [--threads THREADS] [--output OUTPUT]
                             input

parallel scraping of app metadata

positional arguments:
  input                name of the input file (json)

optional arguments:
  --output OUTPUT      directory name of the output files (default:
                       out_metadata)


packages:
usage: gplaycrawler packages [-h] [--locale LOCALE] [--timezone TIMEZONE]
                             [--device DEVICE] [--delay DELAY]
                             [--threads THREADS] [--output OUTPUT]
                             [--expansions] [--splits]
                             input

parallel downloading app packages

positional arguments:
  input                name of the input file (json)

optional arguments:
  --output OUTPUT      directory name of the output files (default:
                       out_packages)
  --expansions         also download expansion files (default: False)
  --splits             also download split files (default: False)
```
