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

        number: _ => {
          //week2任务，16进制数的正则表达式
          const hex_literal = ;

          //week2任务，10进制数的正则表达式
          const decimal_digits = ;
    
          return token(choice(
            hex_literal,
            decimal_digits,
          ));
        },
        expression_statement: $ => seq(
            $.expression,
            $._semicolon,
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
        ),

        function_declaration: $ => prec.right(seq(
            optional('async'),
            'function',
            field('name', $.identifier),
            $.call_signature,
            field('body', $.statement_block),
            optional($._semicolon),
          )),
        

        primitive_type: _ => choice(
            'any', 'number','boolean','string','symbol','void','unknown','string','never','object',
        ),
                
	    //参数的类型注释。匹配的内容为 :number或:any
        type_annotation: $ => seq(
            ':',$.primitive_type,
        ),

        formal_parameters: $ => seq(
            '(',
            //week2任务，支持简单参数，包括类型注解。匹配的内容为 (b:number, c:any)
            //hint1: 匹配零个或多个由逗号分隔的元素，可以使用辅助函数commaSep
            //hint2："$."用于引用当前grammar.js中定义的其他语法规则，如$.type_annotation->引用名为type_annotation的规则
            ')',
        ),

        call_signature: $ => seq(
            //week2任务，函数的调用签名，包括参数与返回类型 。匹配的内容为 (b:number, c:any):void
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