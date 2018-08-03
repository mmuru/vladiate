import io
from gzip import GzipFile
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from vladiate.exceptions import MissingExtraException


class VladInput(object):
    ''' A generic input class '''

    def __init__(self):
        raise NotImplementedError

    def open(self):
        raise NotImplementedError

    def __repr__(self):
        raise NotImplementedError


class LocalFile(VladInput):
    ''' Read from a local file path '''

    def __init__(self, filename):
        self.filename = filename

    def open(self):
        with open(self.filename, 'rb') as f:
            if self.filename.endswith('.gz'):
                fdata = f.read()
                bstream = io.BytesIO(bytes(fdata))
                return GzipFile(None, 'rb', fileobj=bstream)
            else:
                return f.readlines()

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.filename)


class S3File(VladInput):
    ''' Read from a file in S3 '''

    def __init__(self, path=None, bucket=None, key=None, aws_config={}):
        try:
            import boto  # noqa
            self.boto = boto
        except ImportError:
            # 2.7 workaround, should just be `raise Exception() from None`
            exc = MissingExtraException()
            exc.__context__ = None
            raise exc
        #
        self.aws_config = aws_config

        if path and not any((bucket, key)):
            self.path = path
            parse_result = urlparse(path)
            self.bucket = parse_result.netloc
            self.key = parse_result.path
        elif all((bucket, key)):
            self.bucket = bucket
            self.key = key
            self.path = "s3://{}{}"
        else:
            raise ValueError(
                "Either 'path' argument or 'bucket' and 'key' argument must "
                "be set."
            )

    def open(self):
        # aws_access_key_id, aws_secret_access_key
        if self.aws_config:
            key = self.aws_config['aws_access_key_id']
            secret = self.aws_config['aws_secret_access_key']
            s3 = self.boto.connect_s3(
                aws_access_key_id=key, aws_secret_access_key=secret)
        else:
            s3 = self.boto.connect_s3()

        bucket = s3.get_bucket(self.bucket)
        key = bucket.new_key(self.key)
        contents = key.get_contents_as_string()
        bstream = io.BytesIO(bytes(contents))
        # check gzip ext
        if self.key.endswith('.gz'):
            gstream = GzipFile(None, 'rb', fileobj=bstream)
            return gstream
        else:
            return bstream

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, self.path)


class String(VladInput):
    ''' Read a file from a string '''

    def __init__(self, string_input=None, string_io=None):
        self.string_io = string_io if string_io else StringIO(string_input)

    def open(self):
        return self.string_io

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, '...')
