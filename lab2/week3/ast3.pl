(program 
    (class_declaration 
        name: 
            (type_identifier) 
        body: 
            (class_body 
                (comment) 
                (public_field_definition 
                    name: 
                        (property_identifier) 
                    type: 
                        (type_annotation 
                            (predefined_type))) 
                (public_field_definition 
                    (accessibility_modifier) 
                    name: 
                        (property_identifier) 
                    type: 
                        (type_annotation 
                            (predefined_type))) 
                (public_field_definition 
                    (accessibility_modifier) name: 
                    (property_identifier) type: 
                    (type_annotation 
                    (predefined_type))) 
                    (comment) 
                (method_definition 
                    name: 
                        (property_identifier) 
                    parameters: 
                        (formal_parameters 
                            (required_parameter 
                                pattern: 
                                    (identifier) 
                                type: 
                                    (type_annotation 
                                    (predefined_type))) 
                            (required_parameter 
                                pattern: 
                                    (identifier) 
                                type: 
                                    (type_annotation 
                                    (predefined_type))) 
                            (required_parameter 
                                pattern: 
                                    (identifier) 
                                type: 
                                    (type_annotation 
                                    (predefined_type)))) 
                    body: 
                        (statement_block 
                            (expression_statement 
                                (assignment_expression 
                                    left: 
                                        (member_expression object: 
                                        (this) property: 
                                        (property_identifier)) 
                                    right: 
                                        (identifier))) 
                            (expression_statement 
                                (assignment_expression 
                                    left: 
                                        (member_expression object: 
                                        (this) property: 
                                        (property_identifier)) 
                                    right: 
                                        (identifier))) 
                            (expression_statement 
                                (assignment_expression 
                                    left: 
                                        (member_expression object: 
                                        (this) property: 
                                        (property_identifier)) 
                                    right: 
                                        (identifier))))) 
                (comment) 
                (method_definition 
                    (accessibility_modifier)
                    name: 
                        (property_identifier) 
                    parameters: 
                        (formal_parameters 
                        (required_parameter 
                            pattern: 
                                (identifier) 
                            type: 
                                (type_annotation 
                                (predefined_type)))) 
                    return_type: 
                        (type_annotation 
                        (predefined_type)) 
                    body: 
                        (statement_block 
                        (return_statement 
                            (binary_expression left: 
                            (identifier) right: 
                            (member_expression object: 
                            (this) property: 
                            (property_identifier))))))
                )))