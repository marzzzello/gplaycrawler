from os import path, mkdir, walk
from requests.exceptions import HTTPError, ReadTimeout, ChunkedEncodingError
import json
import queue
import threading
import time

from playstoreapi.googleplay import GooglePlayAPI, LoginError, RequestError
from gplaycrawler.utils import get_logger


class Packages:
    def __init__(self, locale='en_US', timezone='UTC', device='px_3a', delay=None, log_level='info'):
        self.locale = locale
        self.timezone = timezone
        self.device = device
        self.delay = delay
        self.lastRequest = 0

        self.log_level = log_level
        self.log = get_logger(log_level, name=__name__)
        self.log.debug('Logging is set to debug')

        if log_level.lower() == 'debug':
            self.quiet = False
        else:
            self.quiet = True

    def worker(self, api, q, done_ids, out_dir, threads, expansion_files, splits):
        while not q.empty():
            if self.delay:
                tosleep = -(time.time() - self.lastRequest - self.delay)
                if tosleep > 0:
                    # print('sleeping', tosleep)
                    time.sleep(tosleep)

            packageName = q.get_nowait()  # non blocking
            self.log.debug(f'Start getting package "{packageName}"')

            try:
                # versionCode=None, offerType=1, expansion_files=False
                download = api.download(packageName, expansion_files=expansion_files)
                self.lastRequest = time.time()
            except RequestError as e:
                if "Can't install. Please try again later." in str(e):
                    self.log.info(f'{packageName}: paid app. Skipping')
                else:
                    self.log.warning(f'{packageName}: {str(e)}')
                    self.log.debug('Readd to queue')
                    q.put_nowait(packageName)
                q.task_done()
                continue
            except HTTPError as e:
                if e.response.status_code == 429 or e.response.status_code == 401:
                    if e.response.status_code == 401:
                        self.log.warning('Unauthorized. Trying relogin...')
                    else:
                        self.log.warning('packages got rate limited')
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
                else:
                    self.log.warning(str(e))
                    q.task_done()
                    continue
            except ReadTimeout:
                self.log.debug(f'Request did timeout (worker), add back {packageName}')
                q.put_nowait(packageName)
                q.task_done()
                continue

            # download = server.download(docid, expansion_files=True)

            if download['docId'] != packageName:
                self.log.warning(f"package name doesn't match {download['docId']} != {packageName}")

            filepath = path.join(out_dir, packageName + '.apk')

            self.log.debug('Downloading apk...')
            try:
                with open(filepath, 'wb') as f:
                    for chunk in download.get('file').get('data'):
                        f.write(chunk)
            except ChunkedEncodingError as e:
                self.warning(f'Error writing chunk for {packageName}.apk: {str(e)}')

            if expansion_files is True and download['additionalData'] != []:
                self.log.debug('Downloading additional files...')
                for obb in download['additionalData']:
                    name = f"{packageName}.{obb['type']}.{str(obb['versionCode'])}.obb"
                    filepath = path.join(out_dir, name)
                    self.log.debug(f'Additional file: {name}')
                    try:
                        with open(filepath, 'wb') as f:
                            for chunk in obb.get('file').get('data'):
                                f.write(chunk)
                    except ChunkedEncodingError as e:
                        self.warning(f'Error writing chunk for {name}: {str(e)}')

            if splits is True and download['splits'] != []:
                self.log.debug('Downloading splits...')
                for split in download.get('splits'):
                    name = f"{packageName}.split.{split['name']}.zip"
                    filepath = path.join(out_dir, name)
                    self.log.debug(f'Split: {name}')
                    try:
                        with open(filepath, "wb") as f:
                            for chunk in split["file"]["data"]:
                                f.write(chunk)
                    except ChunkedEncodingError as e:
                        self.warning(f'Error writing chunk for {name}: {str(e)}')

            q.task_done()
            self.log.info(f'Done: {len(done_ids)}, to do: {q.qsize()}')
            done_ids.add(packageName)

        t = threading.current_thread()
        self.log.info(f'{t.name} finished. Queue empty')
        t.done = True
        return

    def getPackages(self, in_file, out_dir, num_threads, expansion_files, splits):
        ids = set()

        try:
            with open(in_file) as f:
                j = json.load(f)
        except FileNotFoundError:
            self.log.error('Input file not found')
            return

        if type(j) == list:
            ids.update(j)
        else:
            try:
                ids.update(j['done'])
                ids.update(j['ids'])
            except KeyError:
                self.log.error('Input file is in unknown format')

        # load ids that are already done via amp
        try:
            (_, _, done_filenames) = next(walk(out_dir))
        except StopIteration:
            done_filenames = []

        ids_done = set()
        for file in set(done_filenames):
            ids_done.add(file.rstrip('.apk'))

        todo_ids = ids - ids_done
        q = queue.Queue()
        for packageName in todo_ids:
            q.put_nowait(packageName)

        self.log.info(f'Done: {len(ids_done)}, to do: {q.qsize()}')
        try:
            mkdir(out_dir)
        except FileExistsError:
            pass

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
                t = threading.Thread(
                    target=self.worker, args=(api, q, ids_done, out_dir, threads, expansion_files, splits)
                )
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
