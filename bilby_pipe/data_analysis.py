#!/usr/bin/env python
"""
Script to analyse the stored data
"""
from __future__ import division, print_function

import sys
import os

import numpy as np
import configargparse
import bilby

from bilby_pipe.utils import logger
from bilby_pipe import webpages
from bilby_pipe.main import Input, DataDump, parse_args


def create_parser():
    """ Generate a parser for the data_analysis.py script

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
        help=('The names of detectors to analyse. If given in the ini file, '
              'multiple detectors are specified by `detectors=[H1, L1]`. If '
              'given at the command line, as `--detectors H1 --detectors L1`'))
    parser.add("--prior-file", default=None, help="prior file")
    parser.add("--deltaT", type=float, default=0.1,
               help=("The symmetric width (in s) around the trigger time to"
                     " search over the coalesence time"))
    parser.add('--reference-frequency', default=20, type=float,
               help="The reference frequency")
    parser.add('--waveform-approximant', default='IMRPhenomPv2', type=str,
               help="Name of the waveform approximant")
    parser.add(
        '--distance-marginalization', action='store_true', default=False,
        help='If true, use a distance-marginalized likelihood')
    parser.add(
        '--phase-marginalization', action='store_true', default=False,
        help='If true, use a phase-marginalized likelihood')
    parser.add(
        '--time-marginalization', action='store_true', default=False,
        help='If true, use a time-marginalized likelihood')
    parser.add('--sampler', default=None)
    parser.add('--sampler-kwargs', default=None)
    parser.add('--outdir', default='outdir', help='Output directory')
    parser.add('--label', default='label', help='Output label')
    parser.add('--sampling-seed', default=None, type=int, help='Random sampling seed')
    return parser


class DataAnalysisInput(Input):
    """ Handles user-input and analysis of intermediate ifo list

    Parameters
    ----------
    parser: configargparse.ArgParser, optional
        The parser containing the command line / ini file inputs
    args_list: list, optional
        A list of the arguments to parse. Defauts to `sys.argv[1:]`

    """

    def __init__(self, args, unknown_args):
        logger.info('Command line arguments: {}'.format(args))

        self.ini = args.ini
        self.cluster = args.cluster
        self.process = args.process
        self.detectors = args.detectors
        self.prior_file = args.prior_file
        self.deltaT = args.deltaT
        self.reference_frequency = args.reference_frequency
        self.waveform_approximant = args.waveform_approximant
        self.distance_marginalization = args.distance_marginalization
        self.phase_marginalization = args.phase_marginalization
        self.time_marginalization = args.time_marginalization
        self.sampling_seed = args.sampling_seed
        self.sampler = args.sampler
        self.sampler_kwargs = args.sampler_kwargs
        self.outdir = args.outdir
        self.label = args.label

    @property
    def reference_frequency(self):
        return self._reference_frequency

    @reference_frequency.setter
    def reference_frequency(self, reference_frequency):
        self._reference_frequency = float(reference_frequency)

    @property
    def sampling_seed(self):
        return self._samplng_seed

    @sampling_seed.setter
    def sampling_seed(self, sampling_seed):
        if sampling_seed is None:
            sampling_seed = np.random.randint(1, 1e6)
        self._samplng_seed = sampling_seed
        np.random.seed(sampling_seed)
        logger.info('Sampling seed set to {}'.format(sampling_seed))

    @property
    def sampler_kwargs(self):
        if hasattr(self, '_sampler_kwargs'):
            return self._sampler_kwargs
        else:
            return None

    @sampler_kwargs.setter
    def sampler_kwargs(self, sampler_kwargs):
        if sampler_kwargs is not None:
            try:
                self._sampler_kwargs = eval(sampler_kwargs)
            except (NameError, TypeError) as e:
                raise ValueError(
                    "Error {}. Unable to parse sampler_kwargs: {}"
                    .format(e, sampler_kwargs))
        else:
            self._sampler_kwargs = None

    @property
    def interferometers(self):
        return self.data_dump.interferometers

    @property
    def meta_data(self):
        return self.data_dump.meta_data

    @property
    def trigger_time(self):
        return self.data_dump.trigger_time

    @property
    def data_dump(self):
        try:
            return self._data_dump
        except AttributeError:
            filename = os.path.join(self.outdir, self.label + '_data_dump.h5')
            self._data_dump = DataDump.from_hdf5(filename)
            return self._data_dump

    @property
    def run_label(self):
        label = '{}_{}_{}'.format(
            self.label, ''.join(self.detectors), self.sampler)
        return label

    @property
    def priors(self):
        priors = bilby.gw.prior.BBHPriorSet(
            filename=self.prior_file)
        priors['geocent_time'] = bilby.core.prior.Uniform(
            minimum=self.trigger_time - self.deltaT / 2,
            maximum=self.trigger_time + self.deltaT / 2,
            name='geocent_time', latex_label='$t_c$', unit='$s$')
        return priors

    @property
    def parameter_conversion(self):
        return bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters

    @property
    def waveform_generator(self):
        waveform_generator = bilby.gw.WaveformGenerator(
            sampling_frequency=self.interferometers.sampling_frequency,
            duration=self.interferometers.duration,
            frequency_domain_source_model=self.frequency_domain_source_model,
            parameter_conversion=self.parameter_conversion,
            waveform_arguments=self.waveform_arguments)
        return waveform_generator

    @property
    def waveform_arguments(self):
        return dict(
            reference_frequency=self.reference_frequency,
            waveform_approximant=self.waveform_approximant,
            minimum_frequency=self.interferometers[0].minimum_frequency)  # FIXME

    @property
    def likelihood(self):
        return bilby.gw.likelihood.GravitationalWaveTransient(
            interferometers=self.interferometers,
            waveform_generator=self.waveform_generator, prior=self.priors,
            phase_marginalization=self.phase_marginalization,
            distance_marginalization=self.distance_marginalization,
            time_marginalization=self.time_marginalization)

    @property
    def frequency_domain_source_model(self):
        return bilby.gw.source.lal_binary_black_hole

    def run_sampler(self):
        self.result = bilby.run_sampler(
            likelihood=self.likelihood, priors=self.priors,
            sampler=self.sampler, label=self.run_label, outdir=self.outdir,
            conversion_function=bilby.gw.conversion.generate_all_bbh_parameters,
            **self.sampler_kwargs)


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_parser())
    analysis = DataAnalysisInput(args, unknown_args)
    analysis.run_sampler()
    webpages.create_run_output(analysis.result)