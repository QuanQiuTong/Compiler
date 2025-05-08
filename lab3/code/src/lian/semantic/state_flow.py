#!/usr/bin/env python3

import logging
import os
import networkx as nx
import pprint

from lian.util import util
from lian.util.dataframe_operation import DataFrameAgent
from lian.config import (
    config,
    schema
)
from lian.util import dataframe_operation as do
from lian.config.constants import (
    AnalysisPhaseName,
    BuiltinDataTypeName,
    StateChangeFlag,
    ComputeOperation,
    StateKind
)
from lian.semantic.stmt_def_use_analysis import StmtDefUseAnalysis
from lian.semantic.internal_structure import (
    Symbol,
    State,
    BitVectorManager,
    InternalAnalysisTemplate,
    SymbolStateSpace,
    StateFlowGraph,
    SymbolDependencyGraph,
    CallGraph
)

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class StateFlowAnalysis(InternalAnalysisTemplate):
    def init(self):
        self.name = AnalysisPhaseName.StateFlowGraph
        self.description = "state flow graph analysis"

    def internal_analysis_start(self):
        self.call_graph = CallGraph()

    def save_call_graph(self):
        pass

    def internal_analysis_end(self):
        self.save_call_graph()

    def bundle_start(self):
        # self.symbol_dependency_graph_df = DataFrameAgent(columns=schema.symbol_dependency_graph_schema)
        self.all_sdg_edges = []
        self.symbol_dependency_graph = None
        self.all_status = []
        self.all_symbols_and_states = []

    def bundle_end(self):
        semantic_path = self.bundle_path.replace(f"/{config.GLANG_DIR}/", f"/{config.SEMANTIC_DIR}/")
        symbol_dependency_graph_path = semantic_path + config.SYMBOL_DEPENDENCY_EXT
        do.DataFrameAgent(
            self.all_sdg_edges, columns = schema.symbol_dependency_graph_schema
        ).save(
            symbol_dependency_graph_path
        )

        all_status_path = semantic_path + config.STMT_STATUS_EXT
        do.DataFrameAgent(
            self.all_status, columns = schema.stmt_status_schema
        ).save(
            all_status_path
        )

        all_symbols_and_states_path = semantic_path + config.SYMBOLS_STATES_EXT

        do.DataFrameAgent(
            self.all_symbols_and_states, columns = schema.symbols_states_schema
        ).save(
            all_symbols_and_states_path
        )

        self.module_symbols.update_sdg_path_by_glang_path(self.bundle_path, symbol_dependency_graph_path)
        self.module_symbols.update_stmt_status_path_by_glang_path(self.bundle_path, all_status_path)
        self.module_symbols.update_symbols_states_path_by_glang_path(self.bundle_path, all_symbols_and_states_path)

        if self.options.debug and self.symbol_dependency_graph is not None:
            symbol_dependency_graph_png_path = semantic_path + "_sdg.png"
            self.symbol_dependency_graph.save_png(symbol_dependency_graph_png_path)

    def unit_analysis_start(self):
        pass

    def unit_analysis_end(self):
        pass

    def save_results(self):
        edges = []
        edges_with_weights = self.symbol_dependency_graph.graph.edges(data='weight', default = "")
        for e in edges_with_weights:
            edges.append((
                self.symbol_dependency_graph.unit_id,
                self.symbol_dependency_graph.method_id,
                e[0],
                e[1],
                "" if util.is_empty(e[2]) else e[2]
            ))
        self.all_sdg_edges.extend(edges)

        for stmt, status in self.stmt_to_status.items():
            self.all_status.append(status.to_dict(self.unit_id,self.method_id))

        self.all_symbols_and_states.extend(
            self.symbol_state_space.to_dict(self.unit_id, self.method_id)
        )

    def method_analysis(self, previous_results):
        if self.options.debug:
            if util.is_available(self.method_init):
                self.method_init.display()
            if util.is_available(self.method_body):
                self.method_body.display()

        self.cfg = previous_results[AnalysisPhaseName.ControlFlowGraph]

        self.parameter_symbols = set()
        self.defined_external_symbols = set()
        self.used_external_symbols = set()
        self.return_symbols = set()
        self.local_symbols = set()

        self.dynamic_calls = []
        self.direct_calls = []

        self.symbol_dependency_graph = SymbolDependencyGraph(self.unit_info, self.method_stmt)
        self.bit_vector_manager = BitVectorManager()
        self.symbol_state_space = SymbolStateSpace()
        self.stmt_id_to_stmt = {}
        self.stmt_to_status = {}
        self.symbol_to_def_stmts = {}
        self.stmt_counters = {}

        self.stmt_def_use_analysis = StmtDefUseAnalysis(
            self.symbol_to_def_stmts,
            self.symbol_state_space,
            self.stmt_to_status
        )

        # fill "stmt_id_to_stmt"
        self.init_stmts()
        self.analyze_symbol_dependency()
        self.save_results()
        
        return self

    def debug_status(self, status):
        if not self.options.debug:
            return

        result = f"StmtStatus(stmt_id={status.stmt_id}, operation={status.operation}, field={status.field},\n"
        result += f"defined_symbol={status.defined_symbol}:\n"
        result += f" {self.symbol_state_space.find_by_index(status.defined_symbol)}\n"
        result += f"used_symbols={str(status.used_symbols)}:\n"
        result += "\n".join([" " + str(self.symbol_state_space.find_by_index(i)) for i in status.used_symbols])
        result += "\n)"

        util.debug(result)

    def init_stmts(self):
        if util.is_available(self.method_init):
            for row in self.method_init:
                self.stmt_id_to_stmt[row.stmt_id] = row

        if util.is_available(self.method_body):
            for row in self.method_body:
                self.stmt_id_to_stmt[row.stmt_id] = row

    # analyze the defs and uses of each statement.
    def analyze_all_stmt_def_use(self):
        target_nodes = set(self.cfg.nodes())
        for stmt_id in self.stmt_id_to_stmt:
            if stmt_id in target_nodes:
                self.stmt_def_use_analysis.analyze_stmt_def_use(stmt_id, self.stmt_id_to_stmt[stmt_id])

    # connect all def_stmts with bit_vector
    def init_def_stmts_to_bit_vectors(self):
        defs = []
        for stmt_id in self.stmt_to_status:
            defined_symbol_index = self.stmt_to_status[stmt_id].defined_symbol
            symbol = self.symbol_state_space[defined_symbol_index]
            if util.is_available(symbol):
                defs.append(stmt_id)
        self.bit_vector_manager.init(defs)

    def sync_symbol_id(self, defined_symbol, target_stmts):
        if defined_symbol is None:
            return

        all_ids = {defined_symbol.get_id()}
        all_defined_symbols = [defined_symbol]
        for stmt in target_stmts:
            status = self.stmt_to_status.get(stmt)
            if status is None:
                continue
            target_defined_symbol = self.symbol_state_space[status.defined_symbol]
            all_ids.add(target_defined_symbol.get_id())
            all_defined_symbols.append(target_defined_symbol)

        common_id = min(all_ids)
        for target_defined_symbol in all_defined_symbols:
            # pre_id = target_defined_symbol.get_id()
            # del self.symbol_id_to_name[pre_id]
            target_defined_symbol.set_id(common_id)
            # self.symbol_id_to_name[common_id] = target_defined_symbol.name

    @profile
    def reaching_symbol_analysis(self):
       
        worklist = list(self.stmt_to_status.keys())
        while len(worklist) != 0:
            stmt_id = worklist.pop(0)
            if stmt_id not in self.stmt_to_status:
                continue
            status = self.stmt_to_status[stmt_id]
            old_outs = status.out_bits

            status.in_bits = 0
            # TODO task1 how to collect in bits
            for parent_stmt_id in self.cfg.predecessors(stmt_id):
                if parent_stmt_id in self.stmt_to_status:
                    pass

            current_bits = status.in_bits
            # if current stmt has def
            defined_symbol_index = status.defined_symbol
            if defined_symbol_index != -1:
                defined_symbol = self.symbol_state_space[defined_symbol_index]
                if isinstance(defined_symbol, Symbol):
                    # TODO task2 how to kill and gen to get current bits?
                    pass

            status.out_bits = current_bits
            
            # TODO task3 how to determine if we reach fixed point?
            if False:
                worklist = util.merge_list(worklist, list(self.cfg.successors(stmt_id)))

    def construct_symbol_dependency_graph(self):
        for stmt_id in self.stmt_to_status:
            status = self.stmt_to_status[stmt_id]
            for used_symbol_id in status.used_symbols:
                used_symbol = self.symbol_state_space[used_symbol_id]
                if isinstance(used_symbol, Symbol):
                    used_name = used_symbol.name
                    reaching_defs = self.bit_vector_manager.explain(status.in_bits)
                    if used_name in self.symbol_to_def_stmts:
                        reachable_defs = reaching_defs & self.symbol_to_def_stmts[used_name]
                    else:
                        reachable_defs = []
                    # print(f"construct_symbol_dependency_graph@ 可到达词条语句的def stmt有：{reachable_defs}")
                    for def_stmt_id in reachable_defs:
                        reaching_status = self.stmt_to_status[def_stmt_id]
                        defined_symbol_index = reaching_status.defined_symbol
                        # defined_symbol = self.symbol_state_space[defined_symbol_index]
                        # # TODO: why do we need to sync used_symbol's ID?
                        # used_symbol.set_id(defined_symbol.symbol_id)
                        self.symbol_dependency_graph.add_edge(def_stmt_id, stmt_id, used_name)

    def analyze_symbol_dependency(self):
        # Analyze define and use of each stmt, result is saved to "self.stmt_to_status", and meanwhile complete "self.symbol_to_def_stmts"
        self.analyze_all_stmt_def_use()
        # init bit_vectors. Completing "self.stmt_to_bit_pos" and "self.bit_pos_to_stmt"
        self.init_def_stmts_to_bit_vectors()
        # conduct the analysis of reaching definition
        self.reaching_symbol_analysis()
        # construct symbol flow graph
        self.construct_symbol_dependency_graph()