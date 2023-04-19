""" Main class for sentinel search
"""

import numpy as np
import pandas as pd
import logging


logger = logging.getLogger("main_step")
logger.setLevel(logging.WARNING)
logger_handler = logging.StreamHandler()
logger.addHandler(logger_handler)
logger_handler.setFormatter(logging.Formatter("[MAIN:%(asctime)s - %(funcName)12s()] %(message)s",  datefmt='%Y-%m-%d %H:%M:%S'))


class Sentinel:
    """ Sentinel class

    Performs sentinel search and further operations.
    """

    def __init__(self, filename=""):
        """ constructor

        filename (str): save location for all important results (none by default)
        """

        if filename:
            self.has_file = True
            self.sentinel_file = open(filename+'_sentinel.txt', 'w', buffering=1)
        else:
            self.has_file = False

        self.t_in = None
        self.t_out = None
        self.t_in_origin = None
        self.t_out_origin = None
        self.in_flows = 0
        self.out_flows = 0
        self.in_coverage = list()
        self.out_coverage = list()
        self.coverage_steps_in = list()
        self.coverage_steps_out = list()
        self.n_unique_matching_flows = 0
        self.rules_in_src = set()
        self.rules_in_dst = set()
        self.rules_in_src_dst = set()
        self.rules_out_src = set()
        self.rules_out_dst = set()
        self.rules_out_src_dst = set()
        self.dict_in_src = dict()
        self.dict_in_dst = dict()
        self.dict_out_src = dict()
        self.dict_out_dst = dict()

    def __del__(self):
        """ destructor: closes result file and explicitly deletes big files """

        if self.has_file:
            self.sentinel_file.close()

        del self.t_in
        del self.t_out
        del self.t_in_origin
        del self.t_out_origin

    def clean(self):
        """ cleans memory between runs """

        del self.t_in
        self.t_in = None
        del self.t_out
        self.t_out = None
        self.in_flows = 0
        self.out_flows = 0
        self.in_coverage = list()
        self.out_coverage = list()
        self.coverage_steps_in = list()
        self.coverage_steps_out = list()
        self.n_unique_matching_flows = 0
        self.rules_in_src = set()
        self.rules_in_dst = set()
        self.rules_in_src_dst = set()
        self.rules_out_src = set()
        self.rules_out_dst = set()
        self.rules_out_src_dst = set()

    def aggregate(self, aggregation_key, aggregation_types_in, aggregation_types_out=None):
        """ aggregates tables

        aggregation_key (list of str): list of column names used as key for aggregation
        aggreagation_types_in (dict: str to function): how the different columns should be aggregated (e.g. sum, max, ...)
        aggreagation_types_out (dict: str to function): if not None, this aggregation types will be used for the egress traffic
            otherwise the same as for the ingress traffic will be used
        """

        if not aggregation_types_out:
            aggregation_types_out = aggregation_types_in
        self.t_in = self.t_in.groupby(aggregation_key, as_index=False).aggregate(aggregation_types_in)

        logger.info("Aggregation done: %s", aggregation_key)

        # TODO: add support back for stats update
        # self.write_stats()

    def sentinel_search(self, for_ingress, ip_to_use, result_name, unique_column,
                      num_stop=1, keep_temp=False, mark_name=None,
                      start=16, end=8):
        """ general sentinel search

        for_ingress (bool): search Sentinel on ingresses or egresses
        ip_to_use (str): name of table column to use as IP for the search
        result_name (str): column name that will be used to save the results (will be added to the tables)
        unique_column (str): column name of feature that should be unique for one Sentinel
        num_stop (int): stopping criteria for search (default == 1 <= real Sentinel)
        keep_temp (bool): keep temp column used during search (default == False)
        mark_name (str): column name to write down found unique (unique_column) value in other table (default: don't do it)
        start (int): start sentinel search as 32-start (default 16)
        end (int): end sentinel search as 32-end (default 8)

        returns: set of all found sentinels (IP, size, router)
        """

        temp_set = dict()

        self.t_in['temp'] = ""
        self.t_in[result_name] = ""

        # end-1 as second point is not included in range
        for i in range(start, end-1, -1):
            logger.info("Starting Sentinel search level %s for %s", 32-i, result_name)
            self.t_in.loc[self.t_in[result_name] == False, 'temp'] = self.t_in[ip_to_use].loc[self.t_in[result_name] == False].apply(lambda ip: (ip >> i) << i)

            if for_ingress:
                temp = self.t_in.loc[self.t_in[result_name] == False].groupby('temp')[unique_column].nunique()
            else:
                temp = self.t_out.loc[self.t_out[result_name] == False].groupby('temp')[unique_column].nunique()

            for ip, count in temp.items():
                if count <= num_stop:
                    temp_set[ip] = 32-i

            self.t_in[result_name] = self.t_in['temp'].apply(lambda key: key in temp_set)

        # mark matching observations on other side of the network
        if mark_name:
            if for_ingress:
                small_table = self.t_in.loc[self.t_in[result_name] == True][[unique_column, 'temp']]
                temp_dict = small_table.set_index('temp')[unique_column].to_dict()
                self.t_out[mark_name] = -1
                self.t_out.loc[self.t_out[result_name] == True, mark_name] = self.t_out.loc[self.t_out[result_name] == True]['temp'].map(temp_dict)
            else:
                small_table = self.t_out.loc[self.t_out[result_name] == True][[unique_column, 'temp']]
                temp_dict = small_table.set_index('temp')[unique_column].to_dict()
                self.t_in[mark_name] = -1
                self.t_in.loc[self.t_in[result_name] == True, mark_name] = self.t_in.loc[self.t_in[result_name] == True]['temp'].map(temp_dict)

        if for_ingress:
            small_table = self.t_in.loc[self.t_in[result_name] == True][[unique_column, 'temp']]
            if ip_to_use == 'src_ip':
                self.dict_in_src = small_table.set_index('temp')[unique_column].to_dict()
            elif ip_to_use == 'dst_ip':
                self.dict_in_dst = small_table.set_index('temp')[unique_column].to_dict()
        else:
            small_table = self.t_out.loc[self.t_out[result_name] == True][[unique_column, 'temp']]
            if ip_to_use == 'src_ip':
                self.dict_out_src = small_table.set_index('temp')[unique_column].to_dict()
            elif ip_to_use == 'dst_ip':
                self.dict_out_dst = small_table.set_index('temp')[unique_column].to_dict()

        if self.has_file:
            self.write_all_sentinels(for_ingress, ip_to_use, temp_set)

        if not keep_temp:
            self.t_in.drop(columns=['temp'], inplace=True)

        if for_ingress:
            if ip_to_use == 'src_ip':
                temp_set = {(key, value, self.dict_in_src[key]) for key, value in temp_set.items()}
            elif ip_to_use == 'dst_ip':
                temp_set = {(key, value, self.dict_in_dst[key]) for key, value in temp_set.items()}
        else:
            if ip_to_use == 'src_ip':
                temp_set = {(key, value, self.dict_out_src[key]) for key, value in temp_set.items()}
            elif ip_to_use == 'dst_ip':
                temp_set = {(key, value, self.dict_out_dst[key]) for key, value in temp_set.items()}

        return temp_set

    def write_all_sentinels(self, for_ingress, ip_to_use, temp_set):
        """ legacy function to write out all sentinels

        for_ingress (bool): do sentinels belong to ingress or egress
        ip_to_use (str): name of table column to use as IP for the search
        temp_set (set): set which contains all found sentinels
        """

        self.sentinel_file.write('===== ' + str(for_ingress) + ' ' + ip_to_use + ' =====\n')
        if for_ingress:
            if ip_to_use == 'src_ip':        
                for key, value in temp_set.items():
                    self.sentinel_file.write('{},{},{}\n'.format(key, value, self.dict_in_src[key]))

            elif ip_to_use == 'dst_ip':
                for key, value in temp_set.items():
                    self.sentinel_file.write('{},{},{}\n'.format(key, value, self.dict_in_dst[key]))

        else:
            if ip_to_use == 'src_ip':
                for key, value in temp_set.items():
                    self.sentinel_file.write('{},{},{}\n'.format(key, value, self.dict_out_src[key]))

            elif ip_to_use == 'dst_ip':
                for key, value in temp_set.items():
                    self.sentinel_file.write('{},{},{}\n'.format(key, value, self.dict_out_dst[key]))    
