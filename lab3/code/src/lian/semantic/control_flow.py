#!/usr/bin/env python3

import networkx as nx

from lian.config import config,schema
from lian.util import util
from lian.util import dataframe_operation as do
from lian.config.constants import (
    ControlFlowKind,
    AnalysisPhaseName
)
from lian.semantic.internal_structure import (
    ControlFlowGraph,
    CFGNode,
    InternalAnalysisTemplate
)

class ControlFlowAnalysis(InternalAnalysisTemplate):
    def init(self):
        self.name = AnalysisPhaseName.ControlFlowGraph
        self.description = "control flow graph analysis"

        self.stmt_handlers = {
            "if_stmt"       : self.analyze_if_stmt,
            "while_stmt"    : self.analyze_while_stmt,
            "dowhile_stmt"  : self.analyze_dowhile_stmt,
            "for_stmt"      : self.analyze_for_stmt,
            "forin_stmt"    : self.analyze_while_stmt,
            "break_stmt"    : self.analyze_break_stmt,
            "continue_stmt" : self.analyze_continue_stmt,
            "try_stmt"      : self.analyze_try_stmt,
            "switch_stmt"   : self.analyze_switch_stmt,
            "return_stmt"   : self.analyze_return_stmt,
            "yield"         : self.analyze_yield_stmt,
            "method_decl"   : self.analyze_method_decl_stmt,
            "class_decl"    : self.analyze_decl_stmt,
            "record_decl"   : self.analyze_decl_stmt,
            "interface_decl": self.analyze_decl_stmt,
            "struct_decl"   : self.analyze_decl_stmt,
        }


    def unit_analysis_start(self):
        pass

    def unit_analysis_end(self):
        pass

    def bundle_start(self):
        self.all_cfg_edges = []
        self.cfg = None

    def bundle_end(self):
        semantic_path = self.bundle_path.replace(f"/{config.GLANG_DIR}/", f"/{config.SEMANTIC_DIR}/")
        cfg_final_path = semantic_path + config.CONTROL_FLOW_GRAPH_EXT
        data_model = do.DataFrameAgent(self.all_cfg_edges, columns = schema.control_flow_graph_schema)
        data_model.save(cfg_final_path)
        self.module_symbols.update_cfg_path_by_glang_path(self.bundle_path, cfg_final_path)
        if self.options.debug and self.cfg is not None:
            cfg_png_path = semantic_path + "_cfg.png"
            self.cfg.save_png(cfg_png_path)

    def replace_multiple_edges_with_single(self):
        flag = True
        old_graph = self.cfg.graph
        for u, v in old_graph.edges():
            if old_graph.number_of_edges(u, v) > 1:
                flag = False
                break

        if flag:
            return
        
        new_graph = nx.DiGraph()
        for u, v in old_graph.edges():
            if old_graph.number_of_edges(u, v) > 1:
                # total_weight = sum(old_graph[u][v][key]['weight'] for key in old_graph[u][v])
                new_graph.add_edge(u, v, weight = ControlFlowKind.EMPTY)
            else:
                if not new_graph.has_edge(u, v):
                    new_graph.add_edge(u, v, weight = old_graph[u][v][0]['weight'])
        self.cfg.graph = new_graph

    def save_current_cfg(self):
        edges = []
        edges_with_weights = self.cfg.graph.edges(data='weight', default = 0)
        for e in edges_with_weights:
            edges.append((
                self.cfg.unit_id,
                self.cfg.method_id,
                e[0],
                e[1],
                0 if util.is_empty(e[2]) else e[2]
            ))
        self.all_cfg_edges.extend(edges)
            
    def read_block(self, parent, block_id):
        return parent.read_block(block_id, reset_index = True)
        # return self.method_body.read_block(block_id, reset_index = True)

    def boundary_of_multi_blocks(self, block, block_ids):
        return block.boundary_of_multi_blocks(block_ids)

    @profile
    def method_analysis(self, previous_results):
        self.cfg = ControlFlowGraph(self.unit_info, self.method_stmt)

        last_stmts_init = self.analyze_init_block(self.method_init)
        last_stmts = self.analyze_block(self.method_body, last_stmts_init)
        if last_stmts:
            self.cfg.add_edge(last_stmts, -1)
        # util.debug("cfg "*20)
        # util.debug(list(self.cfg.graph.edges(data=True)))
        self.replace_multiple_edges_with_single()
        self.save_current_cfg()
        return self.cfg.graph

    def analyze_if_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        last_stmts_of_then_body = [CFGNode(current_stmt, ControlFlowKind.IF_TRUE)]
        then_body_id = current_stmt.then_body
        if not util.isna(then_body_id):
            then_body = self.read_block(current_block, then_body_id)
            if len(then_body) != 0:
                last_stmts_of_then_body = self.analyze_block(then_body, last_stmts_of_then_body, global_special_stmts)
            
        last_stmts_of_else_body = [CFGNode(current_stmt, ControlFlowKind.IF_FALSE)]
        else_body_id = current_stmt.else_body
        if not util.isna(else_body_id):
            else_body = self.read_block(current_block, else_body_id)
            if len(else_body) != 0:
                last_stmts_of_else_body = self.analyze_block(else_body, last_stmts_of_else_body, global_special_stmts)

        boundary = self.boundary_of_multi_blocks(current_block, [then_body_id, else_body_id])
        return (last_stmts_of_then_body + last_stmts_of_else_body, boundary)

    def deal_with_last_stmts_of_loop_body(
            self, current_stmt, last_stmts, special_stmts, global_special_stmts, current_stmt_edge = None
    ):
        self.link_parent_stmts_to_current_stmt(last_stmts, current_stmt)

        result = []
        for counter in reversed(range(len(special_stmts))):
            node = special_stmts[counter]
            if node.operation == "break_stmt":
                result.append(node)
                del special_stmts[counter]
            elif node.operation == "continue_stmt":
                self.link_parent_stmts_to_current_stmt([CFGNode(node, ControlFlowKind.CONTINUE)], current_stmt)
                del special_stmts[counter]
        global_special_stmts.extend(special_stmts)
        result.append(CFGNode(current_stmt, ControlFlowKind.LOOP_FALSE))
        return result

    def analyze_while_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        new_special_stmts = []
        body_id = current_stmt.body
        body = self.read_block(current_block, body_id)
        last_stmts_of_body = self.analyze_block(
            body,
            [CFGNode(current_stmt, ControlFlowKind.LOOP_TRUE)],
            new_special_stmts
        )
        last_stmts = self.deal_with_last_stmts_of_loop_body(
            current_stmt, last_stmts_of_body, new_special_stmts, global_special_stmts
        )
        
        if util.isna(current_stmt.else_body):
            boundary = self.boundary_of_multi_blocks(current_block, [body_id])
            return (last_stmts, boundary)
        
        else_body_id = current_stmt.else_body
        else_body = self.read_block(current_block, else_body_id)
        boundary = self.boundary_of_multi_blocks(current_block, [body_id, else_body_id])
        last_stmts_of_else_body = self.analyze_block(
            else_body,
            # TODO: should this be loop_false?
            [CFGNode(current_stmt, ControlFlowKind.LOOP_TRUE)],
            new_special_stmts
        )
        last_stmts.pop()
        return (last_stmts + last_stmts_of_else_body, boundary)

    def analyze_dowhile_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        body_id = current_stmt.body
        body = self.read_block(current_block, body_id)
        boundary = self.boundary_of_multi_blocks(current_block, [body_id])

        previous = parent_stmts[:]
        previous.append(
            CFGNode(current_stmt, ControlFlowKind.LOOP_TRUE)
        )

        new_special_stmts = []
        last_stmts_of_body = self.analyze_block(body, previous, new_special_stmts)

        last_stmts = self.deal_with_last_stmts_of_loop_body(
            current_stmt, last_stmts_of_body, new_special_stmts, global_special_stmts
        )

        return (last_stmts, boundary)


    def analyze_for_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # util.debug("analyze_for_stmt\n")
        # self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        init_body_id = current_stmt.init_body
        condition_prebody_id = current_stmt.condition_prebody
        update_body_id = current_stmt.update_body

        init_body = self.read_block(current_block, init_body_id)
        condition_prebody = self.read_block(current_block, condition_prebody_id)
        update_body = self.read_block(current_block, update_body_id)

        # deal with init_body
        # util.debug("for_init_body "*5)
        last_stmts = self.analyze_block(init_body, parent_stmts, global_special_stmts)

        # deal with condition_prebody
        # util.debug("for_condition_prebody "*5)
        last_stmts_condition_prebody = self.analyze_block(condition_prebody, last_stmts, global_special_stmts)

        # deal with for body
        # util.debug("for_body "*5)
        body_id = current_stmt.body
        body = self.read_block(current_block, body_id)
        boundary = self.boundary_of_multi_blocks(current_block, [body_id])

        new_special_stmts = []
        last_stmts = self.analyze_block(
            body,
            [CFGNode(current_stmt, ControlFlowKind.LOOP_TRUE)],
            new_special_stmts
        )

        # deal with update_body
        # util.debug("for_update_body "*5)
        # deal with break,return...
        if len(last_stmts)!=0:
            last_stmts = self.analyze_block(update_body, last_stmts, new_special_stmts)

            # deal with condition_prebody
            # util.debug("for_condition_prebody2 "*5)
            last_stmts = self.analyze_block(condition_prebody, last_stmts, new_special_stmts)

        # link condition_prebody and current_stmt
        # and also generate last_stmts
        # util.debug("deal_with_last_stmts_of_loop_body "*5)
        last_stmts = self.deal_with_last_stmts_of_loop_body(
            current_stmt, last_stmts + last_stmts_condition_prebody,
            new_special_stmts, global_special_stmts
        )

        return (last_stmts, boundary)

    def analyze_switch_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)

        body_id = current_stmt.body
        # util.debug(f"body_id=current_stmt.body: {body_id}")
        body = self.read_block(current_block, body_id)
        boundary = self.boundary_of_multi_blocks(current_block, [body_id])

        case_stmt_set = body.remove_blocks()
        # util.debug(f"case_stmt_set = body.remove_blocks():{case_stmt_set}")

        last_stmts_of_previous_body = []
        special_stmts = []
        for case_stmt in case_stmt_set:
            # util.debug(f"-==-for case_stmt in case_stmt_set:{case_stmt}")
            # link swith and case/default
            self.link_parent_stmts_to_current_stmt([current_stmt], case_stmt)
            last_stmts_of_previous_body.append(case_stmt)

            case_body_id = case_stmt.body
            case_body = self.read_block(current_block, case_body_id)
            # util.debug(f"-==-case_body = self.read_block:\n{case_body}")

            last_stmts_of_previous_body = self.analyze_block(case_body, last_stmts_of_previous_body, special_stmts)

        return (last_stmts_of_previous_body + special_stmts, boundary)

    def analyze_try_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # catch_body is ignored
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)

        new_special_stmts = []
        body_id = current_stmt.body
        catch_body_id = current_stmt.catch_body
        else_body_id = current_stmt.else_body
        final_body_id = current_stmt.final_body

        boundary = self.boundary_of_multi_blocks(current_block, [body_id, catch_body_id, else_body_id, final_body_id])

        body = self.read_block(current_block, body_id)
        last_stmts_of_body = self.analyze_block(body, [CFGNode(current_stmt)], global_special_stmts)

        if util.isna(catch_body_id):
            return (last_stmts_of_body, boundary)

        catch_body = self.read_block(current_block, catch_body_id)
        catch_with_init_set = catch_body.remove_blocks()
        pre_init_stmt = last_stmts_of_body
        last_stmts_of_catch_body = []
        for stmt in catch_with_init_set:
            self.link_parent_stmts_to_current_stmt(pre_init_stmt, stmt)
            if stmt.operation == "catch_clause":
                last_stmts_of_catch_clause = self.analyze_block(
                    self.read_block(current_block, stmt.body), [CFGNode(stmt, ControlFlowKind.CATCH_TRUE)], global_special_stmts
                )
                last_stmts_of_catch_body.extend(last_stmts_of_catch_clause)
            pre_init_stmt = [stmt]

        if not util.isna(else_body_id):
            else_body = self.read_block(current_block, else_body_id)
            last_stmts_of_else_body = self.analyze_block(else_body, [CFGNode(last_stmts_of_body, ControlFlowKind.CATCH_FALSE)], global_special_stmts)

            if not util.isna(final_body_id):
                final_body = self.read_block(current_block, final_body_id)
                last_stmts_of_final_body = self.analyze_block(
                    final_body, [CFGNode(last_stmts_of_catch_body, ControlFlowKind.CATCH_FINALLY)] + [CFGNode(last_stmts_of_else_body, ControlFlowKind.CATCH_FINALLY)], global_special_stmts
                )
            else:
                return (last_stmts_of_catch_body + last_stmts_of_else_body, boundary)

        else:
            if not util.isna(final_body_id):
                final_body = self.read_block(current_block, final_body_id)
                last_stmts_of_final_body = self.analyze_block(
                    final_body, [CFGNode(last_stmts_of_catch_body, ControlFlowKind.CATCH_FINALLY)], global_special_stmts
                )
            else:
                return (last_stmts_of_catch_body, boundary)

        return (last_stmts_of_final_body, boundary)

    def analyze_method_decl_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        boundary = self.boundary_of_multi_blocks(
            current_block,
            [
                current_stmt.parameters,
                current_stmt.init,
                current_stmt.body,
            ]
        )
        return ([current_stmt], boundary)

    def analyze_decl_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        """
        class_decl,
        record_decl,
        interface_decl,
        enum_decl,
        enum_constants,
        annotation_type_decl,
        method_decl,
        """
        # static_member_field -> static_init -> member_field -> init -> constructor
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        boundary = self.boundary_of_multi_blocks(
            current_block,
            [
                current_stmt.static_init,
                current_stmt.init,
                current_stmt.fields,
                current_stmt.methods, 
                current_stmt.nested
            ]
        )
        last_stmts = [current_stmt]
        static_init_id = current_stmt.static_init
        if not util.isna(static_init_id):
            static_init_body = self.read_block(current_block, static_init_id)
            if len(static_init_body) != 0:
                last_stmts = self.analyze_block(static_init_body, current_stmt, global_special_stmts)

        init_id = current_stmt.init
        if not util.isna(init_id):
            init_body = self.read_block(current_block, init_id)
            if len(init_body) != 0:
                last_stmts = self.analyze_block(init_body, last_stmts, global_special_stmts)

        methods_id = current_stmt.methods
        if not util.isna(methods_id):
            methods_body = self.read_block(current_block, methods_id)
            if len(methods_body) != 0:
                last_stmts = self.analyze_block(methods_body, last_stmts, global_special_stmts)

        nested_id = current_stmt.nested
        if not util.isna(nested_id):
            nested_body = self.read_block(current_block, nested_id)
            if len(nested_body) != 0:
                last_stmts = self.analyze_block(nested_body, last_stmts, global_special_stmts)

        return (last_stmts, boundary)

    def analyze_return_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        self.cfg.add_edge(current_stmt, -1, ControlFlowKind.RETURN)

        return ([], -1)

    def analyze_break_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        global_special_stmts.append(current_stmt)

        return ([], -1)

    def analyze_continue_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        # self.cfg.add_edge(current_stmt.stmt_id, -1, ControlFlowKind.RETURN)
        global_special_stmts.append(current_stmt)
        return ([], -1)

    def analyze_yield_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt([parent_stmts], current_stmt)
        self.link_parent_stmts_to_current_stmt([current_stmt], -1)
        boundary = current_stmt._index
        return ([current_stmt], boundary)

    @profile
    def link_parent_stmts_to_current_stmt(self, parent_stmts: list, current_stmt):
        for node in parent_stmts:
            if isinstance(node, CFGNode):
                # Assumes node.stmt and node.edge are valid attributes for CFGNode
                self.cfg.add_edge(node.stmt, current_stmt, node.edge)
            else:
                # Links non-CFGNode items
                self.cfg.add_edge(node, current_stmt)

    @profile
    def analyze_init_block(self, current_block, parent_stmts = [], special_stmts = []):
        counter = 0
        previous = parent_stmts
        last_parameter_decl_stmts = []
        last_parameter_init_stmts = []
        first_init_stmt = True

        if util.is_empty(current_block):
            return previous

        while counter < len(current_block):
            current = current_block.access(counter)
            if current.operation == "parameter_decl":
                self.link_parent_stmts_to_current_stmt(parent_stmts, current)
                last_parameter_init_stmts.extend(previous)
                last_parameter_decl_stmts.append(CFGNode(current, ControlFlowKind.PARAMETER_INPUT_TRUE))
                previous = [current]
                counter += 1
                first_init_stmt = True
            else:
                handler = self.stmt_handlers.get(current.operation)
                if first_init_stmt:
                    previous = [CFGNode(previous, ControlFlowKind.PARAMETER_INPUT_FALSE)]
                    first_init_stmt = False
                if handler is None:
                    self.link_parent_stmts_to_current_stmt(previous, current)
                    previous = [current]
                    counter += 1
                else:
                    previous, boundary = handler(current_block, current, previous, special_stmts)
                    if boundary < 0:
                        break
                    counter = boundary + 1
                if counter >= len(current_block):
                    last_parameter_init_stmts.extend(previous)

        return last_parameter_decl_stmts + last_parameter_init_stmts

    @profile
    def analyze_block(self, current_block, parent_stmts = [], special_stmts = []):
        """
        This function is going to deal with current block and extract its control flow graph.
        It returns the last statements inside this block.
        """
        counter = 0
        boundary = 0
        previous = parent_stmts

        if util.is_empty(current_block):
            return previous

        while counter < len(current_block):
            current = current_block.access(counter)
            handler = self.stmt_handlers.get(current.operation)
            if handler is None:
                self.link_parent_stmts_to_current_stmt(previous, current)
                previous = [current]
                counter += 1
            else:
                previous, boundary = handler(current_block, current, previous, special_stmts)
                if boundary < 0:
                    break
                counter = boundary + 1

        return previous
