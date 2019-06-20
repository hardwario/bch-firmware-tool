# -*- coding: utf-8 -*-
from schema import Schema, And, Or, Use, Optional, SchemaError

meta_yml_schema = Schema({
    Optional('description'): Or(str, None),
    Optional('article'): Or(str, None),
    Optional('video'): Or(str, None),
    Optional('images'): [
        {
            'url': Or(And(str, len), None),
            Optional('title'): Or(str, None),
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
            'type': And(str, lambda x: x in ('list', )),
            'url': And(str, len)
        }
    ]
)
