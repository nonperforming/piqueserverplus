from __future__ import print_function, unicode_literals

import os
import shutil
import sys
import argparse
import six.moves.urllib as urllib
import gzip
import json

from piqueserver.config import (config, TOML_FORMAT, JSON_FORMAT,
            PKG_NAME, MAXMIND_DOWNLOAD, SUPPORTED_PYTHONS, config_dir
        )

def get_git_rev():
    if not os.path.exists(".git"):
        return 'snapshot'

    from distutils.spawn import find_executable
    if find_executable("git") is None:
        return 'gitless'

    import subprocess
    pipe = subprocess.Popen(
        ["git", "rev-parse", "HEAD"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ret = pipe.stdout.read()[:40]
    if not ret:
        return 'unknown'
    return ret


def copy_config():
    config_source = os.path.dirname(os.path.abspath(__file__)) + '/config'
    print('Attempting to copy example config to %s (origin: %s).' %
          (config_dir.get(), config_source))
    try:
        shutil.copytree(config_source, config_dir.get())
    except Exception as e:  # pylint: disable=broad-except
        print(e)
        sys.exit(1)

    print('Complete! Please edit the files in %s to your liking.' %
            config_dir.get())


def update_geoip(target_dir):
    working_directory = os.path.join(target_dir, 'data/')
    zipped_path = os.path.join(
        working_directory, os.path.basename(MAXMIND_DOWNLOAD))
    extracted_path = os.path.join(working_directory, 'GeoLiteCity.dat')

    if not os.path.exists(target_dir):
        print('Configuration directory does not exist')
        sys.exit(1)

    if not os.path.exists(working_directory):
        os.makedirs(working_directory)

    print('Downloading %s' % MAXMIND_DOWNLOAD)

    urllib.request.urlretrieve(MAXMIND_DOWNLOAD, zipped_path)

    print('Download Complete')
    print('Unpacking...')

    with gzip.open(zipped_path, 'rb') as gz:
        d = gz.read()
        with open(extracted_path, 'wb') as ex:
            ex.write(d)

    print('Unpacking Complete')
    print('Cleaning up...')

    os.remove(zipped_path)


def run_server():
    from piqueserver import server
    server.run()


def main():
    if (sys.version_info.major, sys.version_info.minor) not in SUPPORTED_PYTHONS:
        print('Warning: you are running on an unsupported Python version.\n'
              'The server may not run correctly.\n'
              'Please see https://github.com/piqueserver/piqueserver/wiki/Supported-Environments for more information.')
    elif sys.version_info.major == 2:
        print('You are running piqueserver on Python 2.\n'
              'This will be deprecated soon and it is recommended to upgrade to Python 3.\n'
              'Please see https://github.com/piqueserver/piqueserver/wiki/Supported-Environments for more information.')

    description = '%s is an open-source Python server implementation ' \
                  'for the voxel-based game "Ace of Spades".' % PKG_NAME
    arg_parser = argparse.ArgumentParser(prog=PKG_NAME,
                                         description=description)

    arg_parser.add_argument('-c', '--config-file', default=None,
                            help='specify the config file - '
                                 'default is "config.json" in the config dir')

    arg_parser.add_argument('-j', '--json-parameters',
                            help='add extra json parameters '
                                 '(overrides the ones present in the config file)')

    arg_parser.add_argument('-d', '--config-dir', default=config_dir,
                            help='specify the directory which contains '
                                 'maps, scripts, etc (in correctly named '
                                 'subdirs) - default is %s' % config_dir)

    arg_parser.add_argument('--copy-config', action='store_true',
                            help='copies the default/example config dir to '
                            'its default location or as specified by "-d"')

    arg_parser.add_argument('--update-geoip', action='store_true',
                            help='download the latest geoip database')

    args = arg_parser.parse_args()

    # override the config_dir from cli args
    config_dir.set(args.config_dir)

    # find and load the config
    format_ = None
    if args.config_file is None:
        for format__, ext in ((TOML_FORMAT, 'toml'), (JSON_FORMAT, 'json')):
            config_file = os.path.join(config_dir.get(), 'config.{}'.format(ext))
            format_ = format__
            if os.path.exists(config_file):
                break
    else:
        config_file = args.config_file
        ext = os.path.splitext(config_file)[1]
        if ext == 'json':
            format_ = JSON_FORMAT
        elif ext == 'toml':
            format_ = TOML_FORMAT
        else:
            raise ValueError('Unsupported config file format! Must have json or toml extension.')

    print('Loading config from {!r}'.format(config_file))
    with open(config_file) as fobj:
        config.load_from_file(fobj, format_=format_)

    # update config with cli overrides
    if args.json_parameters:
        config.update_from_dict(json.loads(args.json_parameters))

    run = True

    # copy config and update geoip can happen at the same time
    # note that sys.exit is called from either of these functions on failure
    if args.copy_config:
        copy_config()
        run = False
    if args.update_geoip:
        update_geoip(config_dir.get())
        run = False

    # only run the server if other tasks weren't performed
    if run:
        run_server()

if __name__ == "__main__":
    main()
