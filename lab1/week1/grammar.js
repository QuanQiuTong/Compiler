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
      ),

      expression_statement: $ => seq(
          $.expression,
          $._semicolon,
      ),
      
      expression: $ => choice(
          $.assignment_expression,
          $.identifier,
      ),

      assignment_expression: $ => prec.right(seq(
          optional('using'),
          field('left', $.expression),
          '=',
          field('right', $.expression),
      )),

      declaration: $ => choice(
          $.function_declaration,
      ),

      function_declaration: $ => prec.right(seq(
          optional('async'),
          'function',
          field('name', $.identifier),
          $.formal_parameters,
          field('return_type', $.type_annotation),
          field('body', $.statement_block),
          optional($._semicolon),
        )),

      formal_parameters: $ => seq(
          '(',
          optional(seq(
              commaSep1($._formal_parameter),
              optional(','),
          )),
          ')',
      ),

      _formal_parameter: $ => seq(
          field('name', $.identifier),
          field('type', optional($.type_annotation)),
      ),

      type_annotation: $ => seq(
          ':',
          $._type,
      ),

      _type: $ => choice(
          'any',
          'number',
          'boolean',
          'string',
          'symbol',
          'void',
          'unknown',
          'string',
          'never',
          'object',
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