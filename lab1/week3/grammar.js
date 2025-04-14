module.exports = grammar({
    name: 'typescript',
    extras: $ => [
        $.comment,
        /\s/,  // Whitespace
        /[\s\p{Zs}\uFEFF\u2028\u2029\u2060\u200B]/,
    ],
    // precedences: $ => [

    //     ['declaration', 'literal'],

    // ],
    word: $ => $.identifier,
    rules: {
        program: $ => seq(
          optional($.hash_bang_line),
          repeat($.statement),
        ),
    
        hash_bang_line: _ => /#!.*/,

        statement: $ => choice(
            $.declaration,
            $.statement_block,
            $.expression_statement,
            $.statement_block,
            $.if_statement,
            seq('return', $.expression, $._semicolon),
            seq($.identifier, choice('+', '-', '*', '/'), $.expression)
        ),

        if_statement: $ => prec.right(seq(
            //week3 if语句
            'if',
            field('condition', $.parenthesized_expression),
            field('consequence', $.statement),
            optional(field('alternative', $.else_clause))
        )),

        else_clause: $ => seq(
            'else',
            $.statement
        ),
       
        parenthesized_expression: $ => seq(
            '(',
            $.expression,
            ')',
        ),

        variable_declaration: $ => seq(
            choice('let', 'const', 'var'),
            field('name', $.identifier),
            optional(
                field('type', $.type_annotation)
            ),
            optional(seq('=',
                field('value', $.expression)
            )),
            optional($._semicolon),
        ),

       

        number: _ => {
          const hex_literal = /0[xX][0-9A-Fa-f]+/;
    
          const decimal_digits = /[0-9]+/;
    
          return token(choice(
            hex_literal,
            decimal_digits,
          ));
        },
        expression_statement: $ => seq(
            $.expression,
            optional($._semicolon),
        ),
        expression: $ => choice(
            $.assignment_expression,
            $.identifier,
            $.number
        ),

        assignment_expression: $ => prec.right(seq(
            optional('using'),
            field('left', $.identifier),
            '=',
            field('right', $.expression),
        )),

        declaration: $ => choice(
            $.function_declaration,
            $.variable_declaration,
        ),

        function_declaration: $ => prec.right(seq(
            optional('async'),
            'function',
            field('name', $.identifier),
            $.call_signature,
            field('body', $.statement_block),
            optional($._semicolon),
          )),
        
        call_signature: $ => seq(
            field('parameter', $.formal_parameters),
            optional(field('return_type', $.type_annotation))
        ),
        formal_parameters: $ => seq(
            '(',
            optional(commaSep(seq(
                field('name', $.identifier),
                optional(field('type', $.type_annotation)),
                optional(seq('=', $.expression))  // 支持默认值
            ))),
            ')',
        ),


        type_annotation: $ => seq(
            ':',$.primitive_type,
        ),

        primitive_type: _ => choice(
            'any', 'number','boolean','string','symbol','void','unknown','string','never','object',
        ),
        statement_block: $ => prec.right(seq(
            '{',
            repeat($.statement),
            '}',
            optional($._semicolon),
        )),

          
        comment: $ => choice(
            token(choice(
            seq('//', /.*/),
            seq(
                '/*',
                /[^*]*\*+([^/*][^*]*\*+)*/,
                '/',
            ),
            )),
        ),

        
        
        identifier: $ => /[_a-zA-Z][_a-zA-Z0-9]*/, 
        
        // 分号
        _semicolon: $ => ';',

    }
    
})



function commaSep1(rule) {
    return seq(rule, repeat(seq(',', rule)));
  }
  
  function commaSep(rule) {
    return optional(commaSep1(rule));
  }
  
  function sepBy1(sep, rule) {
    return seq(rule, repeat(seq(sep, rule)));
  }