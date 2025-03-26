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
    [$.update_expression, $.variable_declaration]
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
      //week3 if语句
    )),

    parenthesized_expression: $ => seq(
      //week3 括号表达式,勇于if_statement的条件部分
    ),

    variable_declaration: $ => seq(
      //week3 变量声明
    ),



    number: _ => {
      //week2任务，10、16进制数的正则表达式
      const hex_literal = ;

      const decimal_digits = ;

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
      //week2任务，函数的调用签名，包括参数与返回类型

    ),
    formal_parameters: $ => seq(
      '(',
      //week2
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