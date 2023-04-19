import unittest
from sim_util import get_ground_truth, get_sentinels, prepare_ingress_routers, gt_init, export_sentinels, enhance_sentinels, order_sentinels
from common.ip_conversion import ipv4_to_int
from sim_mirroring import get_mirroring_rules, get_mirrored_packets
from sim_results import get_results_ground_truth, get_results_ground_truth_sampling, get_results_ground_truth_invalidated_sentinels
from sim_pkts import get_pkts, get_pkts_time_slice, get_pkts_efficient, get_sampled_packets_per_router, get_sampled_packets_everflow, get_preprocessed_pkts
# from preprocess_pkt_csv import preprocess
from collections import defaultdict
import os.path
import io


class TestSentinelSearch(unittest.TestCase):
    def setUp(self):
        self.packets = [(ipv4_to_int('1.2.3.0'), '1.2.3.0/24', 1),
                        (ipv4_to_int('1.2.3.1'), '1.2.3.0/24', 2),
                        (ipv4_to_int('10.0.0.1'), '10.0.0.0/24', 1),
                        (ipv4_to_int('10.0.1.1'), '10.0.1.0/24', 2),
                        (ipv4_to_int('20.0.0.1'), '20.0.0.0/24', 1),
                        (ipv4_to_int('20.0.0.2'), '20.0.0.0/24', 1),
                        (ipv4_to_int('128.0.0.1'), '128.0.0.0/24', 3)]

        # search needs one iteration -> finds /17
        self.expected_default = set([('10.0.0.0/24', 1),
                                     ('10.0.1.0/24', 2),
                                     ('20.0.0.0/17', 1),
                                     ('128.0.0.0/17', 3)])

        self.expected_32 = set([('1.2.3.0/32', 1),
                                ('1.2.3.1/32', 2),
                                ('10.0.0.0/24', 1),
                                ('10.0.1.0/24', 2),
                                ('20.0.0.0/17', 1),
                                ('128.0.0.0/17', 3)])

        self.expected_big = set([('10.0.0.0/24', 1),
                                 ('10.0.1.0/24', 2),
                                 ('16.0.0.0/4', 1),
                                 ('128.0.0.0/1', 3)])

    def test_default_s_search(self):
        self.assertCountEqual(get_sentinels(self.packets, 16, 24),
                              self.expected_default)

    def test_32_s_search(self):
        self.assertCountEqual(get_sentinels(self.packets, 16, 32),
                              self.expected_32)

    def test_big_s_search(self):
        self.assertCountEqual(get_sentinels(self.packets, 0, 24),
                              self.expected_big)


class TestGroundTruthData(unittest.TestCase):
    def setUp(self):
        self.packets = [(ipv4_to_int('1.2.3.0'), '1.2.3.0/24', 1),
                        (ipv4_to_int('1.2.3.1'), '1.2.3.0/24', 2),
                        (ipv4_to_int('10.0.0.1'), '10.0.0.0/24', 1),
                        (ipv4_to_int('10.0.1.1'), '10.0.1.0/24', 2),
                        (ipv4_to_int('20.0.0.1'), '20.0.0.0/24', 1),
                        (ipv4_to_int('20.0.0.2'), '20.0.0.0/24', 1),
                        (ipv4_to_int('128.0.0.1'), '128.0.0.0/24', 3)]

        self.expected_gt = defaultdict(gt_init)

        self.expected_gt['1.2.3.0/24']['ingress_router'] = set([1, 2])
        self.expected_gt['10.0.0.0/24']['ingress_router'] = set([1])
        self.expected_gt['10.0.1.0/24']['ingress_router'] = set([2])
        self.expected_gt['20.0.0.0/24']['ingress_router'] = set([1])
        self.expected_gt['128.0.0.0/24']['ingress_router'] = set([3])

        self.expected_gt['1.2.3.0/24']['pkt_count'] = 2
        self.expected_gt['10.0.0.0/24']['pkt_count'] = 1
        self.expected_gt['10.0.1.0/24']['pkt_count'] = 1
        self.expected_gt['20.0.0.0/24']['pkt_count'] = 2
        self.expected_gt['128.0.0.0/24']['pkt_count'] = 1

    def test_ground_truth(self):
        self.assertDictEqual(get_ground_truth(self.packets),
                             self.expected_gt)


class TestMirroring(unittest.TestCase):
    def setUp(self):
        self.pkts_sentinel = [(ipv4_to_int('1.2.3.1'), '1.2.3.0/24', 1),
                              (ipv4_to_int('1.2.4.1'), '1.2.4.0/24', 2),
                              (ipv4_to_int('1.2.5.1'), '1.2.5.0/24', 3)]

        self.pkts_mirror = [(ipv4_to_int('1.2.3.1'), '1.2.3.0/24', 1),
                            (ipv4_to_int('1.2.4.1'), '1.2.4.0/24', 2),
                            (ipv4_to_int('1.2.5.1'), '1.2.5.0/24', 3),
                            (ipv4_to_int('1.2.3.10'), '1.2.3.0/24', 2),
                            (ipv4_to_int('1.2.3.11'), '1.2.3.0/24', 3),
                            (ipv4_to_int('1.2.4.34'), '1.2.4.0/24', 4),
                            (ipv4_to_int('1.2.4.34'), '1.2.4.0/24', 4),
                            (ipv4_to_int('1.2.5.77'), '1.2.5.0/24', 1)]

        self.expected_no_remove = [(ipv4_to_int('1.2.3.10'), '1.2.3.0/24', 2),
                                   (ipv4_to_int('1.2.3.11'), '1.2.3.0/24', 3),
                                   (ipv4_to_int('1.2.4.34'), '1.2.4.0/24', 4),
                                   (ipv4_to_int('1.2.4.34'), '1.2.4.0/24', 4),
                                   (ipv4_to_int('1.2.5.77'), '1.2.5.0/24', 1)]

        self.expected_remove = [(ipv4_to_int('1.2.3.10'), '1.2.3.0/24', 2),
                                (ipv4_to_int('1.2.4.34'), '1.2.4.0/24', 4),
                                (ipv4_to_int('1.2.5.77'), '1.2.5.0/24', 1)]

        self.expected_sentinels = [('1.2.0.0/22', 1),
                                   ('1.2.4.0/24', 2),
                                   ('1.2.5.0/24', 3)]
        self.expected_sentinels.sort()

        self.removed_sentinels_no_remove = list()

        self.removed_sentinels_do_remove = ['1.2.0.0/22',
                                            '1.2.4.0/24',
                                            '1.2.5.0/24']
        self.removed_sentinels_do_remove.sort()

    def test_mirroring_no_remove(self):
        # by setting ordering and top to None, we consider all possible sentinels
        # -> ordering and enhancing functions are checked in dedicated tests
        rules, sentinels = get_mirroring_rules(self.pkts_sentinel, 16, 24, None, None)
        sentinels = list(sentinels)
        sentinels.sort()
        self.assertListEqual(sentinels, self.expected_sentinels)

        mirrored_pkts, removed_sentinels = get_mirrored_packets(rules, self.pkts_mirror, False)
        removed_sentinels = list(removed_sentinels)
        removed_sentinels.sort()
        self.assertListEqual(mirrored_pkts, self.expected_no_remove)
        self.assertListEqual(removed_sentinels, self.removed_sentinels_no_remove)

    def test_mirroring_remove(self):
        rules, sentinels = get_mirroring_rules(self.pkts_sentinel, 16, 24, None, None)
        sentinels = list(sentinels)
        sentinels.sort()
        self.assertListEqual(sentinels, self.expected_sentinels)

        mirrored_pkts, removed_sentinels = get_mirrored_packets(rules, self.pkts_mirror, True)
        removed_sentinels = list(removed_sentinels)
        removed_sentinels.sort()
        self.assertListEqual(mirrored_pkts, self.expected_remove)
        self.assertListEqual(removed_sentinels, self.removed_sentinels_do_remove)


class TestGtResults(unittest.TestCase):
    def setUp(self):
        self.pkts_gt = [(ipv4_to_int('1.2.3.1'), '1.2.3.0/24', 1),
                        (ipv4_to_int('1.2.4.1'), '1.2.4.0/24', 2),
                        (ipv4_to_int('10.0.0.1'), '10.0.0.0/24', 3),
                        (ipv4_to_int('10.0.0.2'), '10.0.0.0/24', 4),
                        (ipv4_to_int('20.0.0.1'), '20.0.0.0/24', 3),
                        (ipv4_to_int('20.0.0.2'), '20.0.0.0/24', 4),
                        (ipv4_to_int('30.0.0.1'), '30.0.0.0/24', 5),
                        (ipv4_to_int('40.0.0.1'), '40.0.0.0/24', 5),
                        (ipv4_to_int('50.0.0.1'), '50.0.0.0/24', 5),
                        (ipv4_to_int('50.0.0.1'), '50.0.0.0/24', 6)]

        self.sentinels = set([('1.2.3.0/24', 1),
                              ('1.2.4.0/24', 1),
                              ('10.0.0.0/24', 4),
                              ('20.0.0.0/24', 1),
                              ('40.0.0.0/23', 5)])

        self.removed_sentinels = set(['10.0.0.0/24',
                                      '40.0.0.0/23'])

        self.expected_final_sentinels = [('1.2.3.0/24', 1),
                                         ('1.2.4.0/24', 1),
                                         ('20.0.0.0/24', 1)]
        self.expected_final_sentinels.sort()

        self.expected_gt_result = [3,  # 1.2.3.0/24, 10.0.0.0/24, 40.0.0.0/23 (1x)
                                   2,  # 1.2.4.0/24, 20.0.0.0/24
                                   1,  # 40.0.0.0/23 (1x)
                                   2,  # 30.0.0.0/24, 50.0.0.0/24
                                   1,  # 10.0.0.0/24
                                   1,  # 50.0.0.0/24
                                   4,  # 4 pkts correct
                                   4,  # 4 pkts correctly inferred
                                   3,  # 3 pkts wrongly inferred
                                   2,  # 2 pkts correctly inferred but no unique ingress
                                   3,  # 3 pkts active in gt data but not covered by sentinel
                                   2,  # 2 pkts active in gt data but not unique ingress and not active in sentinel
                                   4]  # 4 pkts overall with unique /24

        self.expected_gt_result_remove_invalid = [2,  # 1.2.3.0/24, 40.0.0.0/23 (1x)
                                                  0,  # no longer any wrong sentinels
                                                  1,  # 40.0.0.0/23 (1x)
                                                  5,  # 1.2.4.0/24, 10.0.0.0/24, 20.0.0.0/24, 30.0.0.0/24, 50.0.0.0/24
                                                  0,  # no longer any not unique sentinels
                                                  3,  # 10.0.0.0/24, 20.0.0.0/24, 50.0.0.0/24
                                                  2,  # 2 pkts correct
                                                  2,  # 2 pkts correctly inferred
                                                  0,  # 0 pkts wrongly inferred
                                                  0,  # 0 pkts correctly inferred but no unique ingress
                                                  8,  # 8 pkts active in gt data but not covered by sentinel
                                                  6,  # 6 pkts active in gt data but not unique ingress and not active in sentinel
                                                  4]  # 4 pkts overall with unique /24

        self.sampled = [(ipv4_to_int('1.2.3.1'), '1.2.3.0/24', 1),
                        (ipv4_to_int('10.0.0.2'), '10.0.0.0/24', 4),
                        (ipv4_to_int('30.0.0.1'), '30.0.0.0/24', 5),
                        (ipv4_to_int('100.0.0.1'), '100.0.0.0/24', 2)]  # is no longer in gt data

        self.expected_gt_sampling_result = [3,  # 1.2.3.0/24, 10.0.0.0/24, 30.0.0.0/24
                                            1,  # 10.0.0.0/24
                                            4,  # 1.2.4.0/24, 20.0.0.0/24, 40.0.0.0/24, 50.0.0.0/24
                                            2,  # 20.0.0.0/24, 50.0.0.0/24
                                            4,  # 4 pkts correct
                                            2,  # 2 pkts correct not unique
                                            6,  # 6 pkts not covered
                                            4,  # 4 pkts not covered not unique
                                            1]  # 1 /24 prefix is no longer in gt data

        self.expected_gt_mirroring_lost_result = [2,  # 1x 10.0.0.0/24 and 1x 40.0.0.0/23 (as only one is in gt)
                                                  1,  # 10.0.0.0/24
                                                  1,  # 1x 40.0.0.0/23 (here we count the one which is not in gt)
                                                  3,  # 2x 10.0.0.0/24 and 1x 40.0.0.0/23
                                                  2]  # 2x 10.0.0.0/24

    def test_gt_results(self):
        self.assertListEqual(list(get_results_ground_truth(get_ground_truth(self.pkts_gt), self.sentinels)),
                             self.expected_gt_result)

        self.assertListEqual(list(get_results_ground_truth(get_ground_truth(self.pkts_gt), self.sentinels, True)),
                             self.expected_gt_result_remove_invalid)

    def test_gt_results_sampling(self):
        self.assertListEqual(list(get_results_ground_truth_sampling(get_ground_truth(self.pkts_gt), self.sampled)),
                             self.expected_gt_sampling_result)

    def test_gt_results_mirroring_lost(self):
        final_sentinels, lost_results = get_results_ground_truth_invalidated_sentinels(self.sentinels, self.removed_sentinels, get_ground_truth(self.pkts_gt))
        final_sentinels.sort()
        self.assertListEqual(final_sentinels, self.expected_final_sentinels)
        self.assertListEqual(list(lost_results),
                             self.expected_gt_mirroring_lost_result)


class TestGetPkts(unittest.TestCase):
    def setUp(self):
        self.file_name = 'files_for_unittests/default.csv'
        self.file_name_persistent = 'files_for_unittests/default_persistent.csv'
        self.duration_real = 2
        self.duration_pps = 1
        self.pps = 4
        self.border = 8
        self.real_iterations = 3
        self.pps_iterations = 6
        self.pps_iterations_persistent = 2
        self.preprocessed_input = 'files_for_unittests/expected_preprocessed.csv'
        self.preprocessed_input_persistent = 'files_for_unittests/expected_preprocessed_persistent.csv'

        self.expected_pps_real_pkts_old = [
            (ipv4_to_int('10.10.10.10'), '10.10.10.0/24', 1),
            (ipv4_to_int('20.20.20.20'), '20.20.20.0/24', 2),
            (ipv4_to_int('30.30.30.30'), '30.30.30.0/24', 3),
            (ipv4_to_int('40.40.40.40'), '40.40.40.0/24', 4),
            (ipv4_to_int('50.50.50.50'), '50.50.50.0/24', 5),
            (ipv4_to_int('60.60.60.60'), '60.60.60.0/24', 6),
            (ipv4_to_int('70.70.70.70'), '70.70.70.0/24', 7),
            (ipv4_to_int('80.80.80.80'), '80.80.80.0/24', 8),
            # (ipv4_to_int('90.90.90.90'), '90.90.90.0/24',),
            (ipv4_to_int('100.100.100.100'), '100.100.100.0/24', 1),
            (ipv4_to_int('110.110.110.110'), '110.110.110.0/24', 2),
            (ipv4_to_int('120.120.120.120'), '120.120.120.0/24', 8),
            (ipv4_to_int('130.130.130.130'), '130.130.130.0/24', 2),
            (ipv4_to_int('140.140.140.140'), '140.140.140.0/24', 7),
            (ipv4_to_int('150.150.150.150'), '150.150.150.0/24', 7),
            (ipv4_to_int('160.160.160.160'), '160.160.160.0/24', 1),
            (ipv4_to_int('170.170.170.170'), '170.170.170.0/24', 4),
            (ipv4_to_int('180.180.180.180'), '180.180.180.0/24', 2),
            (ipv4_to_int('190.190.190.190'), '190.190.190.0/24', 2),
            (ipv4_to_int('200.200.200.200'), '200.200.200.0/24', 2),
            (ipv4_to_int('210.210.210.210'), '210.210.210.0/24', 2),
            # (ipv4_to_int('220.220.220.220'), '220.220.220.0/24',),
            # (ipv4_to_int('230.230.230.230'), '230.230.230.0/24',),
            (ipv4_to_int('240.240.240.240'), '240.240.240.0/24', 2),
            (ipv4_to_int('250.250.250.250'), '250.250.250.0/24', 2),
            (ipv4_to_int('10.10.10.10'), '10.10.10.0/24', 2)
        ]

        self.expected_pps_real_timestamps_old = [
            float('1521119300.100'),
            float('1521119300.500'),
            float('1521119300.600'),
            float('1521119300.700'),
            float('1521119301.200'),
            float('1521119301.400'),
            float('1521119301.500'),
            float('1521119301.700'),
            # float('1521119302.000'),
            float('1521119302.000'),
            float('1521119302.100'),
            float('1521119302.200'),
            float('1521119302.500'),
            float('1521119302.600'),
            float('1521119302.700'),
            float('1521119302.800'),
            float('1521119302.900'),
            float('1521119303.000'),
            float('1521119303.500'),
            float('1521119304.000'),
            float('1521119304.500'),
            # float('1521119300.000'),
            # float('1521119300.000'),
            float('1521119305.100'),
            float('1521119305.200'),
            float('1521119306.300')
        ]

        self.expected_pps_real_flags_old = [
            True,
            False,
            True,
            False,
            True,
            False,
            False,
            False,
            # True,
            True,
            True,
            True,
            False,
            True,
            False,
            False,
            False,
            False,
            False,
            False,
            False,
            # False,
            # False,
            False,
            True,
            True
        ]

        self.expected_real_timing_old = [
            0,
            9,
            19,
            23,
            23  # the same because of crafted structure of test input csv
        ]

        self.expected_real_pkts_new = [
            self.expected_pps_real_pkts_old[self.expected_real_timing_old[0]:self.expected_real_timing_old[1]],
            self.expected_pps_real_pkts_old[self.expected_real_timing_old[1]:self.expected_real_timing_old[2]],
            self.expected_pps_real_pkts_old[self.expected_real_timing_old[2]:self.expected_real_timing_old[3]],
        ]

        self.expected_real_timestamps_new = [
            self.expected_pps_real_timestamps_old[self.expected_real_timing_old[0]:self.expected_real_timing_old[1]],
            self.expected_pps_real_timestamps_old[self.expected_real_timing_old[1]:self.expected_real_timing_old[2]],
            self.expected_pps_real_timestamps_old[self.expected_real_timing_old[2]:self.expected_real_timing_old[3]],
        ]

        self.expected_real_flags_new = [
            self.expected_pps_real_flags_old[self.expected_real_timing_old[0]:self.expected_real_timing_old[1]],
            self.expected_pps_real_flags_old[self.expected_real_timing_old[1]:self.expected_real_timing_old[2]],
            self.expected_pps_real_flags_old[self.expected_real_timing_old[2]:self.expected_real_timing_old[3]],
        ]

        self.expected_pps_pkts_new = [
            self.expected_pps_real_pkts_old[0:4],
            self.expected_pps_real_pkts_old[4:8],
            self.expected_pps_real_pkts_old[8:12],
            self.expected_pps_real_pkts_old[12:16],
            self.expected_pps_real_pkts_old[16:20],
            self.expected_pps_real_pkts_old[20:],
        ]

        self.expected_pps_timestamps_new = [
            self.expected_pps_real_timestamps_old[0:4],
            self.expected_pps_real_timestamps_old[4:8],
            self.expected_pps_real_timestamps_old[8:12],
            self.expected_pps_real_timestamps_old[12:16],
            self.expected_pps_real_timestamps_old[16:20],
            self.expected_pps_real_timestamps_old[20:],
        ]

        self.expected_pps_flags_new = [
            self.expected_pps_real_flags_old[0:4],
            self.expected_pps_real_flags_old[4:8],
            self.expected_pps_real_flags_old[8:12],
            self.expected_pps_real_flags_old[12:16],
            self.expected_pps_real_flags_old[16:20],
            self.expected_pps_real_flags_old[20:],
        ]

        self.expected_real_per_router = [
            [
                [(168430090, '10.10.10.0/24', 1), (1684300900, '100.100.100.0/24', 1)],
                [(2694881440, '160.160.160.0/24', 1)],
                [],
            ],
            [
                [(336860180, '20.20.20.0/24', 2)],
                [(1852730990, '110.110.110.0/24', 2), (2189591170, '130.130.130.0/24', 2), (3031741620, '180.180.180.0/24', 2), (3200171710, '190.190.190.0/24', 2), (3368601800, '200.200.200.0/24', 2)],
                [(3537031890, '210.210.210.0/24', 2), (4042322160, '240.240.240.0/24', 2), (4210752250, '250.250.250.0/24', 2), (168430090, '10.10.10.0/24', 2)],
            ],
            [
                [(505290270, '30.30.30.0/24', 3)],
                [],
                [],
            ],
            [
                [(673720360, '40.40.40.0/24', 4)],
                [(2863311530, '170.170.170.0/24', 4)],
                [],
            ],
            [
                [(842150450, '50.50.50.0/24', 5)],
                [],
                [],
            ],
            [
                [(1010580540, '60.60.60.0/24', 6)],
                [],
                [],
            ],
            [
                [(1179010630, '70.70.70.0/24', 7)],
                [(2358021260, '140.140.140.0/24', 7), (2526451350, '150.150.150.0/24', 7)],
                [],
            ],
            [
                [(1347440720, '80.80.80.0/24', 8)],
                [(2021161080, '120.120.120.0/24', 8)],
                []],
        ]

        self.expected_real_per_router_flags = [
            [[True, True], [False], [], ],
            [[False], [True, False, False, False, False], [False, False, True, True], ],
            [[True], [], [], ],
            [[False], [False], [], ],
            [[True], [], [], ],
            [[False], [], [], ],
            [[False], [True, False], [], ],
            [[False], [True], []],
        ]

        self.expected_pps_per_router = [
            [[(168430090, '10.10.10.0/24', 1)], [], [(1684300900, '100.100.100.0/24', 1)], [(2694881440, '160.160.160.0/24', 1)], [], [], ],
            [
                [(336860180, '20.20.20.0/24', 2)],
                [],
                [(1852730990, '110.110.110.0/24', 2), (2189591170, '130.130.130.0/24', 2)],
                [],
                [(3031741620, '180.180.180.0/24', 2), (3200171710, '190.190.190.0/24', 2), (3368601800, '200.200.200.0/24', 2), (3537031890, '210.210.210.0/24', 2)],
                [(4042322160, '240.240.240.0/24', 2), (4210752250, '250.250.250.0/24', 2), (168430090, '10.10.10.0/24', 2)], ],
            [[(505290270, '30.30.30.0/24', 3)], [], [], [], [], [], ],
            [[(673720360, '40.40.40.0/24', 4)], [], [], [(2863311530, '170.170.170.0/24', 4)], [], [], ],
            [[], [(842150450, '50.50.50.0/24', 5)], [], [], [], [], ],
            [[], [(1010580540, '60.60.60.0/24', 6)], [], [], [], [], ],
            [[], [(1179010630, '70.70.70.0/24', 7)], [], [(2358021260, '140.140.140.0/24', 7), (2526451350, '150.150.150.0/24', 7)], [], [], ],
            [[], [(1347440720, '80.80.80.0/24', 8)], [(2021161080, '120.120.120.0/24', 8)], [], [], [], ],
        ]

        self.expected_pps_per_router_flags = [
           [[True], [], [True], [False], [], [], ],
           [[False], [], [True, False], [], [False, False, False, False], [False, True, True], ],
           [[True], [], [], [], [], [], ],
           [[False], [], [], [False], [], [], ],
           [[], [True], [], [], [], [], ],
           [[], [False], [], [], [], [], ],
           [[], [False], [], [True, False], [], [], ],
           [[], [False], [True], [], [], [], ],
        ]

        self.expected_pps_pkts_persistent = [
            [
                (ipv4_to_int('10.10.10.10'), '10.10.10.0/24', 1),
                (ipv4_to_int('40.40.40.40'), '40.40.40.0/24', 4),
                (ipv4_to_int('60.60.60.60'), '60.60.60.0/24', 6),
                (ipv4_to_int('80.80.80.80'), '80.80.80.0/24', 8),
            ],
            [
                (ipv4_to_int('10.10.10.10'), '10.10.10.0/24', 1),
                (ipv4_to_int('40.40.40.40'), '40.40.40.0/24', 4),
                (ipv4_to_int('60.60.60.60'), '60.60.60.0/24', 6),
                (ipv4_to_int('80.80.80.80'), '80.80.80.0/24', 8),
            ],
        ]

        self.expected_pps_flags_persistent = [
            [True, True, False, False],
            [False, False, True, False],
        ]

    def test_get_pkts_real_old(self):
        boundaries = prepare_ingress_routers(self.border)

        all_packets, timing, timestamps, flags = get_pkts_time_slice(
            self.file_name, self.real_iterations, self.duration_real, boundaries)

        self.assertListEqual(all_packets, self.expected_pps_real_pkts_old)
        self.assertListEqual(timing, self.expected_real_timing_old)
        self.assertListEqual(timestamps, self.expected_pps_real_timestamps_old)
        self.assertListEqual(flags, self.expected_pps_real_flags_old)

    def test_get_pkts_pps_old(self):
        boundaries = prepare_ingress_routers(self.border)

        all_packets, timestamps, flags = get_pkts(
            self.file_name, self.pps_iterations, self.duration_pps, self.pps, boundaries)

        self.assertListEqual(all_packets, self.expected_pps_real_pkts_old)
        self.assertListEqual(timestamps, self.expected_pps_real_timestamps_old)
        self.assertListEqual(flags, self.expected_pps_real_flags_old)

    def test_get_pkts_real_new(self):
        file_ptr = open(self.file_name, 'r')
        IP_SLICE = int(2**32 / self.border)

        router_pkts = [[] for i in range(self.border)]
        pkts = list()
        timestamps = list()
        flags = list()
        router_flags = [[] for i in range(self.border)]

        for i in range(self.real_iterations):
            start = i * self.duration_real
            end = (i+1) * self.duration_real

            current_pkts, current_timestamps, current_flags, file_ptr, per_router, per_router_flags = get_pkts_efficient(file_ptr, start, end, IP_SLICE, True, self.border)
            pkts.append(current_pkts)
            for i in range(self.border):
                router_pkts[i].append(per_router[i])
                router_flags[i].append(per_router_flags[i])
            timestamps.append(current_timestamps)
            flags.append(current_flags)

        file_ptr.close()

        self.assertListEqual(pkts, self.expected_real_pkts_new)
        self.assertListEqual(timestamps, self.expected_real_timestamps_new)
        self.assertListEqual(flags, self.expected_real_flags_new)
        self.assertListEqual(router_pkts, self.expected_real_per_router)
        self.assertListEqual(router_flags, self.expected_real_per_router_flags)

    def test_get_pkts_pps_new(self):
        file_ptr = open(self.file_name, 'r')
        IP_SLICE = int(2**32 / self.border)

        router_pkts = [[] for i in range(self.border)]
        pkts = list()
        timestamps = list()
        flags = list()
        router_flags = [[] for i in range(self.border)]

        for i in range(self.pps_iterations):
            start = i * self.duration_pps * self.pps
            end = (i+1) * self.duration_pps * self.pps

            current_pkts, current_timestamps, current_flags, file_ptr, per_router, per_router_flags = get_pkts_efficient(file_ptr, start, end, IP_SLICE, False, self.border)
            pkts.append(current_pkts)
            for i in range(self.border):
                router_pkts[i].append(per_router[i])
                router_flags[i].append(per_router_flags[i])
            timestamps.append(current_timestamps)
            flags.append(current_flags)

        file_ptr.close()

        self.assertListEqual(pkts, self.expected_pps_pkts_new)
        self.assertListEqual(timestamps, self.expected_pps_timestamps_new)
        self.assertListEqual(flags, self.expected_pps_flags_new)
        self.assertListEqual(router_pkts, self.expected_pps_per_router)
        self.assertListEqual(router_flags, self.expected_pps_per_router_flags)

    def test_get_pkts_real_preprocessed(self):
        file_ptr = open(self.preprocessed_input, 'r')

        router_pkts = [[] for i in range(self.border)]
        pkts = list()
        timestamps = list()
        flags = list()
        router_flags = [[] for i in range(self.border)]

        for i in range(self.real_iterations):
            start = i * self.duration_real
            end = (i+1) * self.duration_real

            current_pkts, current_timestamps, current_flags, file_ptr, per_router, per_router_flags = get_preprocessed_pkts(file_ptr, start, end, True, self.border, False)
            pkts.append(current_pkts)
            for i in range(self.border):
                router_pkts[i].append(per_router[i])
                router_flags[i].append(per_router_flags[i])
            timestamps.append(current_timestamps)
            flags.append(current_flags)

        file_ptr.close()

        self.assertListEqual(pkts, self.expected_real_pkts_new)
        self.assertListEqual(timestamps, self.expected_real_timestamps_new)
        self.assertListEqual(flags, self.expected_real_flags_new)
        self.assertListEqual(router_pkts, self.expected_real_per_router)
        self.assertListEqual(router_flags, self.expected_real_per_router_flags)

    def test_get_pkts_pps_preprocessed(self):
        file_ptr = open(self.preprocessed_input, 'r')

        router_pkts = [[] for i in range(self.border)]
        pkts = list()
        timestamps = list()
        flags = list()
        router_flags = [[] for i in range(self.border)]

        for i in range(self.pps_iterations):
            start = i * self.duration_pps * self.pps
            end = (i+1) * self.duration_pps * self.pps

            current_pkts, current_timestamps, current_flags, file_ptr, per_router, per_router_flags = get_preprocessed_pkts(file_ptr, start, end, False, self.border, False)
            pkts.append(current_pkts)
            for i in range(self.border):
                router_pkts[i].append(per_router[i])
                router_flags[i].append(per_router_flags[i])
            timestamps.append(current_timestamps)
            flags.append(current_flags)

        file_ptr.close()

        self.assertListEqual(pkts, self.expected_pps_pkts_new)
        self.assertListEqual(timestamps, self.expected_pps_timestamps_new)
        self.assertListEqual(flags, self.expected_pps_flags_new)
        self.assertListEqual(router_pkts, self.expected_pps_per_router)
        self.assertListEqual(router_flags, self.expected_pps_per_router_flags)

    def test_get_pkts_pps_persistent(self):
        file_ptr = open(self.file_name_persistent, 'r')
        IP_SLICE = int(2**32 / self.border)

        pkts = list()
        flags = list()
        border_dict = {}

        for i in range(self.pps_iterations_persistent):
            start = i * self.duration_pps * self.pps
            end = (i+1) * self.duration_pps * self.pps

            current_pkts, _, current_flags, file_ptr, _, _ = get_pkts_efficient(file_ptr, start, end, IP_SLICE, False, self.border, True, border_dict)
            pkts.append(current_pkts)
            flags.append(current_flags)

        file_ptr.close()

        self.assertListEqual(pkts, self.expected_pps_pkts_persistent)
        self.assertListEqual(flags, self.expected_pps_flags_persistent)

    def test_get_pkts_pps_preprocessed_persistent(self):
        file_ptr = open(self.preprocessed_input_persistent, 'r')

        pkts = list()
        flags = list()

        for i in range(self.pps_iterations_persistent):
            start = i * self.duration_pps * self.pps
            end = (i+1) * self.duration_pps * self.pps

            current_pkts, _, current_flags, file_ptr, _, _ = get_preprocessed_pkts(file_ptr, start, end, False, self.border, True)
            pkts.append(current_pkts)
            flags.append(current_flags)

        file_ptr.close()

        self.assertListEqual(pkts, self.expected_pps_pkts_persistent)
        self.assertListEqual(flags, self.expected_pps_flags_persistent)


class TestPktSampling(unittest.TestCase):
    def setUp(self):
        self.file_name = 'files_for_unittests/default.csv'
        self.duration_real = 2
        self.border = 8
        self.real_iterations = 3
        self.frequency = 3

        # fixed "random" starting points in 0..2
        self.to_sample = [
            0,
            1,
            2,
            0,
            1,
            2,
            0,
            1,
        ]

        self.expected_sampled_pkts = [
            [(168430090, '10.10.10.0/24', 1), (673720360, '40.40.40.0/24', 4), (1179010630, '70.70.70.0/24', 7)],
            [(1852730990, '110.110.110.0/24', 2), (3200171710, '190.190.190.0/24', 2), (2021161080, '120.120.120.0/24', 8)],
            [(4042322160, '240.240.240.0/24', 2)],
        ]

        self.expected_to_sample = [
            [1, 0, 0],
            [0, 1, 0],
            [1, 1, 1],
            [2, 1, 1],
            [0, 0, 0],
            [1, 1, 1],
            [2, 0, 0],
            [0, 2, 2],
        ]

        # all pkts with flags + randomly sampled ones without flags
        self.expected_sampled_pkts_everflow = [
                [(168430090, '10.10.10.0/24', 1), (505290270, '30.30.30.0/24', 3), (842150450, '50.50.50.0/24', 5), (1684300900, '100.100.100.0/24', 1)] +
                [(673720360, '40.40.40.0/24', 4), (1179010630, '70.70.70.0/24', 7)],

                [(1852730990, '110.110.110.0/24', 2), (2021161080, '120.120.120.0/24', 8), (2358021260, '140.140.140.0/24', 7)] +
                [(3200171710, '190.190.190.0/24', 2)],

                [(4210752250, '250.250.250.0/24', 2), (168430090, '10.10.10.0/24', 2)] +
                [(4042322160, '240.240.240.0/24', 2)],
        ]

        self.expected_n_flags = [4, 3, 2]

        self.expected_n_random = [2, 1, 1]

    def test_get_sampled_magnifier(self):
        file_ptr = open(self.file_name, 'r')
        IP_SLICE = int(2**32 / self.border)

        sampled_pkts = list()
        all_to_sample = [[] for i in range(self.border)]

        for i in range(self.real_iterations):
            start = i * self.duration_real
            end = (i+1) * self.duration_real

            _, _, _, file_ptr, per_router, per_router_flags = get_pkts_efficient(file_ptr, start, end, IP_SLICE, True, self.border)
            sampled, self.to_sample = get_sampled_packets_per_router(per_router, per_router_flags, False, self.frequency, self.to_sample)
            for j, value in enumerate(self.to_sample):
                all_to_sample[j].append(value)

            sampled_pkts.append(sampled)

        file_ptr.close()

        self.assertListEqual(sampled_pkts, self.expected_sampled_pkts)
        self.assertListEqual(all_to_sample, self.expected_to_sample)

    def test_get_sampled_everflow(self):
        file_ptr = open(self.file_name, 'r')
        IP_SLICE = int(2**32 / self.border)

        sampled_pkts = list()
        all_to_sample = [[] for i in range(self.border)]
        all_n_flags = list()
        all_n_random = list()

        for i in range(self.real_iterations):
            start = i * self.duration_real
            end = (i+1) * self.duration_real

            current_pkts, _, current_flags, file_ptr, per_router, per_router_flags = get_pkts_efficient(file_ptr, start, end, IP_SLICE, True, self.border)
            sampled, self.to_sample, n_flags, n_random = get_sampled_packets_everflow(current_pkts, current_flags, per_router, per_router_flags, self.frequency, self.to_sample)
            for j, value in enumerate(self.to_sample):
                all_to_sample[j].append(value)

            sampled_pkts.append(sampled)
            all_n_flags.append(n_flags)
            all_n_random.append(n_random)

        file_ptr.close()

        self.assertListEqual(sampled_pkts, self.expected_sampled_pkts_everflow)
        # should be the same as for magnifier
        self.assertListEqual(all_to_sample, self.expected_to_sample)
        self.assertListEqual(all_n_flags, self.expected_n_flags)
        self.assertListEqual(all_n_random, self.expected_n_random)


class TestSentinelExport(unittest.TestCase):
    def setUp(self):
        self.pkt = [
            (0, '1.2.3.0/24', 0),
            (0, '1.2.3.0/24', 0),
            (0, '1.2.3.0/24', 0),
            (0, '1.2.3.0/24', 0),
            (0, '2.2.3.0/24', 0),
            (0, '2.2.200.0/24', 0),
            (0, '2.2.4.0/24', 0),
            (0, '3.2.3.0/24', 0),
            (0, '4.2.3.0/24', 0),
            (0, '5.2.3.0/24', 0),
        ]

        self.sentinel_1 = [
            ('1.2.3.0/24', 1),
            ('2.2.0.0/16', 2),
            ('3.2.3.0/20', 3),
        ]

        self.sentinel_2 = [
            ('4.2.3.0/24', 1),
            ('2.2.0.0/20', 2),
            ('5.2.0.0/16', 3),
        ]

        self.out_file = 'unittest_sentinel_export.csv'
        self.expected = 'files_for_unittests/sentinel_export_expected.csv'

    def test_sentinel_export(self):
        if os.path.isfile(self.out_file):
            os.remove(self.out_file)

        export_sentinels(self.sentinel_1, self.pkt, self.out_file, 1)
        export_sentinels(self.sentinel_2, self.pkt, self.out_file, 2)

        with io.open(self.expected) as f_expected, io.open(self.out_file) as f_out:
            self.assertListEqual(list(f_expected), list(f_out))

        if os.path.isfile(self.out_file):
            os.remove(self.out_file)


# class TestPktPreprocessing(unittest.TestCase):
#     def setUp(self):
#         self.expected = 'files_for_unittests/expected_preprocessed.csv'
#         self.raw = 'files_for_unittests/default.csv'
#         self.output = 'test_preprocess.csv'

#     def test_sentinel_export(self):
#         preprocess(self.raw, self.output)

#         with io.open(self.expected) as f_expected, io.open(self.output) as f_out:
#             self.assertListEqual(list(f_expected), list(f_out))

#         if os.path.isfile(self.output):
#             os.remove(self.output)


class TestEnhanceSentinels(unittest.TestCase):
    def setUp(self):
        self.pkt = [
            (0, '1.2.3.0/24', 0),
            (0, '1.2.3.0/24', 0),
            (0, '1.2.3.0/24', 0),
            (0, '1.2.3.0/24', 0),
            (0, '2.2.3.0/24', 0),
            (0, '2.2.200.0/24', 0),
            (0, '2.2.4.0/24', 0),
            (0, '3.2.3.0/24', 0),
            (0, '4.2.3.0/24', 0),
            (0, '5.2.3.0/24', 0),
        ]

        self.sentinel = [
            ('1.2.3.0/24', 1),
            ('2.2.0.0/16', 2),
            ('3.2.3.0/20', 3),
        ]

        self.expected = {
            '1.2.3.0/24': [1, 4, 24],
            '2.2.0.0/16': [2, 3, 16],
            '3.2.3.0/20': [3, 1, 20],
        }

    def test_enhance_sentinel(self):
        sentinel_dict = enhance_sentinels(self.sentinel, self.pkt)
        self.assertDictEqual(sentinel_dict, self.expected)


class TestOrderSentinels(unittest.TestCase):
    def setUp(self):
        self.pkt = [
            (0, '1.2.3.0/24', 0),
            (0, '1.2.3.0/24', 0),
            (0, '2.2.3.0/24', 0),
            (0, '2.2.200.0/24', 0),
            (0, '2.2.4.0/24', 0),
            (0, '3.2.3.0/24', 0),
            (0, '4.2.3.0/24', 0),
            (0, '5.2.3.0/24', 0),
        ]

        self.sentinel = [
            ('1.2.3.0/24', 1),
            ('2.2.0.0/16', 2),
            ('3.2.3.0/20', 3),
        ]

        self.expected_activity = [
            ('2.2.0.0/16', 2),
            ('1.2.3.0/24', 1),
            ('3.2.3.0/20', 3),
        ]

        self.expected_size = [
            ('2.2.0.0/16', 2),
            ('3.2.3.0/20', 3),
            ('1.2.3.0/24', 1),
        ]

    def test_order_sentinel_activity(self):
        sentinel_dict = enhance_sentinels(self.sentinel, self.pkt)
        sentinels = order_sentinels(sentinel_dict, 'activity')
        self.assertListEqual(self.expected_activity, sentinels)

    def test_order_sentinel_size(self):
        sentinel_dict = enhance_sentinels(self.sentinel, self.pkt)
        sentinels = order_sentinels(sentinel_dict, 'size')
        self.assertListEqual(self.expected_size, sentinels)


if __name__ == '__main__':
    unittest.main()
