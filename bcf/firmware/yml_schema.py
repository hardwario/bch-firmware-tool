# -*- coding: utf-8 -*-
from schema import Schema, And, Or, Use, Optional, SchemaError
import os

meta_yml_schema = Schema({
    Optional('description'): Or(str, None),
    Optional('article'): Or(str, None),
    Optional('video'): Or(str, None),
    Optional('images'): [
        {
            'url': And(str, len),
            Optional('title'): Or(str, None),
        }
    ],
    Optional('articles'): [
        {
            'url': And(str, len),
            Optional('title'): Or(str, None),
            Optional('description'): Or(str, None),
            Optional('images'): [
                {
                    'url': And(str, len),
                    Optional('title'): Or(str, None),
                }
            ],
            Optional('video'): Or(str, None),
        }
    ],
    Optional('assembly'): [
        {
            'name': And(str, len),
            Optional('url'): Or(str, None),
            Optional('image'): Or(str, None),
            Optional('optional'): Or(bool, None)
        }
    ],
})

source_yml_schema = Schema(
    [
        {
            'id': And(str, len),
            'type': And(str, lambda x: x in ('list', 'api',)),
            'url': And(str, len)
        }
    ]
)


def validate(schema, data):
    try:
        schema.validate(data)
    except SchemaError as e:
        error = []
        n = 0
        for row in e.autos:

            i = row.find('did not validate')
            if i > -1:
                row = 'D' + row[i + 1:]

            if row.startswith('Wrong keys'):
                del error[-1]
                n -= 2

            error.append(" " * n + row)
            n += 2

        raise Exception(os.linesep.join(error))

    return True
