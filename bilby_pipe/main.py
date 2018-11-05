#!/usr/bin/env python
"""
"""
import os
import sys
import shutil
import itertools

import configargparse
import pycondor

from .utils import logger
from . import utils
from . import webpages


class Input(object):
    def __init__(self, args, unknown_args):
        """ An object to hold all the inputs to bilby_pipe """
        logger.debug('Creating new Input object')

        self.known_detectors = ['H1', 'L1', 'V1']
        logger.debug('Known detector list = {}'.format(self.known_detectors))
        logger.debug('Input args = {}'.format(args))
        logger.debug('Input unknown_args = {}'.format(unknown_args))

        self.unknown_args = unknown_args
        self.ini = args.ini
        self.submit = args.submit
        self.outdir = args.outdir
        self.label = args.label
        self.queue = args.queue
        self.create_summary = args.create_summary
        self.accounting = args.accounting
        self.sampler = args.sampler
        self.include_detectors = args.include_detectors
        self.coherence_test = args.coherence_test
        self.executable = args.executable
        self.x509userproxy = args.X509
        if args.exe_help:
            self.executable_help()

        self.meta_keys = ['label', 'outdir', 'ini', 'executable',
                          'include_detectors', 'coherence_test',
                          'sampler', 'accounting']

    @property
    def include_detectors(self):
        """ A list of the detectors to include, e.g., ['H1', 'L1'] """
        return self._include_detectors

    @include_detectors.setter
    def include_detectors(self, include_detectors):
        if isinstance(include_detectors, str):
            det_list = self._split_string_by_space(include_detectors)
        elif isinstance(include_detectors, list):
            if len(include_detectors) == 1:
                det_list = self._split_string_by_space(include_detectors[0])
            else:
                det_list = include_detectors
        else:
            raise ValueError('Input `include_detectors` = {} not understood'
                             .format(include_detectors))

        det_list.sort()
        det_list = [det.upper() for det in det_list]

        for element in det_list:
            if element not in self.known_detectors:
                raise ValueError(
                    'include_detectors contains "{}" not in the known '
                    'detectors list: {} '.format(
                        element, self.known_detectors))
        self._include_detectors = det_list

    @staticmethod
    def _split_string_by_space(string):
        """ Converts "H1 L1" to ["H1", "L1"] """
        return string.split(' ')

    @property
    def outdir(self):
        return self._outdir

    @outdir.setter
    def outdir(self, outdir):
        utils.check_directory_exists_and_if_not_mkdir(outdir)
        self._outdir = os.path.abspath(outdir)

    @property
    def executable(self):
        return self._executable

    @executable.setter
    def executable(self, executable):
        if os.path.isfile(executable):
            self._executable = executable
        else:
            executable_library = 'lib_scripts'
            executable_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                executable_library,
                executable)
            if os.path.isfile(executable_path):
                self._executable = executable_path
            elif os.path.isfile(executable_path + '.py'):
                self._executable = executable_path + '.py'
            else:
                raise ValueError('Unable to identify executable')

    def executable_help(self):
        logger.info('Printing help message for given executable')
        os.system('{} --help'.format(self.executable))
        sys.exit()

    @property
    def x509userproxy(self):
        try:
            return self._x509userproxy
        except AttributeError:
            raise ValueError(
                "The X509 user proxy has not been correctly set, please check"
                " the logs")

    @x509userproxy.setter
    def x509userproxy(self, x509userproxy):
        if x509userproxy is None:
            cert_alias = 'X509_USER_PROXY'
            try:
                cert_path = os.environ[cert_alias]
                new_cert_path = os.path.join(
                    self.outdir, '.' + os.path.basename(cert_path))
                shutil.copyfile(cert_path, new_cert_path)
                self._x509userproxy = new_cert_path
            except FileNotFoundError:
                logger.warning(
                    "Environment variable X509_USER_PROXY does not point to a"
                    " file. Try running $ligo-proxy-init albert.einstein")
            except KeyError:
                logger.warning(
                    "Environment variable X509_USER_PROXY not set"
                    " Try running $ligo-proxy-init albert.einstein")
                self._x509userproxy = None
        elif os.path.isfile(x509userproxy):
            self._x509userproxy = x509userproxy
        else:
            raise ValueError('Input X509 not a file or not understood')


class Dag(object):
    def __init__(self, inputs, request_memory=None, request_disk=None,
                 request_cpus=None, getenv=True, universe='vanilla',
                 initialdir=None, notification='never', requirements=None,
                 retry=None, verbose=0):
        """ A class to handle the creation and building of a DAG

        Parameters
        ----------
        inputs: bilby_pipe.Input
            An object holding the inputs built from the command-line/ini

        Parameters pass to PyCondor
        ---------------------------
        request_memory : str or None, optional
            Memory request to be included in submit file.
            request_disk : str or None, optional
            Disk request to be included in submit file.
        request_cpus : int or None, optional
            Number of CPUs to request in submit file.
        getenv : bool or None, optional
            Whether or not to use the current environment settings when running
            the job (default is None).
        universe : str or None, optional
            Universe execution environment to be specified in submit file
            (default is None).
        initialdir : str or None, optional
            Initial directory for relative paths (defaults to the directory was
            the job was submitted from).
        notification : str or None, optional
            E-mail notification preference (default is None).
        requirements : str or None, optional
            Additional requirements to be included in ClassAd.
        extra_lines : list or None, optional
            List of additional lines to be added to submit file.
        dag : Dagman, optional
            If specified, Job will be added to dag (default is None).
        arguments : str or iterable, optional
            Arguments with which to initialize the Job list of arguments
            (default is None).
        retry : int or None, optional
            Option to specify the number of retries for all Job arguments. This
            can be superseded for arguments added via the add_arg() method.
            Note: this feature is only available to Jobs that are submitted via
            a Dagman (default is None; no retries).
        verbose : int, optional
            Level of logging verbosity option are 0-warning, 1-info,
            2-debugging (default is 0).

        Note, the "Parameters passed to pycondor" are passed directly to
        `pycondor.Job()`. Documentation for these is taken verbatim from the
        API available at https://jrbourbeau.github.io/pycondor/api.html

        """
        self.request_memory = request_memory
        self.request_disk = request_disk
        self.request_cpus = request_disk
        self.getenv = getenv
        self.universe = universe
        self.initialdir = initialdir
        self.notification = notification
        self.requirements = requirements
        self.retry = retry
        self.verbose = verbose
        self.inputs = inputs

        self.dag = pycondor.Dagman(
            name='main_' + inputs.label,
            submit=self.submit_directory)
        self.jobs = []
        self.results_pages = dict()
        self.create_jobs()
        self.create_postprocessing_jobs()
        self.build_submit()

    @property
    def submit_directory(self):
        return os.path.join(self.inputs.outdir, 'submit')

    def create_jobs(self):
        """ Create all the condor jobs and add them to the dag """
        for job_input in self.jobs_inputs:
            self.jobs.append(self._create_job(**job_input))

    @property
    def jobs_inputs(self):
        """ A list of dictionaries enumerating all the main jobs to generate

        This contains the logic of generating multiple parallel running jobs
        The keys of each dictionary should be the keyword arguments to
        `self._create_jobs()`

        """
        logger.debug("Generating list of jobs")
        detectors_list = []
        detectors_list.append(self.inputs.include_detectors)
        if self.inputs.coherence_test:
            for detector in self.inputs.include_detectors:
                detectors_list.append([detector])

        sampler_list = self.inputs.sampler

        prod_list = itertools.product(detectors_list, sampler_list)
        jobs_inputs = []
        for detectors, sampler in prod_list:
            jobs_inputs.append(dict(detectors=detectors, sampler=sampler))

        logger.debug("List of job inputs = {}".format(jobs_inputs))
        return jobs_inputs

    def _create_job(self, detectors, sampler):
        """ Create a condor job and add it to the dag

        Parameters
        ----------
        detectors: list, str
            A list of the detectors to include, e.g. `['H1', 'L1']`
        sampler: str
            The sampler to use for the job

        """

        if not isinstance(detectors, list):
            raise ValueError("`detectors must be a list")

        job_logs_path = os.path.join(self.inputs.outdir, 'logs')
        error = job_logs_path
        log = job_logs_path
        output = job_logs_path
        submit = self.submit_directory
        extra_lines = 'accounting_group={}'.format(self.inputs.accounting)
        extra_lines += '\nx509userproxy={}'.format(self.inputs.x509userproxy)
        arguments = '--ini {}'.format(self.inputs.ini)
        run_label = '{}_{}_{}'.format(self.inputs.label, ''.join(detectors),
                                      sampler)
        for detector in detectors:
            arguments += ' --detectors {}'.format(detector)
        arguments += ' --sampler {}'.format(sampler)
        arguments += ' --cluster $(Cluster)'
        arguments += ' --process $(Process)'
        arguments += ' ' + ' '.join(self.inputs.unknown_args)
        job = pycondor.Job(
            name=run_label, executable=self.inputs.executable, error=error, log=log,
            output=output, submit=submit, request_memory=self.request_memory,
            request_disk=self.request_disk, request_cpus=self.request_cpus,
            getenv=self.getenv, universe=self.universe,
            initialdir=self.initialdir, notification=self.notification,
            requirements=self.requirements, queue=self.inputs.queue,
            extra_lines=extra_lines, dag=self.dag, arguments=arguments,
            retry=self.retry, verbose=self.verbose)

        logger.debug('Adding job: {}'.format(run_label))
        self.results_pages[run_label] = '{}.html'.format(run_label)
        return job

    def create_postprocessing_jobs(self):
        job_logs_path = os.path.join(self.inputs.outdir, 'logs')
        error = job_logs_path
        log = job_logs_path
        output = job_logs_path
        submit = self.submit_directory
        name = self.inputs.label + '_combine_results'
        extra_lines = 'accounting_group={}'.format(self.inputs.accounting)
        expected_h5_files = ['{}/{}_result.h5'.format(self.inputs.outdir,
                                                      job.name)
                             for job in self.jobs]
        labels = ' '.join(''.join(job['detectors']) for job in self.jobs_inputs)
        arguments = ('-r {} -f {}/{}_corner.png -l {}'
                     .format(' '.join(expected_h5_files), self.inputs.outdir,
                             name, labels))
        executable = '/home/gregory.ashton/anaconda3/bin/bilby_plot'
        post_job = pycondor.Job(
            name=name, executable=executable, extra_lines=extra_lines,
            error=error, log=log, output=output,
            submit=submit, arguments=arguments, dag=self.dag)
        for job in self.jobs:
            post_job.add_parent(job)

    def build_submit(self):
        """ Build the dag, optionally submit them if requested in inputs """
        if self.inputs.submit:
            self.dag.build_submit()
        else:
            self.dag.build()


class JobOutput():
    def __init__(self, directory, name):
        self.directory = directory
        self.name = name

    @property
    def full_corner(self):
        return '{}_corner.png'.format(self.name)


def parse_args(args):
    parser = configargparse.ArgParser(
        usage='Generate submission scripts for the job',
        ignore_unknown_config_file_keys=True, allow_abbrev=False)
    parser.add('ini', type=str, is_config_file=True, help='The ini file')
    parser.add('--submit', action='store_true',
               help='If given, build and submit')
    parser.add('--exe-help', action='store_true',
               help='Print the help function for the executable')
    parser.add('--sampler', nargs='+', default='dynesty',
               help='Sampler to use, or list of sampler to use')
    parser.add('--include-detectors', nargs='+', default=['H1', 'L1'],
               help='The names of detectors to include {H1, L1}')
    parser.add('--coherence-test', action='store_true')
    parser.add('--queue', type=int, default=1)
    parser.add('--label', type=str, default='LABEL',
               help='The output label')
    parser.add('--outdir', type=str, default='bilby_outdir',
               help='The output directory')
    parser.add('--create-summary', action='store_true',
               help='If true, create a summary page')
    parser.add('--accounting', type=str, required=True,
               help='The accounting group to use')
    parser.add('--executable', type=str, required=True,
               help=('Either a path to the executable or the name of '
                     'the executable in the library'))
    parser.add('--X509', type=str, default=None,
               help=('If given, the path to the users X509 certificate file.'
                     'If not given, a copy of the file at the env. variable '
                     '$X509_USER_PROXY will be made in outdir and linked in '
                     'the condor jobs submission'))
    parser.add('-v', '--verbose', action='store_true', help='verbose')
    args, unknown_args = parser.parse_known_args(args)
    return args, unknown_args


def main():
    args, unknown_args = parse_args(sys.argv[1:])
    inputs = Input(args, unknown_args)
    dag = Dag(inputs)
    if inputs.create_summary:
        webpages.create_summary_page(dag)
