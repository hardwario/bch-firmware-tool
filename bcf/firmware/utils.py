import yaml
import schema
from bcf.firmware.yml_schema import meta_yml_schema, validate


def load_meta_yaml(fd):
    meta_yaml = yaml.safe_load(fd)
    validate(meta_yml_schema, meta_yaml)
    return meta_yaml
