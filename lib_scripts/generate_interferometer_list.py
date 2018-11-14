#!/usr/bin/env python
"""
bilby_pipe script to generate the stored interferometer list
"""
from __future__ import division, print_function

import sys

import configargparse
import bilby

from bilby_pipe.utils import logger


class GenerateInterferometerList(object):
    """ Handles user-input and creation of intermediate ifo list

    Parameters
    ----------
    parser: configargparse.ArgParser, optional
        The parser containing the command line / ini file inputs
    args_list: list, optional
        A list of the arguments to parse. Defauts to `sys.argv[1:]`

    """
    def __init__(self, parser, args_list=None):
        if args_list is None:
            args_list = sys.argv[1:]

        args, unknown_args = parser.parse_known_args(args_list)
        self.meta_data = dict(command_line_args=args,
                              unknown_command_line_args=unknown_args)
        logger.info('Command line arguments: {}'.format(args))

        self.ini = args.ini
        self.cluster = args.cluster
        self.process = args.process
        self.detectors = args.detectors
        self.calibration = args.calibration
        self.channel_names = args.channel_names
        self.duration = args.duration
        self.trigger_time = args.trigger_time
        self.sampling_frequency = args.sampling_frequency
        self.psd_duration = args.psd_duration
        self.minimum_frequency = args.minimum_frequency
        self.outdir = args.outdir
        self.label = args.label

        self.gracedb = args.gracedb

    @staticmethod
    def _convert_string_to_list(string):
        """ Converts various strings to a list """
        string = string.replace(',', ' ')
        string = string.replace('[', '')
        string = string.replace(']', '')
        string = string.replace('"', '')
        string = string.replace("'", '')
        string_list = string.split()
        return string_list

    @property
    def detectors(self):
        """ A list of the detectors to search over, e.g., ['H1', 'L1'] """
        return self._detectors

    @detectors.setter
    def detectors(self, detectors):
        """ Handles various types of user input """
        if isinstance(detectors, list):
            if len(detectors) == 1:
                det_list = self._convert_string_to_list(detectors[0])
            else:
                det_list = detectors
        else:
            raise ValueError('Input `detectors` = {} not understood'
                             .format(detectors))

        det_list.sort()
        det_list = [det.upper() for det in det_list]
        self._detectors = det_list

    @property
    def gracedb(self):
        """ The gracedb of the candidate """
        return self._gracedb

    @gracedb.setter
    def gracedb(self, gracedb):
        """ Set the gracedb ID

        At setting, will load the json candidate data and path to the frame
        cache file.
        """
        candidate, frame_caches = bilby.gw.utils.get_gracedb(
            gracedb, self.outdir, self.duration, self.calibration,
            self.detectors)
        self.meta_data['gracedb_candidate'] = candidate
        self._gracedb = gracedb
        self.trigger_time = self.candidate['gpstime']
        self.frame_caches = frame_caches

    @property
    def frame_caches(self):
        """ A list of paths to the frame-cache files """
        try:
            return self._frame_caches
        except AttributeError:
            raise ValueError("frame_caches list is unset")

    @frame_caches.setter
    def frame_caches(self, frame_caches):
        if isinstance(frame_caches, list):
            interferometers = bilby.gw.detector.InterferometerList([])
            if self.channel_names is None:
                channel_names_none_list = [None] * len(self.frame_caches)
            for cache_file, channel_name in zip(self.frame_caches, channel_names_none_list):
                interferometers.append(
                    bilby.gw.detector.load_data_from_cache_file(
                        cache_file, self.trigger_time, self.duration,
                        self.psd_duration, channel_name))
                self.interferometers = interferometers

        else:
            raise ValueError("frame_caches list must be a list")

    @property
    def interferometers(self):
        """ A bilby.gw.detector.InterferometerList """
        try:
            return self._interferometers
        except AttributeError:
            raise ValueError("interferometers unset, did you provide a set-data method?")

    @interferometers.setter
    def interferometers(self, interferometers):
        self._interferometers = interferometers


def create_generate_interferometer_list_parser():
    """ Generate a parser for the generate_interferometer_list.py script

    Additional options can be added to the returned parser beforing calling
    `parser.parse_args` to generate the arguments`

    Returns
    -------
    parser: configargparse.ArgParser
        A parser with all the default options already added

    """
    parser = configargparse.ArgParser(ignore_unknown_config_file_keys=True)
    parser.add('--ini', is_config_file=True, help='The ini-style config file')
    parser.add('--cluster', type=int,
               help='The condor cluster ID', default=None)
    parser.add('--process', type=int,
               help='The condor process ID', default=None)
    parser.add(
        '--detectors', action='append',
        help=('The names of detectors to include. If given in the ini file, '
              'multiple detectors are specified by `detectors=[H1, L1]`. If '
              'given at the command line, as `--detectors H1 --detectors L1`'))
    parser.add('--calibration', type=int, default=2,
               help='Which calibration to use')
    parser.add('--duration', type=int, default=4,
               help='The duration of data around the event to use')
    parser.add("--trigger-time", default=None, type=float,
               help="The trigger time")
    parser.add("--sampling-frequency", default=4096, type=int)
    parser.add("--channel-names", default=None, nargs="*",
               help="Channel names to use, if not provided known "
               "channel names will be tested.")
    parser.add('--psd-duration', default=500, type=int,
               help='Time used to generate the PSD, default is 500.')
    parser.add('--minimum-frequency', default=20, type=float)
    parser.add('--outdir', default='outdir', help='Output directory')
    parser.add('--label', default='label', help='Output label')

    # Method specific options below here
    parser.add('--gracedb', type=str, help='Gracedb UID', default=None)
    return parser


if __name__ == '__main__':
    parser = create_generate_interferometer_list_parser()
    data = GenerateInterferometerList(parser)
    data.interferometers.to_hdf5()
