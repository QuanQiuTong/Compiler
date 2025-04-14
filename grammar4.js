module.exports = grammar({
    name: 'typescript',
    extras: $ => [
        $.comment,
        /\s/,  // Whitespace
        /[\s\p{Zs}\uFEFF\u2028\u2029\u2060\u200B]/,
    ],
    // 指定优先级
    precedences: $ => [
        [
            $.update_expression,
            'binary_times',
            'binary_plus',
            'binary_relation',
            'binary_equality',
        ],
    ],
    // 处理冲突
    conflicts: $ => [
        [$.update_expression, $.expression_statement],
        [$.update_expression, $.variable_declaration],
        [$.variable_declaration], // 变量声明可能含分号
    ],

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
            $.for_statement,
        ),

        for_statement: $ => seq(
            // week4 for语句
            'for',
            '(',
            optional(field('init', choice($.declaration, $.expression))),
            ';',
            optional(field('condition', $.expression)),
            ';',
            optional(field('update', $.expression)),
            ')',
            field('body', $.statement),
        ),

        binary_expression: $ => choice(
            ...[
                ['+', 'binary_plus'],
                ['-', 'binary_plus'],
                ['*', 'binary_times'],
                ['/', 'binary_times'],
                ['%', 'binary_times'],
                ['<', 'binary_relation'],
                ['<=', 'binary_relation'],
                ['==', 'binary_equality'],
                ['===', 'binary_equality'],
                ['!=', 'binary_equality'],
                ['!==', 'binary_equality'],
                ['>=', 'binary_relation'],
                ['>', 'binary_relation'],
            ].map(([operator, precedence, associativity]) =>
                (associativity === 'right' ? prec.right : prec.left)(precedence, seq(
                    // week4 识别二元操作binary_expression
                    field('left', $.expression),
                    field('operator', operator),
                    field('right', $.expression),
                )),
            ),
        ),

        update_expression: $ => prec.left(choice(
            seq(
                field('argument', $.expression),
                field('operator', choice('++', '--')),
            ),
            seq(
                field('operator', choice('++', '--')),
                field('argument', $.expression),
            ),
        )),

        if_statement: $ => prec.right(seq(
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
            $.number,
            $.binary_expression,
            $.update_expression,
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
        required_parameter: $ => seq(
            $.identifier,
            field('type', optional($.type_annotation)),
        ),

        type_annotation: $ => seq(
            ':', $.primitive_type,
        ),

        primitive_type: _ => choice(
            'any', 'number', 'boolean', 'string', 'symbol', 'void', 'unknown', 'string', 'never', 'object',
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
