import yaml
import schema
import requests
import click
from bcf.firmware.yml_schema import meta_yml_schema, validate


def load_meta_yaml(fd):
    meta_yaml = yaml.safe_load(fd)
    validate(meta_yml_schema, meta_yaml)
    return meta_yaml


def load_source_from_url(url):
    click.echo("Download list from %s ..." % url, nl=False)

    try:
        response = requests.get(url, allow_redirects=True)

        if response.status_code < 200 or response.status_code >= 300:
            raise Exception("Response status_code=%d" % response.status_code)

        data = yaml.safe_load(response.text)

        click.secho("\r\rDownload list from %s    " % url, fg='green')

        return data

    except Exception as e:
        click.secho("\r\rDownload list from %s    " % url, nl=False, fg='red')
        if isinstance(e, requests.exceptions.ConnectionError):
            click.echo("Unable to connect to server")
        else:
            click.echo("Error " + str(e))


def test_firmware_resources(data, skip_error=True):

    error_url = []

    def test_url(url):
        text = '  - url: %s ... ' % url
        click.echo(text, nl=False)
        response = requests.head(url, allow_redirects=True)
        if response.status_code != 204 and response.status_code != 200:
            if skip_error:
                click.secho('error', fg='red')
                error_url.append(url)
            else:
                click.echo()
                raise Exception('Bad status code %s' % response.status_code)
        else:
            click.secho('ok', fg='green')

    if 'article' in data:
        test_url(data['article'])
    if 'articles' in data:
        for article in data['articles']:
            test_url(article['url'])
            if 'video' in article:
                test_url(article['video'])
            if 'images' in article:
                for image in article['images']:
                    test_url(image['url'])
    if 'images' in data:
        for image in data['images']:
            test_url(image['url'])
    if 'assembly' in data:
        for assembly in data['assembly']:
            if 'url' in assembly:
                test_url(assembly['url'])
            if 'image' in assembly:
                test_url(assembly['image'])

    return error_url
