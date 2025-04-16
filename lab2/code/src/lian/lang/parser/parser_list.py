from . import java_parser
from . import typescript_parser

PARSERS = {
    'java'  : java_parser.Parser,
    'typescript' :typescript_parser.Parser,
}