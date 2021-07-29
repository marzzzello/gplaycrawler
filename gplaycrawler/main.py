# stdlib
from argparse import ArgumentParser, HelpFormatter
from importlib.metadata import metadata

# internal
from gplaycrawler.related import Related
from gplaycrawler.search import Search
from gplaycrawler.metadata import Metadata
from gplaycrawler.packages import Packages
from gplaycrawler.charts import Charts


class F(HelpFormatter):
    def __init__(self, *args, **kwargs):
        kwargs['max_help_position'] = 30
        super().__init__(*args, **kwargs)


def main():
    parser = ArgumentParser(description=metadata(__package__)['Summary'])
    parser.add_argument(
        '-v',
        '--verbosity',
        help='Set verbosity level (default: %(default)s)',
        choices=['warning', 'info', 'debug'],
        default='info',
    )
    subparsers = parser.add_subparsers(help='Desired action to perform', dest='command')

    # help
    subparsers.add_parser('help', help='Print this help message')

    # usage
    subparsers.add_parser('usage', help='Print full usage')

    # Create parent subparser for with common arguments
    parent_parser = ArgumentParser(add_help=False, formatter_class=F)
    parent_parser.add_argument('--locale', default='en_US', help='(default: %(default)s)')
    parent_parser.add_argument('--timezone', default='UTC', help='(default: %(default)s)')
    parent_parser.add_argument('--device', default='px_3a', help='(default: %(default)s)')
    parent_parser.add_argument(
        '--delay', default=0.51, help='Delay between every request in seconds (default: %(default)s)', type=float
    )
    parent_parser.add_argument(
        '--threads', default=2, help='Number of parallel workers (default: %(default)s)', type=int
    )

    # Subparsers based on parent

    # charts
    d = 'parallel downloading of all cross category app charts'
    parser_charts = subparsers.add_parser('charts', parents=[parent_parser], help=d, description=d, formatter_class=F)

    parser_charts.add_argument('--output', help='name of the output file (default: %(default)s)', default='charts.json')

    # search
    d = 'parallel searching of apps via search terms'
    parser_search = subparsers.add_parser('search', parents=[parent_parser], help=d, description=d, formatter_class=F)

    parser_search.add_argument(
        '--output', help='name of the output file (default: %(default)s)', default='ids_search.json'
    )
    parser_search.add_argument(
        '--length', default=2, help='length of strings to search (default: %(default)s)', type=int
    )

    # related
    d = 'parallel searching of apps via related apps'
    parser_related = subparsers.add_parser('related', parents=[parent_parser], help=d, description=d, formatter_class=F)

    parser_related.add_argument('input', help='name of the input file (default: %(default)s)', default='charts.json')
    parser_related.add_argument(
        '--output', help='base name of the output files (default: %(default)s)', default='ids_related'
    )
    parser_related.add_argument('--level', default=3, help='How deep to crawl (default: %(default)s)', type=int)

    # metadata
    d = 'parallel scraping of app metadata'
    parser_metadata = subparsers.add_parser(
        'metadata', parents=[parent_parser], help=d, description=d, formatter_class=F
    )

    parser_metadata.add_argument('input', help='name of the input file (json)')
    parser_metadata.add_argument(
        '--output', help='directory name of the output files (default: %(default)s)', default='out_metadata'
    )
    # packages
    d = 'parallel downloading app packages'
    parser_packages = subparsers.add_parser(
        'packages', parents=[parent_parser], help=d, description=d, formatter_class=F
    )

    parser_packages.add_argument('input', help='name of the input file (json)')
    parser_packages.add_argument(
        '--output', help='directory name of the output files (default: %(default)s)', default='out_packages'
    )
    parser_packages.add_argument(
        '--expansions', help='also download expansion files (default: %(default)s)', action='store_true'
    )
    parser_packages.add_argument(
        '--splits', help='also download split files (default: %(default)s)', action='store_true'
    )

    args = parser.parse_args()

    if args.command == 'help' or args.command is None:
        parser.print_help()
        exit()

    if args.command == 'usage':
        parser.print_help()
        print('\n\nAll commands in detail:')

        parentsubparsers = [parser_charts, parser_search, parser_related, parser_metadata, parser_packages]
        commonargs = ['-h, --help', '--locale', '--timezone', '--device', '--delay', '--threads']
        parentsubparsers_str = []
        for p in parentsubparsers:
            parentsubparsers_str.append(p.prog.split(' ')[1])

        print(f'\n\nCommon optional arguments for {", ".join(parentsubparsers_str)}:')
        print('\n'.join(parent_parser.format_help().splitlines()[4:]))
        for p, p_str in zip(parentsubparsers, parentsubparsers_str):
            h = p.format_help()
            hn = ''
            for line in h.splitlines():
                add = True
                for arg in commonargs:
                    if line.lstrip().startswith(arg):
                        add = False
                if add:
                    hn += line + '\n'
            hn = hn.rstrip('optional arguments:\n')
            print(f"\n\n{p_str}:\n{hn}")
        exit()

    if args.command == 'charts':
        c = Charts(
            locale=args.locale, timezone=args.timezone, device=args.device, delay=args.delay, log_level=args.verbosity
        )
        c.getCharts(args.output)
    elif args.command == 'search':
        s = Search(
            locale=args.locale, timezone=args.timezone, device=args.device, delay=args.delay, log_level=args.verbosity
        )
        s.getSearch(args.output, args.threads, args.length)
    elif args.command == 'related':
        r = Related(
            locale=args.locale, timezone=args.timezone, device=args.device, delay=args.delay, log_level=args.verbosity
        )
        r.getRelated(args.input, args.output, until_level=args.level, threads=args.threads)
    elif args.command == 'metadata':
        m = Metadata(
            locale=args.locale, timezone=args.timezone, device=args.device, delay=args.delay, log_level=args.verbosity
        )
        m.getMetadata(args.input, args.output, args.threads)
    elif args.command == 'packages':
        p = Packages(
            locale=args.locale, timezone=args.timezone, device=args.device, delay=args.delay, log_level=args.verbosity
        )
        p.getPackages(args.input, args.output, args.threads, args.expansions, args.splits)

    else:
        parser.print_help()
        exit()
