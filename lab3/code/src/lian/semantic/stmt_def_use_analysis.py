#!/usr/bin/env python3

import ast

from lian.util import util
from lian.config.constants import (
    ComputeOperation,
    BuiltinDataTypeName,
    BuiltinSymbolName,
    StateKind
)
from lian.semantic.internal_structure import (
    StmtStatus,
    Symbol,
    State
)

def determine_constant_symbol_type(name):
    if util.isna(name):
        return None

    if name in ["NULL", "none"]:
        return BuiltinDataTypeName.NULL
    elif name in ["true", "True", "false", "False"]:
        return BuiltinDataTypeName.BOOL

    try:
        int(name)
        return BuiltinDataTypeName.INT
    except ValueError:
        pass

    try:
        float(name)
        return BuiltinDataTypeName.FLOAT
    except ValueError:
        pass

    return BuiltinDataTypeName.STRING


class StmtDefUseAnalysis:
    def __init__(self, symbol_to_def_stmts, symbol_state_space, stmt_to_status):
        self.symbol_to_def_stmts = symbol_to_def_stmts
        self.symbol_state_space = symbol_state_space
        self.stmt_to_status = stmt_to_status
        self.def_use_analysis_handlers = {
            "use_stmt"                      : self.use_stmt_defuse,
            "variable_decl"                 : self.variable_decl_defuse,
            "method_decl"                   : self.method_decl_defuse,
            "assign_stmt"                   : self.assign_stmt_defuse,
            # "call_stmt"                     : self.call_stmt_def_use,
            # "array_write"                    : self.array_write_def_use,
            # "if_stmt"                       : self.if_stmt_def_use, 
            # "array_read"                    : self.array_read_def_use,
            "while_stmt"                    : self.while_stmt_def_use,
            
        }

    def analyze_stmt_def_use(self, stmt_id, stmt):
        # util.debug(f"stmt:{stmt}")
        handler = self.def_use_analysis_handlers.get(stmt.operation)
        # util.debug(f"handler:{handler}")
        if handler is not None:
            return handler(stmt_id, stmt)
        return self.empty_def_use(stmt_id, stmt)

    def add_def_use_status(self, status):
        # util.debug(f"status:{status}").
        # final_used_symbols = []
        # for used_symbol in status.used_symbols:
        #     if used_symbol != -1:
        #         final_used_symbols.append(used_symbol)
        # status.used_symbols = final_used_symbols
        self.stmt_to_status[status.stmt_id] = status

        defined_symbol = self.symbol_state_space[status.defined_symbol]
        if isinstance(defined_symbol, Symbol):
            if defined_symbol.name not in self.symbol_to_def_stmts:
                self.symbol_to_def_stmts[defined_symbol.name] = set()
            self.symbol_to_def_stmts[defined_symbol.name].add(status.stmt_id)
            # self.symbol_id_to_name[defined_symbol.symbol_id] = defined_symbol.name

    def create_state(self, stmt_id, value = "", data_type = "", state_type = StateKind.REGULAR):
        return State(
            stmt_id = stmt_id,
            value = value,
            data_type = str(data_type),
            state_type = state_type
        )

    def create_symbol(self, stmt_id, name, default_data_type = ""):
        return Symbol(
            stmt_id = stmt_id,
            name = name,
            default_data_type = default_data_type
        )

    def create_symbol_state_and_add_space(self, stmt_id, name, default_data_type = "", state_type = StateKind.REGULAR):
        if util.is_empty(name):
            return -1

        item = None
        if util.is_variable(name):
            item = self.create_symbol(stmt_id, name, default_data_type = default_data_type)
        else:
            if not default_data_type:
                default_data_type = determine_constant_symbol_type(name)
            item = self.create_state(stmt_id, name, data_type = default_data_type, state_type = state_type)

        index = self.symbol_state_space.add(item)
        return index

    def empty_def_use(self, stmt_id, stmt):
        self.add_def_use_status(
            StmtStatus(
                stmt_id,
            )
        )

    def use_stmt_defuse(self, stmt_id, stmt):
        used_symbol_list = []
        for symbol in [stmt.name]:
            if not util.isna(symbol):
                used_symbol_list.append(
                    self.create_symbol_state_and_add_space(stmt_id, symbol)
                )

        self.add_def_use_status(
            StmtStatus(
                stmt_id,
                used_symbols = used_symbol_list,
            )
        )

    def variable_decl_defuse(self, stmt_id, stmt):
        defined_symbol = self.create_symbol_state_and_add_space(stmt_id, stmt.name, stmt.data_type, state_type = StateKind.UNSOLVED)
        status = StmtStatus(
                stmt_id,
                defined_symbol = defined_symbol,
                operation = ComputeOperation.VARIABLE_DECL
            )
        self.add_def_use_status(status)

    def method_decl_defuse(self, stmt_id, stmt):
        # self.empty_def_use(stmt_id, stmt)
        defined_symbol = self.create_symbol_state_and_add_space(stmt_id, stmt.name)
        self.add_def_use_status(
            StmtStatus(
                stmt_id,
                defined_symbol = defined_symbol,
                operation = ComputeOperation.METHOD_DECL,
            )
        )

    def assign_stmt_defuse(self, stmt_id, stmt):
        self.add_def_use_symbols(stmt_id, stmt.target, [stmt.operand, stmt.operand2])



    def call_stmt_def_use(self, stmt_id, stmt):
        # convert stmt.args(str) to list
        args_list = []
        positional_args = ast.literal_eval(stmt.positional_args)

        self.add_def_use_symbols(stmt_id, stmt.target, [stmt.name] + positional_args)

    def array_read_def_use(self, stmt_id, stmt):
        self.add_def_use_symbols(stmt_id, stmt.target, [stmt.array, stmt.index])

    def array_write_def_use(self, stmt_id, stmt):
        self.add_def_use_symbols(stmt_id, stmt.array, [stmt.array, stmt.index, stmt.source])

    def if_stmt_def_use(self, stmt_id, stmt):
        self.add_def_use_symbols(stmt_id, None, [stmt.condition])
    def while_stmt_def_use(self, stmt_id, stmt):
        self.add_def_use_symbols(stmt_id, None, [stmt.condition])


    def add_def_use_symbols(self, stmt_id, def_symbol = None, used_symbols = [], op =ComputeOperation.DATA_FLOW):

        used_symbol_list = []

        for symbol in used_symbols:
            if not util.isna(symbol):
                used_symbol_list.append(
                    self.create_symbol_state_and_add_space(stmt_id, symbol)
                )

        defined_symbol = self.create_symbol_state_and_add_space(stmt_id, def_symbol)

        self.add_def_use_status(
            StmtStatus(
                stmt_id,
                defined_symbol = defined_symbol,
                used_symbols = used_symbol_list,
                operation = ComputeOperation.DATA_FLOW,
            )
        )
