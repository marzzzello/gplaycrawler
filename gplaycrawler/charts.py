import json
import threading
import time

from reprint import output
from playstoreapi.googleplay import GooglePlayAPI, LoginError
from gplaycrawler.utils import get_logger


class Charts:
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

    def worker(self, api, categorie, chart, ids):
        '''
        Get all ids by downloading all pages
        Every page has 6 entries and the api returns ~110 pages resulting in ~660 ids
        '''
        if categorie not in ids:
            ids[categorie] = {}
        if chart not in ids[categorie]:
            ids[categorie][chart] = []
        nextPageUrl = None
        while True:
            data = api.topChart(cat=categorie, chart=chart, nextPageUrl=nextPageUrl)
            s = data.get('subItem')
            if s is None:
                self.log.warning('No subItem found')
                self.log.debug(s)
                continue
            for subItem in data['subItem']:
                for app in subItem['subItem']:
                    # print('\t{} ({}): {}'.format(chart, len(ids[chart]), app['id']))
                    ids[categorie][chart].append(app['id'])
                try:
                    nextPageUrl = subItem['containerMetadata']['nextPageUrl']
                except KeyError:
                    return

    def getCharts(self, out_file):
        '''
        parallel downloading of all app charts and saving them in a json file
        '''
        api = GooglePlayAPI(self.locale, self.timezone, self.device, delay=self.delay)
        try:
            api.envLogin(quiet=self.quiet, check=False)
        except LoginError:
            self.log.info('Login failed.')

        charts = ['apps_topselling_free', 'apps_topselling_paid', 'apps_topgrossing', 'apps_movers_shakers']
        categories = ['APPLICATION', 'GAME']
        ids = {}
        threads = []
        for cat in categories:
            for chart in charts:
                t = threading.Thread(target=self.worker, args=(api, cat, chart, ids))
                t.name = f'{cat}: {chart}'
                threads.append(t)
                print('starting thread', t.name)
                t.start()

        with output(output_type='dict') as output_lines:
            alive = 1
            while alive > 0:
                alive = 0
                for t in threads:
                    n = t.name.split(': ')
                    cat = n[0]
                    chart = n[1]
                    if t.is_alive():
                        alive += 1
                        output_lines[t.name] = f'{len(ids[cat][chart])} ...'
                    else:
                        output_lines[t.name] = f'{len(ids[cat][chart])} (done)'
                time.sleep(0.1)

        self.log.info('Waiting for threads')
        for t in threads:
            t.join()

        self.log.info(f'Writing to file {out_file}')
        with open(out_file, 'w') as fp:
            json.dump(ids, fp, indent=2)
