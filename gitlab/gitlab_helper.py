# -*- coding: utf-8 -*-
from http_requests.retry_session import Session


class GitlabHelper(object):
    def __init__(self, host, project_id, token):
        self.url = f"{host}/api/v4/projects/{project_id}/trigger/pipeline"
        self.token = token
        self.session = Session()

    def run_pipeline(self, ref, variables: dict = None):
        """
        触发流水线
        Args:
            ref: 分支
            variables:  CI/CD变量
        Returns:

        """
        form = {"ref": ref, "token": self.token}
        if variables:
            form.update({f"variables[{k}]": v for k, v in variables.items()})
        return self.session.post(self.url, data=form)
