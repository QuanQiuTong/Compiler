#!/usr/bin/env python3

import pprint
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

    # 解析object.property形式
    def parse_field(self, node: Node, statements: list):
        myobject = self.find_child_by_field(node, "object")
        field = self.find_child_by_field(node, "property")
        shadow_object = self.parse(myobject, statements)
        shadow_field = self.parse(field, statements)
        return (shadow_object, shadow_field)

    def assignment_expression(self, node: Node, statements: list):
        shadow_right = self.parse(self.find_child_by_field(node, "right"), statements)
        if self.find_child_by_field(node, "left").type == "member_expression":
            object, field = self.parse_field(self.find_child_by_field(node, "left"), statements)
            statements.append({
                "field_write": {
                    "receiver_object": object,
                    "field": field,
                    "source": shadow_right
                }
            })
            return {
                "field_read": {
                    "receiver_object": object,
                    "field": field
                }
            }
        else:
            shadow_left = self.read_node_text(self.find_child_by_field(node, "left"))
            statements.append({"assign_stmt": {
                "target": shadow_left,
                "operand": shadow_right
            }})
            return shadow_left

    def method_declaration(self,node,statements):
        method_decl: dict[str, str] = {}
        method_decl['name'] = self.read_node_text(self.find_child_by_field(node, "name"))
        if self.find_child_by_field(node, "return_type"):
            method_decl['data_type'] = method_decl['data_type'] = self.read_node_text(self.find_child_by_field(node, "return_type").named_children[0]) # 去掉冒号
        attrs: list[str] = []
        for child in node.named_children:
            if child.type == "accessibility_modifier":
                attrs.append(self.read_node_text(child))
        method_decl['attrs'] = attrs
        new_param: list = []
        self.formal_parameter(self.find_child_by_field(node, "parameters"), new_param)
        method_decl['parameters'] = new_param
        new_body: list = []
        self.statement_block(self.find_child_by_field(node, "body"), new_body)
        method_decl['body'] = new_body
        statements.append({'method_decl': method_decl})
        return method_decl
        #week3任务，需要支持参数，可以用formal_parameter函数帮助解析

    def formal_parameter(self, node: Node, statements: list):
        for child in node.named_children:
            statements.append({
                'parameter_decl':{
                    'name': self.read_node_text(self.find_child_by_field(child, "pattern")),
                    'data_type': self.read_node_text(self.find_child_by_field(child, "type").named_children[0])
                    }
            })

    def class_declaration(self, node: Node, statements: list):
        #week3任务，解析class,class_body部分可用class_body函数帮助解析
        # print(f"class_declaration: {node}")
        class_decl: dict[str] = {}
        class_decl['name'] = self.read_node_text(self.find_child_by_field(node, "name"))
        # new_body = []
        self.class_body(self.find_child_by_field(node, "body"), class_decl)
        # class_decl['body'] = new_body
        statements.append({'class_decl': class_decl})
        return {'class_decl': class_decl}

    def class_body(self, node, class_decl: dict[str]):
        #week3任务，解析class_body部分，需要解析类的字段与成员函数
        statements: list = []
        for child in node.named_children:
            if self.is_comment(child):
                continue
            else:
                self.parse(child, statements)
        for child in statements:
            print(child)
            key = list(child.keys())
            assert len(key) == 1
            if key[0] not in class_decl:
                class_decl[key[0]] = []
            class_decl[key[0]].append(child)
        print()

    def public_field_definition(self, node: Node, statements: list):
        #week3任务, 解析类的字段
        # print(f"public_field_definition: {node}, {self.read_node_text(node)}\n")
        variable_decl: dict[str] = {}
        variable_decl['name'] = self.read_node_text(self.find_child_by_field(node, "name"))
        if self.find_child_by_field(node, "type"):
            variable_decl['data_type'] = self.read_node_text(self.find_child_by_field(node, "type").named_children[0])
        attrs: list[str] = []
        for child in node.named_children:
            if child.type == "accessibility_modifier":
                attrs.append(self.read_node_text(child))
        variable_decl['attrs'] = attrs
        statements.append({'variable_decl': variable_decl})
        # print(variable_decl)
        return {'variable_decl': variable_decl}

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
