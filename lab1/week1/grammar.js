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
        ),
  
        declaration: $ => choice(
            $.function_declaration,
        ),
  
        function_declaration: $ => prec.right(seq(
            optional('async'),
            'function',
            field('name', $.identifier),
            $.formal_parameters,
            field('body', $.statement_block),
            optional($._semicolon),
          )),
  
        formal_parameters: $ => seq(
        '(',
  
        ')',
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