import json
import threading
import time
import queue
from requests.exceptions import HTTPError, ReadTimeout
import random

from playstoreapi.googleplay import GooglePlayAPI, LoginError
from gplaycrawler.utils import get_logger


# def details(packageName):

#     d = api.details(packageName)
#     filename = packageName + '.json'
#     with open(filename, 'w') as f:
#         json.dump(d, f)

#     d = api.bulkDetails([packageName])
#     filename = packageName + '_bulk.json'
#     with open(filename, 'w') as f:
#         json.dump(d, f)


class Related:
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

    def streamPages(self, api, nextPageUrl):
        ids = set()
        while True:
            try:
                d = api.streamDetails(nextPageUrl=nextPageUrl)
            except HTTPError as e:
                if e.response.status_code == 429 or e.response.status_code == 401:
                    if e.response.status_code == 401:
                        self.log.warning('Unauthorized. Trying relogin...')
                    else:
                        self.log.debug('streamPages got rate limited')
                    api = GooglePlayAPI(self.locale, self.timezone, self.device, delay=self.delay)
                    while True:
                        try:
                            api.envLogin(quiet=self.quiet)
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
                self.log.debug('Request did timeout (pages), try again in 1 min')
                time.sleep(60)
                continue
            try:
                streamBundle = d['item'][0]['subItem']
            except KeyError:
                try:
                    streamBundle = d[0]['subItem']
                except KeyError:
                    self.log.debug(f'No bundle found (pages) {d}')
                    return ids
            if len(streamBundle) > 1:
                self.log.warning('This should not happen')
                return ids
            stream = streamBundle[0]
            try:
                nextPageUrl = stream['containerMetadata']['nextPageUrl']
            except KeyError:
                return ids

            for subItem in stream['subItem']:
                ids.add(subItem['id'])
            # print(stream['title'], len(ids))

    def streamDetails(self, api, ids, packageName):
        d = api.streamDetails(packageName)
        try:
            streamBundle = d['item'][0]['subItem']
        except KeyError:
            try:
                streamBundle = d[0]['subItem']
            except KeyError:
                self.log.warning(f'{packageName}: No bundle found (details)')
                self.log.debug(d)
                return
        for stream in streamBundle:
            # print(packageName, stream['title'])
            for subItem in stream['subItem']:
                ids.add(subItem['id'])

            # get all pages for every stream
            try:
                nextPageUrl = stream['containerMetadata']['nextPageUrl']
            except KeyError:
                pass
            else:
                i = self.streamPages(api, nextPageUrl)
                before = len(ids)
                ids.update(i)
                new = len(ids) - before
                self.log.debug(f"{packageName} {stream['title']}: Got {len(i)} package names, {new} new")

            # print('return', len(ids), ids)
            # return ids

    def worker(self, api, q, ids, done_ids, shared, tmp_file, out_file, until_level=3):
        s = shared
        t = threading.current_thread()
        t.level = s['level']
        t.idle = False
        while True:
            try:
                packageName = q.get_nowait()  # non blocking
                self.log.debug(f'Start crawling {packageName}')
            except queue.Empty:
                t.idle = True
                time.sleep(random.random())
                if t.level != s['level']:
                    if s['level'] > until_level:
                        self.log.info('Done')
                        t.done = True
                        return
                    else:
                        self.log.debug('sleeping (wait for save and filled queue')
                        while q.empty():
                            time.sleep(1)
                        t.idle = False
                        t.level += 1
                        continue

                # this code is just run by the first thread
                # level up and save
                t.level += 1
                s['level'] += 1
                for thread in s['threads']:
                    while not thread.idle:
                        self.log.debug('Waiting for other threads to finish level')
                        time.sleep(1)

                todo_ids = ids - done_ids
                self.log.info(f'Done with level {s["level"]}. Got {len(ids)} IDs. Done IDs: {len(done_ids)}')

                self.log.info('Saving json file\n')
                if s['level'] > until_level:
                    filename = f'{out_file}.json'
                else:
                    filename = f'{out_file}_level-{s["level"]}.json'

                with open(filename, 'w') as f:
                    json.dump({"done": list(done_ids), "ids": list(ids)}, f, indent=2)

                if s['level'] > until_level:
                    self.log.info(f'{t.name}: First thread done')
                    t.done = True
                    return

                for packageName in todo_ids:
                    q.put_nowait(packageName)

                self.log.info(f'Filled queue for next level: {s["level"]}, Todo: {q.qsize()}\n')
                continue
            try:
                self.streamDetails(api, ids, packageName)
            except HTTPError as e:
                if e.response.status_code == 429 or e.response.status_code == 401:
                    if e.response.status_code == 401:
                        self.log.warning('Unauthorized. Trying relogin...')
                    else:
                        self.log.debug('streamDetails got rate limited')
                    api = GooglePlayAPI(self.locale, self.timezone, self.device, delay=self.delay)
                    while True:
                        try:
                            api.envLogin(quiet=self.quiet)
                        except LoginError:
                            self.log.info('Login failed. Retry in 3 minutes')
                            time.sleep(180)
                        else:
                            break
                    self.log.debug(f'new api, logged in, add back {packageName}')
                    q.put_nowait(packageName)
                    q.task_done()
                    continue
                else:
                    self.log.warning(str(e))
            except ReadTimeout:
                self.log.debug(f'Request did timeout (details), add back {packageName}')
                q.put_nowait(packageName)
                q.task_done()
                continue

            q.task_done()
            self.log.info(f'Done: {len(done_ids)}, to do: {q.qsize()} received {len(ids)} ids (level {t.level})')
            done_ids.add(packageName)

            # save tmp file regularly
            num_threads = len(s['threads'])
            if len(done_ids) % (100 * num_threads) == 0:
                self.log.debug(f'Saving tmp file {tmp_file}')
                with open(tmp_file, 'w') as f:
                    json.dump({"done": list(done_ids), "ids": list(ids)}, f, indent=2)

    def getRelated(self, in_file, out_file, until_level=3, threads=3):
        '''
        parallel downloading of related apps from charts.json and saving them in a json file
        '''
        with open(in_file) as f:
            input_dict = json.load(f)

        in_ids = set()
        try:
            for cat in input_dict:
                for chart in input_dict[cat]:
                    in_ids.update(input_dict[cat][chart])
        except TypeError:
            self.log.info('doesn\'t look like a charts.json. Trying to load level file')
            if type(input_dict) == list:
                in_ids.update(input_dict)
            elif type(input_dict.get('ids')) == list:
                in_ids.update(input_dict['ids'])
            else:
                self.log.error('Could not load input file')
                return

        out_file = out_file.rstrip('.json')

        ids = set()
        done_ids = set()

        # resume from tmp file if it exists
        tmp_file = out_file + '_tmp.json'
        try:
            with open(tmp_file) as f:
                done = json.load(f)
            done_ids.update(done['done'])
            ids.update(done['ids'])
        except FileNotFoundError:
            pass
        except Exception as e:
            self.log.warning(str(e))

        todo_ids = in_ids - done_ids
        q = queue.Queue()
        for packageName in todo_ids:
            q.put_nowait(packageName)

        self.log.info(f'Done: {len(done_ids)}, to do: {q.qsize()} received {len(ids)} ids')

        # needs to be dict
        shared = dict()
        shared['level'] = 0
        shared['threads'] = []

        i = 0
        while True:
            while len(shared['threads']) < threads:
                api = GooglePlayAPI(self.locale, self.timezone, self.device, delay=self.delay)
                while True:
                    try:
                        api.envLogin(quiet=self.quiet)
                    except LoginError:
                        self.log.info('Login failed. Retry in 3 minutes')
                        time.sleep(180)
                    else:
                        break

                t = threading.Thread(
                    target=self.worker, args=(api, q, ids, done_ids, shared, tmp_file, out_file, until_level)
                )
                i += 1
                t.name = f'Worker-{i}'
                t.done = False
                shared['threads'].append(t)
                t.start()
                self.log.info(f'Started {t.name}')

            for t in shared['threads']:
                t.join(timeout=1)
                if not t.is_alive():
                    if t.done:
                        threads -= 1
                    else:
                        self.log.info(f'Worker {t.name} crashed. Starting a new worker')
                        time.sleep(1)

        self.log.info('Threads finished')
        self.log.info(f'Saving out file {out_file}.json')
        with open(out_file + '.json', 'w') as f:
            json.dump({"done": list(done_ids), "ids": list(ids)}, f, indent=2)
