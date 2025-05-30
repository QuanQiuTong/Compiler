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
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator).replace("=", "")

        shadow_right = self.parse(right, statements)

        # week3任务，需要支持left为object.property的形式，可以用parser_field函数帮助解析
        if left.type  == "member_expression":
            shadow_object, field = self.parse_field(left, statements)
            if not shadow_operator:
                statements.append(
                    {"field_write": {"receiver_object": shadow_object, "field": field, "source": shadow_right}})
                return shadow_right

            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": field, }})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"field_write": {"receiver_object": shadow_object, "field": field, "source": tmp_var2}})

            return tmp_var2

        shadow_left = self.read_node_text(left)
        if not shadow_operator:
            statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})
        else:
            statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
        return shadow_left

    def method_declaration(self, node: Node, statements: list):
        child = self.find_child_by_field(node, "return_type")
        mytype = self.read_node_text(child.named_child(0)) if child else None

        attrs = [
            self.read_node_text(m)
            for m in self.find_children_by_type(node, "accessibility_modifier")
        ]

        child = self.find_child_by_field(node, "name")
        name = self.read_node_text(child)

        parameters = []
        params = self.find_child_by_field(node, "parameters")
        self.formal_parameter(params, parameters)

        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)

        statements.append(
            {"method_decl": {"attrs":attrs, "data_type": mytype, "name": name, "parameters": parameters, "body": new_body}})

    def formal_parameter(self, node: Node, statements: list):
        # week3任务，解析参数
        if not node:
            return
        for param in node.named_children:
            child = self.find_child_by_type(param, "modifiers")
            modifiers = self.read_node_text(child).split()

            mytype = self.find_child_by_field(param, "type").named_child(0)
            shadow_type = self.read_node_text(mytype)

            if "[]" in shadow_type:
                modifiers.append("array")

            name = self.find_child_by_field(param, "pattern")
            shadow_name = self.read_node_text(name)

            statements.append({"parameter_decl": {"attr": modifiers, "data_type": shadow_type, "name": shadow_name}})

    def class_declaration(self, node: Node, statements: list):
        glang_node = {
            "attrs": [], # "class" 可能是为了区分interface?
            "fields": [],
            "member_methods": []
            # "nested" = [] # subclass
        }

        child = self.find_child_by_type(node, "modifiers")
        modifiers = self.read_node_text(child).split()
        glang_node["attrs"].extend(modifiers)

        child = self.find_child_by_field(node, "name")
        if child:
            glang_node["name"] = self.read_node_text(child)

        child = self.find_child_by_field(node, "body")
        if child:
            self.class_body(child, glang_node)

        statements.append({"class_decl": glang_node})

    def class_body(self, node: Node, gir_node: dict):
        # week3任务，解析class_body部分，需要解析类的字段与成员函数
        for child in self.find_children_by_type(node, "public_field_definition"):
            self.public_field_definition(child, gir_node["fields"])

        for child in self.find_children_by_type(node, "method_definition"):
            self.method_declaration(child, gir_node["member_methods"])

    def public_field_definition(self, node: Node, statements: list):
        attrs = [
            self.read_node_text(m)
            for m in self.find_children_by_type(node, "accessibility_modifier")
        ]
        name = self.read_node_text(self.find_child_by_field(node, "name"))
        t = self.find_child_by_field(node, "type")
        type = self.read_node_text(t.named_child(0)) if t else None
        statements.append({"variable_decl":{"attrs":attrs, "name":name, "data_type":type}})

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
