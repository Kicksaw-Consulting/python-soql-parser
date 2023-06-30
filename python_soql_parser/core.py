# stolen from https://github.com/pyparsing/pyparsing/blob/master/examples/simpleSQL.py

from typing import Any, TypedDict
from functools import cache

from pyparsing import (
    CaselessKeyword,
    Literal,
    Forward,
    Group,
    Optional,
    ParserElement,
    Suppress,
    Word,
    alphanums,
    alphas,
    delimitedList,
    infixNotation,
    oneOf,
    opAssoc,
    pyparsing_common,
    quotedString,
)

from python_soql_parser.binops import EQ, GT, GTE, LT, LTE, NEQ
from python_soql_parser.date_literals import CONSTANT_DATE_KEYWORDS, PARAMETERIZED_DATE_KEYWORDS


@cache
def create_soql_parser() -> ParserElement:
    ParserElement.enablePackrat()

    select_statement = Forward()
    SELECT, FROM, WHERE, AND, OR, IN, NULL, TRUE, FALSE, LIMIT, OFFSET, ORDER, BY, DESC, ASC = map(
        CaselessKeyword,
        "select from where and or in null true false limit offset order by desc asc".split(),
    )

    identifier = Word(alphas, alphanums + "_" + ".").setName("identifier")
    field_name = delimitedList(identifier).setName("field name")
    field_name_list = Group(delimitedList(field_name))
    sobject_name = identifier.setName("sobject name")

    binop = oneOf(f"{EQ} {NEQ} {LT} {LTE} {GT} {GTE}")
    real_num = pyparsing_common.real()
    int_num = pyparsing_common.signed_integer()
    date_time = pyparsing_common.iso8601_datetime()
    # See https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql_select_dateformats.htm
    constant_date_literal = oneOf(CONSTANT_DATE_KEYWORDS)("constant date literal")
    parameterized_date_literal = Group(
        oneOf(PARAMETERIZED_DATE_KEYWORDS) + Suppress(Literal(":")) + int_num
    )("parameterized date literal")

    field_right_value = (
        date_time | real_num | int_num | quotedString
        | constant_date_literal | parameterized_date_literal
        | field_name
    )
    where_condition = Group(
        (field_name + binop + field_right_value)
        | (field_name + IN + Group("(" + delimitedList(field_right_value) + ")"))
    )

    where_expression = infixNotation(
        where_condition,
        [
            (AND, 2, opAssoc.LEFT),
            (OR, 2, opAssoc.LEFT),
        ],
    )

    where_clause = Optional(Suppress(WHERE) + where_expression, None)

    limit_clause = Optional(Suppress(LIMIT) + int_num, None)

    offset_clause = Optional(Suppress(OFFSET) + int_num, None)

    ordering_term = Group(field_name + Optional(ASC | DESC)("direction"))

    order_clause = Optional(
        Suppress(ORDER) + Suppress(BY) + Group(delimitedList(ordering_term))
    )

    # define the grammar
    select_statement <<= (
        SELECT
        + field_name_list("fields")
        + FROM
        + sobject_name("sobject")
        + where_clause("where")
        + order_clause("order_by")
        + limit_clause("limit")
        + offset_clause("offset")
    )

    soql: ParserElement = select_statement

    return soql


class SoqlQuery(TypedDict):
    # TODO: type the `Any`s
    fields: Any
    sobject: str
    where: Any
    limit: Any
    offset: Any


def parse(soql_query: str) -> SoqlQuery:
    return create_soql_parser().parseString(soql_query)
