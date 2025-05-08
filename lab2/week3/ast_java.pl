(program
  (class_declaration
    (modifiers)
    name: (identifier)       ; 类名
    body: (class_body
      (line_comment)         ; "// 成员变量"
      
      ;;━━ 字段声明 ━━━━━━━━━━━━━━━━━
      (field_declaration
        type: (type_identifier)
        declarator: (variable_declarator
          name: (identifier)))
          
      (field_declaration
        (modifiers)          ; public
        type: (type_identifier)
        declarator: (variable_declarator
          name: (identifier)))
          
      (field_declaration
        (modifiers)          ; public
        type: (integral_type) ; number → int
        declarator: (variable_declarator
          name: (identifier)))
      
      (line_comment)         ; "// 构造函数"
      
      ;;━━ 构造函数 ━━━━━━━━━━━━━━━━━
      (constructor_declaration
        (modifiers)          ; public
        name: (identifier)    ; constructor
        parameters: (formal_parameters
          (formal_parameter
            type: (type_identifier)
            name: (identifier))
          (formal_parameter
            type: (type_identifier)
            name: (identifier))
          (formal_parameter
            type: (integral_type) ; number → int
            name: (identifier)))
        body: (constructor_body
          ;;━━ 字段赋值语句 ━━━━━━━
          (expression_statement
            (assignment_expression
              left: (field_access
                object: (this)
                field: (identifier))
              right: (identifier)))
          (expression_statement
            (assignment_expression
              left: (field_access
                object: (this)
                field: (identifier))
              right: (identifier)))
          (expression_statement
            (assignment_expression
              left: (field_access
                object: (this)
                field: (identifier))
              right: (identifier))))))
      
      (line_comment)         ; "// 私有方法"
      
      ;;━━ 方法声明 ━━━━━━━━━━━━━━━━━
      (method_declaration
        (modifiers)          ; private
        type: (integral_type) ; number → int
        name: (identifier)    ; getBirthYear
        parameters: (formal_parameters
          (formal_parameter
            type: (integral_type) ; number → int
            name: (identifier)))
        body: (block
          (return_statement
            (binary_expression
              left: (identifier)     ; currentYear
              right: (field_access   ; this.age
                object: (this)
                field: (identifier))))))))