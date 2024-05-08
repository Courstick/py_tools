# -*- coding: utf-8 -*-

import urllib3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def requests_retry_session(retries=3,
                           backoff_factor=30,
                           status_forcelist=(500, 502, 504),
                           retry_session=None):
    retry_session = retry_session or requests.Session()
    retry = Retry(total=retries,
                  read=retries,
                  connect=retries,
                  backoff_factor=backoff_factor,
                  status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry,
                          pool_maxsize=20,
                          pool_connections=10)
    retry_session.mount('http://', adapter)
    retry_session.mount('https://', adapter)
    return retry_session


class CheckResponse:
    def __init__(self, method):
        self.method = method

    def __call__(self, *args, **kwargs):
        # 默认timeout
        if 'timeout' not in kwargs:
            kwargs["timeout"] = 10
        # result类型 json or content
        need_raw_content = kwargs.pop("need_raw_content", False)
        result = self.method(*args, **kwargs)
        if result.status_code // 100 == 5 or result.status_code // 100 == 4:
            raise
        else:
            if need_raw_content:
                result_raw = result.content
                result.close()
                return result_raw
            json_data = result.json()
            result.close()
            return json_data


class Session(object):
    def __init__(self):
        self.retry_session = requests_retry_session()
        self.get = CheckResponse(self.retry_session.get)
        self.put = CheckResponse(self.retry_session.put)
        self.post = CheckResponse(self.retry_session.post)
        self.delete = CheckResponse(self.retry_session.delete)
        self.options = CheckResponse(self.retry_session.options)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.retry_session.close()
