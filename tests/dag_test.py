import os
import unittest
from argparse import Namespace
import copy

import bilby_pipe


class TestDag(unittest.TestCase):

    def setUp(self):
        self.directory = os.path.abspath(os.path.dirname(__file__))
        self.test_args = Namespace(
            ini='file.ini', submit=False, outdir='outdir', label='label',
            accounting='accounting.group', include_detectors='H1',
            coherence_test=False, executable='bbh_from_gracedb.py',
            exe_help=False, X509=os.path.join(self.directory, 'X509.txt'),
            sampler=['nestle'])
        self.test_unknown_args = ['--argument', 'value']
        self.inputs = bilby_pipe.Input(self.test_args, self.test_unknown_args)

    def tearDown(self):
        del self.test_args
        del self.inputs

    def test_job_logs(self):
        dag = bilby_pipe.Dag(self.inputs, job_logs='test')
        self.assertEqual(dag.job_logs, 'test')

    def test_jobs_creation(self):
        test_args = copy.copy(self.test_args)
        test_args.include_detectors = 'H1 L1'
        test_args.coherence_test = True
        inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
        dag = bilby_pipe.Dag(inputs)
        expected_jobs = [dict(detectors=['H1', 'L1'], sampler='nestle'),
                         dict(detectors=['H1'], sampler='nestle'),
                         dict(detectors=['L1'], sampler='nestle')]
        self.assertEqual(dag.jobs_inputs, expected_jobs)

    # def test_build_submit(self):
    #     test_args = copy.copy(self.test_args)
    #     test_args.submit = True
    #     inputs = bilby_pipe.Input(test_args, self.test_unknown_args)
    #     dag = bilby_pipe.Dag(inputs)
    #     dag.build_submit()


if __name__ == '__main__':
    unittest.main()
