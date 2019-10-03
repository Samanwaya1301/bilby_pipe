#!/usr/bin/env python
"""
Module containing the tools for creating injection files
"""
from __future__ import division, print_function

import argparse
import sys
import json
import os

import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("agg")  # noqa
import bilby

from .utils import (
    parse_args,
    logger,
    BilbyPipeError,
    check_directory_exists_and_if_not_mkdir,
)
from .input import Input


class BilbyPipeCreateInjectionsError(BilbyPipeError):
    def __init__(self, message):
        super().__init__(message)


def create_parser():
    """ Generate a parser for the create_injections.py script

    Additional options can be added to the returned parser beforing calling
    `parser.parse_args` to generate the arguments`

    Returns
    -------
    parser: BilbyArgParser
        A parser with all the default options already added

    """
    parser = argparse.ArgumentParser()
    parser.add_arg(
        "prior_file",
        type=str,
        default=None,
        help="The prior file from which to generate injections",
    )
    parser.add("-f", "--filename", type=str, default="injection")
    parser.add_arg(
        "-e",
        "--extension",
        type=str,
        default="dat",
        choices=["json", "dat"],
        help="Prior file format",
    )
    parser.add_arg(
        "-n",
        "--n-injection",
        type=int,
        help="The number of injections to generate",
        required=True,
    )
    parser.add_arg(
        "-t",
        "--trigger-time",
        type=int,
        default=0,
        help=(
            "The trigger time to use for setting a geocent_time prior "
            "(default=0). Ignored if a geocent_time prior exists in the "
            "prior_file"
        ),
    )
    parser.add(
        "--deltaT",
        type=float,
        default=0.2,
        help=(
            "The symmetric width (in s) around the trigger time to"
            " search over the coalesence time. Ignored if a geocent_time prior"
            " exists in the prior_file"
        ),
    )
    parser.add(
        "-s",
        "--generation-seed",
        default=None,
        type=int,
        help="Random seed used during data generation",
    )
    parser.add(
        "--default-prior",
        default="BBHPriorDict",
        type=str,
        help="The name of the prior set to base the prior on. Can be one of"
        "[PriorDict, BBHPriorDict, BNSPriorDict, CalibrationPriorDict]",
    )
    return parser


class PriorFileInput(Input):
    """ An object to hold inputs to create_injection for consistency"""

    def __init__(self, prior_file, default_prior, trigger_time, deltaT):
        self.prior_file = prior_file
        self.default_prior = default_prior
        self.trigger_time = trigger_time
        self.deltaT = deltaT


def get_full_path(filename, extension):
    ext_in_filename = os.path.splitext(filename)[1].lstrip(".")
    if ext_in_filename == "":
        path = "{}.{}".format(filename, extension)
    elif ext_in_filename == extension:
        path = filename
    else:
        logger.debug("Overwriting given extension name")
        path = filename
        extension = ext_in_filename
    return path, extension


def create_injection_file(
    filename,
    prior_file,
    n_injection,
    trigger_time=None,
    deltaT=0.2,
    generation_seed=None,
    extension="dat",
    default_prior="BBHPriorDict",
):
    path, extension = get_full_path(filename, extension)
    outdir = os.path.dirname(path)
    if outdir != "":
        check_directory_exists_and_if_not_mkdir(outdir)

    prior_file_input = PriorFileInput(
        prior_file=prior_file,
        default_prior=default_prior,
        trigger_time=trigger_time,
        deltaT=deltaT,
    )
    prior_file = prior_file_input.prior_file

    if prior_file is None:
        raise BilbyPipeCreateInjectionsError("prior_file is None")

    np.random.seed(generation_seed)
    logger.info("Setting generation seed={}".format(generation_seed))

    if isinstance(n_injection, int) is False or n_injection < 1:
        raise BilbyPipeCreateInjectionsError("n_injection must bea positive integer")

    logger.info(
        "Generating injection file {} from prior={}, n_injection={}".format(
            path, prior_file, n_injection
        )
    )

    priors = prior_file_input.priors
    injection_values = pd.DataFrame.from_dict(priors.sample(n_injection))

    if extension == "json":
        injections = dict(injections=injection_values)
        with open(path, "w") as file:
            json.dump(
                injections, file, indent=2, cls=bilby.core.result.BilbyJsonEncoder
            )
    elif extension == "dat":
        injection_values.to_csv(path, index=False, header=True, sep=" ")
    else:
        raise BilbyPipeCreateInjectionsError(
            "Extension {} not implemented".format(extension)
        )
    logger.info("Created injection file {}".format(path))


def main():
    args, unknown_args = parse_args(sys.argv[1:], create_parser())
    create_injection_file(
        filename=args.filename,
        prior_file=args.prior_file,
        n_injection=args.n_injection,
        trigger_time=args.trigger_time,
        deltaT=args.deltaT,
        generation_seed=args.generation_seed,
        extension=args.extension,
    )
