#!/usr/bin/env python3

from tree_sitter import Node
from . import common_parser

class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type in ["line_comment", "block_comment"]

    def is_identifier(self, node):
        return node.type == "identifier"

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "null": self.regular_literal,
            "true": self.regular_literal,
            "false": self.regular_literal,
            "identifier": self.regular_literal,
            "number": self.regular_number_literal,
            "string": self.string_literal,
            "summary_string": self.string_literal,
            "summary_substitution": self.string_substitution,
            "subscript_expression": self.parse_subscript,
            "this": self.this_literal,
            "super": self.super_literal,
            "private_property_identifier": self.regular_literal,
            "property_identifier": self.regular_literal
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node: Node, statements: list, replacement: list):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            "function_declaration": self.method_declaration,
            "method_signature": self.method_declaration,
            "function_signature": self.method_declaration,
            "class_declaration": self.class_declaration,
            "public_field_definition": self.public_field_definition,
            "method_definition": self.method_declaration,


        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node: Node, statements: list):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "assignment_expression": self.assignment_expression,
            "assignment_pattern": self.assignment_expression,  # "assignment_pattern" is a special case of "assignment_expression
            "function_expression": self.method_declaration,
            "binary_expression": self.binary_expression,
            "member_expression": self.member_expression,
            "call_expression": self.call_expression,
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node: Node, statements: list):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "statement_block": self.statement_block,
            "return_statement": self.return_statement,
            "if_statement": self.if_statement,
            "for_statement": self.for_statement,

        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node: Node, statements: list):
        handler = self.check_statement_handler(node)
        return handler(node, statements)

    def string_literal(self, node: Node, statements: list, replacement: list):
        replacement = []
        for child in node.named_children:
            self.parse(child,statements,replacement)

        ret = self.read_node_text(node)
        if replacement:
            for r in replacement:
                (expr, value) = r
                ret = ret.replace(self.read_node_text(expr), value)

        ret = self.handle_hex_string(ret)
        return self.handle_hex_string(ret)

    def string_substitution(self, node: Node, statements: list, replacement: list):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)
        replacement.append((node, shadow_expr))
        return shadow_expr

    def this_literal(self, node: Node, statements: list, replacement: list):
        return self.global_this()

    def super_literal(self, node: Node, statements: list, replacement: list):
        return self.global_super()

    def regular_literal(self, node: Node, statements: list, replacement: list):
        return self.read_node_text(node)
    
    def regular_number_literal(self, node: Node, statements: list, replacement: list):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)
    
    def non_null_expression(self, node: Node, statements: list):
        self.parse(node.named_children[0], statements)

    def parse_field(self, node: Node, statements: list):
        myobject = self.find_child_by_field(node, "object")
        field = self.find_child_by_field(node, "property")
        shadow_object = self.parse(myobject, statements)
        shadow_field = self.parse(field, statements)

        return (shadow_object, shadow_field)
    def call_expression(self, node: Node, statements: list):
        name = self.find_child_by_field(node, "function")
        shadow_name = self.parse(name, statements)

        type_arguments = self.find_child_by_field(node, "type_arguments")
        type_text = self.read_node_text(type_arguments)[1:-1] if type_arguments else ""

        args = self.find_child_by_field(node, "arguments")
        args_list = []

        if args.named_child_count > 0:
            for child in args.named_children:
                if self.is_comment(child):
                    continue

                shadow_variable = self.parse(child, statements)
                if shadow_variable:
                    args_list.append(shadow_variable)

        tmp_return = self.tmp_variable(node)
        statements.append({"call_stmt": {"target": tmp_return, "name": shadow_name, "positional_args": args_list,"data_type": type_text}})

        return tmp_return
    def parse_subscript(self,node,statements,flag = 0):
        if flag == 1: # for write
            obj = self.parse(self.find_child_by_field(node, "object"), statements)
            optional_chain = self.find_child_by_field(node, "optional_chain")
            index = self.parse(self.find_child_by_field(node, "index"), statements)
            return obj,index
        else:
            obj = self.parse(self.find_child_by_field(node, "object"), statements)
            optional_chain = self.find_child_by_field(node, "optional_chain")
            index = self.parse(self.find_child_by_field(node, "index"), statements)
            tmp_var = self.tmp_variable(node)
            statements.append({"array_read": {"target": tmp_var, "array": obj, "index": index}})
            return tmp_var
    def parse_array_pattern(self, node: Node, statements: list):
        elements = node.named_children
        num_elements = len(elements)
        shadow_left_list = []
        for i in range(num_elements):
            element = elements[i]
            if self.is_comment(element):
                continue
            shadow_element = self.parse(element, statements)
            shadow_left_list.append(shadow_element)
        return shadow_left_list
    def assignment_expression(self, node: Node, statements: list):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator).replace("=", "")

        shadow_right = self.parse(right, statements)



        if left.type == "subscript_expression":
            shadow_array, shadow_index = self.parse_array_pattern(left, statements)

            if not shadow_operator:
                statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": shadow_right}})
                return shadow_right

            tmp_var = self.tmp_variable(node)
            statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
            tmp_var2 = self.tmp_variable(node)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": tmp_var2}})

            return tmp_var2

        # 数组解构
        if left.type == "array_pattern":
            index = 0
            for p in left.named_children:
                if self.is_comment(p):
                    continue

                pattern = self.parse(p, statements)

                statements.append({"array_read": {"target": pattern, "array": shadow_right, "index": str(index)}})
                index += 1

            return shadow_right



        shadow_left = self.read_node_text(left)
        if not shadow_operator:
            statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})
        else:
            statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
        return shadow_left

    def pattern(self, node: Node, statements: list):
        return self.parse(self.node.named_children[0], statements)


    def parse_private_property_identifier(self, node: Node, statements: list):
            return self.read_node_text(node)

    def parse_sequence_expression(self, node: Node, statements: list):
        sub_expressions = node.named_children
        sequence_list = []
        for sub_expression in sub_expressions:
            if self.is_comment(sub_expression):
                continue
            sequence_list.append(self.parse(sub_expression, statements))
        return sequence_list

    def method_declaration(self,node,statements):
        #week2 assignment
        child = self.find_child_by_field(node, "name")
        name = self.read_node_text(child)

        modifiers = []
        child = self.find_child_by_type(node, "accessibility_modifier")
        if child:
            modifiers.append(self.read_node_text(child))

        child = self.find_child_by_type(node, "override_modifier")
        if child:
            modifiers.append(self.read_node_text(child))

        child = self.find_child_by_field(node, "return_type")
        return_type = ""
        if child:
            named_cld = child.named_children
            if named_cld:
                return_type = self.read_node_text(named_cld[0])

        

        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)

        statements.append({"method_decl": {"attrs": modifiers, "data_type": return_type, "name": name, 
                               "body": new_body}})

        return name


    
    def formal_parameter(self, node: Node, statements: list):

        pass

    def class_declaration(self, node: Node, statements: list):
        pass

    def class_body(self, node, gir_node):
        pass
    def public_field_definition(self, node: Node, statements: list):
        pass

    def for_statement(self, node: Node, statements: list):
        init_children = self.find_children_by_field(node, "initializer")
        step_children = self.find_children_by_field(node, "increment")

        condition = self.find_child_by_field(node, "condition")

        init_body = []
        condition_init = []
        step_body = []

        shadow_condition = self.parse(condition, condition_init)
        for child in init_children:
            self.parse(child, init_body)

        # Change from Java: may contain no step expressions. Leave step_body blank.
        # if step_children and step_children.named_child_count > 0:
        if step_children:
            for child in step_children:
                self.parse(child, step_body)

        for_body = []

        block = self.find_child_by_field(node, "body")
        self.parse(block, for_body)

        statements.append({"for_stmt":
                               {"init_body": init_body,
                                "condition": shadow_condition,
                                "condition_prebody": condition_init,
                                "update_body": step_body,
                                "body": for_body}})
    def if_statement(self, node: Node, statements: list):
        condition_part = self.find_child_by_field(node, "condition")
        true_part = self.find_child_by_field(node, "consequence")
        false_part = self.find_child_by_field(node, "alternative")

        true_body = []

        shadow_condition = self.parse(condition_part, statements)
        self.parse(true_part, true_body)
        if false_part:
            false_body = []
            self.parse(false_part, false_body)
            # Change from Java: else_clause wraps another rule around the false body.
            statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body, "else_body": false_body}})
        else:
            statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body}})

    # field_read表达式，解析如this.name操作，返回临时变量
    def member_expression(self, node: Node, statements: list,flag = 0):
        obj = self.parse(self.find_child_by_field(node, "object"), statements)
        property_ = self.parse(self.find_child_by_field(node, "property"), statements)
        tmp_var = self.tmp_variable(node)
        statements.append({"field_read": {"target": tmp_var, "receiver_object": obj, "field": property_}})
        return tmp_var

    # 二元表达式，解析如a + b操作，返回临时变量
    def binary_expression(self, node: Node, statements: list):
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)
        right = self.find_child_by_field(node, "right")
        shadow_right = self.parse(right, statements)
        left = self.find_child_by_field(node, "left")
        shadow_left = self.parse(left, statements)

        tmp_var = self.tmp_variable(node)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_left,
                                        "operand2": shadow_right}})
        return tmp_var
    # return语句，解析如return a操作，返回临时变量
    def return_statement(self, node: Node, statements: list):
        shadow_name = ""
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        statements.append({"return_stmt": {"name": shadow_name}})
        return shadow_name
        
    def function_expression(self, node: Node, statements: list):
        return self.method_declaration(node, statements)

    def statement_block(self, node: Node, statements: list):
        children = node.named_children
        for child in children:
            if self.is_comment(child):
                continue
            self.parse(child, statements)

    def expression_statement(self, node: Node, statements: list):
        return self.parse(node.named_children[0], statements)


