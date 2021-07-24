import json
import threading
import time
import queue
from requests.exceptions import HTTPError, ReadTimeout

from playstoreapi.googleplay import GooglePlayAPI, LoginError
from gplaycrawler.utils import get_logger

import string
import itertools


class Search:
    def __init__(self, locale='en_US', timezone='UTC', device='px_3a', delay=None, log_level='info'):
        self.locale = locale
        self.timezone = timezone
        self.device = device
        self.delay = delay

        self.log_level = log_level
        self.log = get_logger(log_level, name=__name__)
        self.log.debug('Logging is set to debug')

        if log_level.lower() == 'debug':
            self.quiet = False
        else:
            self.quiet = True

    def search(self, api, nextPageUrl=None, query=None):
        np = queue.Queue()
        if query is None:
            np.put_nowait(nextPageUrl)

        ids = set()
        done = set()
        num_pages = 0
        while not np.empty() or query is not None:
            nextPageUrl = None
            if query is None:
                nextPageUrl = np.get_nowait()
                if nextPageUrl in done:
                    continue
                done.add(nextPageUrl)

            try:
                result = api.search(query=query, nextPageUrl=nextPageUrl)
                query = None
            except HTTPError as e:
                if e.response.status_code == 429 or e.response.status_code == 401:
                    if e.response.status_code == 401:
                        self.log.warning('Unauthorized. Trying relogin...')
                    else:
                        self.log.warning('search got rate limited')
                    api = GooglePlayAPI(self.locale, self.timezone, self.device, delay=self.delay)
                    while True:
                        try:
                            api.envLogin(quiet=self.quiet, check=False)
                        except LoginError:
                            self.log.info('Login failed. Retry in 3 minutes')
                            time.sleep(180)
                        else:
                            break
                    self.log.debug('new api, logged in, try again')
                    np.put_nowait(nextPageUrl)
                else:
                    self.log.warning(str(e))
                continue

            if len(result) != 1:
                self.log.warning(f'Pages: Got result with len {len(result)}')
                self.log.debug(result)
                continue

            doc = result[0]
            clusters = doc.get('subItem')

            try:
                np.put_nowait(doc['containerMetadata']['nextPageUrl'])
            except KeyError:
                pass

            if clusters is None:
                self.log.debug('No clusters found in searchPages')
                continue

            num_pages += 1

            # at the first page there are also the clusters 'Recommended for you' and 'Related Searches'
            # so the item can be list of apps or related search terms
            for cluster in clusters:
                apps = 0
                try:
                    items = cluster['subItem']
                except KeyError:
                    items = []
                for item in items:
                    try:
                        ids.add(item['id'])
                    except KeyError:
                        pass
                    else:
                        apps += 1
                self.log.debug(f"queue: {np.qsize()}, pages: Found {apps} apps in cluster {cluster.get('title')}")

                try:
                    np.put_nowait(cluster['containerMetadata']['nextPageUrl'])
                except KeyError:
                    pass
        return ids

    def worker(self, api, q, ids, done_searchTerms, tmp_file, threads):
        while not q.empty():
            searchTerm = q.get_nowait()  # non blocking
            self.log.debug(f'Start searching "{searchTerm}"')

            try:
                sids = self.search(api, query=searchTerm)

            except HTTPError as e:
                if e.response.status_code == 429 or e.response.status_code == 401:
                    if e.response.status_code == 401:
                        self.log.warning('Unauthorized. Trying relogin...')
                    else:
                        self.log.warning('search worker got rate limited')
                    api = GooglePlayAPI(self.locale, self.timezone, self.device, delay=self.delay)
                    while True:
                        try:
                            api.envLogin(quiet=self.quiet, check=False)
                        except LoginError:
                            self.log.info('Login failed. Retry in 3 minutes')
                            time.sleep(180)
                        else:
                            break
                    self.log.debug(f'new api, logged in, add back {searchTerm}')
                    q.put_nowait(searchTerm)
                    q.task_done()
                    continue
                else:
                    self.log.warning(str(e))

            except ReadTimeout:
                self.log.debug(f'Request did timeout (search), add back {searchTerm}')
                q.put_nowait(searchTerm)
                q.task_done()
                continue

            q.task_done()
            before = len(ids)
            ids.update(sids)
            new = len(ids) - before
            self.log.debug(f'{searchTerm}: Got {len(sids)} package names, {new} new')

            self.log.info(f'Done: {len(done_searchTerms)}, to do: {q.qsize()} received {len(ids)} ids')
            done_searchTerms.add(searchTerm)

            # save tmp file regularly
            if len(done_searchTerms) % (100 * len(threads)) == 0:
                self.log.debug(f'Saving tmp file {tmp_file}')
                with open(tmp_file, 'w') as f:
                    json.dump({"done": list(done_searchTerms), "ids": list(ids)}, f, indent=2)

        t = threading.current_thread()
        self.log.info(f'{t.name} finished. Queue empty')
        t.done = True
        return

    def get_strings(self, alphabet):
        with open('chars.json') as f:
            chars = json.load(f)
        for charset in chars:
            if charset['name'] == alphabet:
                return charset['chars']

    def generate_strings(self, length=3):
        chars = string.ascii_lowercase
        # nums = string.digits

        for item in itertools.product(chars, repeat=length):
            yield "".join(item)

    def getSearch(self, out_file, num_threads, length):
        all_searchTerms = set()
        for s in self.generate_strings(length=length):
            all_searchTerms.add(s.lower())

        out_file = out_file.rstrip('.json')

        tmp_file = out_file + '_tmp.json'

        ids = set()
        done_searchTerms = set()

        # resume from tmp file if it exists
        try:
            with open(tmp_file) as f:
                done = json.load(f)
            done_searchTerms.update(done['done'])
            ids.update(done['ids'])
        except FileNotFoundError:
            pass
        except Exception as e:
            self.log.warning(str(e))

        todo_seachTerms = all_searchTerms - done_searchTerms
        q = queue.Queue()
        for searchTerm in todo_seachTerms:
            q.put_nowait(searchTerm)

        self.log.info(f'Done: {len(done_searchTerms)}, to do: {q.qsize()} received {len(ids)} ids')

        i = 0
        threads = []
        while num_threads > 0:
            while len(threads) < num_threads:
                api = GooglePlayAPI(self.locale, self.timezone, self.device, delay=self.delay)
                while True:
                    try:
                        api.envLogin(quiet=self.quiet, check=False)
                    except LoginError:
                        self.log.info('Login failed. Retry in 3 minutes')
                        time.sleep(180)
                    else:
                        break
                t = threading.Thread(target=self.worker, args=(api, q, ids, done_searchTerms, tmp_file, threads))
                i += 1
                t.name = f'Worker-{i}'
                t.done = False
                threads.append(t)
                t.start()
                self.log.info(f'Started {t.name}')
                # wait 10-11 min to start next thread
                # time.sleep(60 * 10 + random() * 60)

            for t in threads:
                t.join(timeout=1)
                if not t.is_alive():
                    if t.done:
                        num_threads -= 1
                    else:
                        threads.remove(t)
                        self.log.info(f'Worker {t.name} crashed. Starting a new worker')
                        time.sleep(1)

        self.log.info('Threads finished')
        self.log.info(f'Saving out file {out_file}.json')
        with open(out_file + '.json', 'w') as f:
            json.dump({"done": list(done_searchTerms), "ids": list(ids)}, f, indent=2)
