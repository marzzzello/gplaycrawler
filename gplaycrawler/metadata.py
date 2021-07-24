from os import path, mkdir, walk
from requests.exceptions import HTTPError, ReadTimeout
import json
import queue
import threading
import time

from playstoreapi.googleplay import GooglePlayAPI, LoginError
from gplaycrawler.utils import get_logger


class Metadata:
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

    def worker(self, api, q, done_ids, out_dir, threads):
        while not q.empty():
            packageName = q.get_nowait()  # non blocking
            self.log.debug(f'Start getting metadata for "{packageName}"')

            try:
                result = api.details(packageName)
            except HTTPError as e:
                if e.response.status_code == 429 or e.response.status_code == 401:
                    if e.response.status_code == 401:
                        self.log.warning('Unauthorized. Trying relogin...')
                    else:
                        self.log.warning('metadata got rate limited')
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
                continue
            except ReadTimeout:
                self.log.debug(f'Request did timeout (worker), add back {packageName}')
                q.put_nowait(packageName)
                q.task_done()
                continue

            filepath = path.join(out_dir, packageName + '.json')
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2)

            q.task_done()
            self.log.info(f'Done: {len(done_ids)}, to do: {q.qsize()}')
            done_ids.add(packageName)

        t = threading.current_thread()
        self.log.info(f'{t.name} finished. Queue empty')
        t.done = True
        return

    def getMetadata(self, in_file, out_dir, num_threads):
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
            ids_done.add(file.rstrip('.json'))

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
                t = threading.Thread(target=self.worker, args=(api, q, ids_done, out_dir, threads))
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
