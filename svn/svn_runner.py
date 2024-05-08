#!/usr/bin/env python3
# coding:utf-8

import os
import platform
import subprocess
import xmltodict

from exception import CMDException

SVN_URL = "svn://svn_host"


def resolve_relative_path(base_path, rel_path):
    return os.path.normpath(os.path.join(base_path, rel_path))


def flatten_dict(d, parent_key='', sep='/'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            if '..' in v:
                base_path = os.path.dirname(new_key)
                tmp_path = resolve_relative_path(base_path, v).replace("\\", "/")
                resolved_path = f'^{tmp_path}'
                items.append((new_key, resolved_path))
            else:
                items.append((new_key, v))
    return dict(items)


class SVNCmdRunner(object):
    def __init__(self, cmd, quiet=True):
        self.cmd = cmd
        self.quiet = quiet
        self.process = None
        self.output = None
        self.error = None
        self.run()

    def run_command(self, cmd):
        if not isinstance(cmd, list):
            cmd_list = cmd.split(' ')
        else:
            cmd_list = cmd
        # print(f"run svn cmd: {cmd}")
        if self.quiet:
            return subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            return subprocess.Popen(cmd_list)

    def run(self):
        retries = 0
        while retries < 2:
            self.process = self.run_command(self.cmd)
            self.output, self.error = self.get_output()
            if self.error and self.should_retry():
                retries += 1
            else:
                break

    def should_retry(self):
        return "E160024" in self.error

    @property
    def returncode(self):
        return self.process.returncode

    def get_output(self):
        out, err = self.process.communicate()
        if out is None and err is None:
            return out, err
        try:
            return out.decode('gbk'), err.decode('gbk')
        except UnicodeDecodeError:
            return out.decode('utf-8'), err.decode('utf-8')


class SVNHelper(object):

    @staticmethod
    def format_externals(externals):
        externals_dict = {}
        if externals:
            try:
                data = xmltodict.parse(externals)
                target = data["properties"].get("target", [])
            except Exception:
                return externals_dict
            if isinstance(target, list):
                for t in target:
                    externals_dict[t["@path"].replace(SVN_URL, "")] = {
                        external.split(" ")[1]: external.split(" ")[0]
                        for external in t.get("property").get("#text", "").strip().splitlines()
                    }
            else:
                externals_dict[target["@path"].replace(SVN_URL, "")] = {
                    external.split(" ")[1]: external.split(" ")[0]
                    for external in target.get("property").get("#text", "").strip().splitlines()
                }
        return externals_dict

    @staticmethod
    def convert_external_svn_path(current_svn_path, svn_relative_path, source_path=None):
        if svn_relative_path.startswith('^'):
            return '{}{}'.format(SVN_URL, svn_relative_path[1:])
        if svn_relative_path.startswith('..'):
            if not source_path:
                current_svn_path = current_svn_path.replace(SVN_URL, "")
                svn_path = os.path.normpath(os.path.join(current_svn_path, svn_relative_path))
            else:
                source_path = source_path.replace(SVN_URL, "")
                svn_path = os.path.normpath(os.path.join(source_path, svn_relative_path))
            return SVN_URL + svn_path.replace('\\', '/')
        raise Exception('Not match svn_relative_path: {}'.format(svn_relative_path))

    def externals2cp(self, remote_url, external_info, source_path=None):
        for k, v in external_info.items():
            for i, j in v.items():
                external_info[k][i] = self.convert_external_svn_path(k, j, source_path=source_path)
        d = flatten_dict(external_info)
        for k, v, in d.items():
            self.cp(v, f'{remote_url}{k}', msg=f'override_externals:{k}')
            v_externals = self.format_externals(self.get_externals(f'{remote_url}{k}'))
            if any(v_externals.items()):
                self.externals2cp(remote_url, v_externals, source_path=source_path)
        for k in external_info.keys():
            self.pe(f'{remote_url}{k}', 'off' if platform.system() == "Windows" else '', 'delete_externals')

    @staticmethod
    def check_target_exist(url):
        proc = SVNCmdRunner(["svn", "info", url])
        if proc.returncode != 0 and "E200009" in proc.error:
            return False
        return True

    def get_real_path(self, url):
        if url.endswith('/'):
            url = url[:-1]
        real_path, index = None, None
        parts = url.split('/')
        for i in range(len(parts), 0, -1):
            _url = '/'.join(parts[:i])
            if self.check_target_exist(_url):
                real_path = _url
                index = i
                break
        else:
            raise CMDException('Param', f'Check the targets:{url} exist')
        lst = parts[index:]
        while lst:
            externals = self.ls(real_path, verbose=True)
            part = next(filter(lambda x: x['name'] == lst[0], externals), None)
            if part is None:
                raise CMDException('Param', f'Check the targets:{url} exist')
            real_path = f"{part['url']}/{part['name']}"
            lst = lst[1:]
        return real_path

    @staticmethod
    def _ls_info(s):
        json_data = xmltodict.parse(s).get("lists").get("list")
        url = json_data["@path"]
        try:
            return [{
                "kind": entry["@kind"],
                "name": entry["name"],
                "revision": entry["commit"]["@revision"],
                "author": entry["commit"]["author"],
                "date": entry["commit"]["date"],
                "url": url
            } for entry in (json_data["entry"] if isinstance(json_data["entry"], list) else [json_data["entry"]])]
        except:
            return []

    def ls(self, url, verbose=False):
        if not verbose:
            runner = SVNCmdRunner(['svn', 'ls', url])
            return runner.output.strip().splitlines()
        else:
            externals = self.format_externals(self.get_externals(url))
            runner = SVNCmdRunner(['svn', 'ls', url, '--xml'])
            result = self._ls_info(runner.output)

            for k, v in externals.items():
                for name, external in v.items():
                    external_url = self.convert_external_svn_path(k, external)
                    runner = SVNCmdRunner(['svn', 'ls', os.path.dirname(external_url), '--xml'])
                    if runner.output:
                        item = next(filter(lambda x: x["name"] == name, self._ls_info(runner.output)), None)
                        result.append(item)

        return result

    def custom_diff(self, o, n, path='./'):
        diff_files = {'added': [], 'removed': [], 'updated': []}
        o_list = self.ls(o, True)
        n_list = self.ls(n, True)

        updated = []

        set1 = {path + item['name'] for item in o_list}
        set2 = {path + item['name'] for item in n_list}

        added = list(set2 - set1)
        removed = list(set1 - set2)

        for item1 in o_list:
            for item2 in n_list:
                if item1['name'] == item2['name']:
                    if item1['revision'] != item2['revision']:
                        updated.append(item2)
                    break
        for item in updated:
            if item.get('kind') == "dir":
                _diff = self.custom_diff(f"{o}{item['name']}/", f"{item['url']}/{item['name']}/",
                                         f"{path}{item['name']}/")
                added.extend(_diff['added'])
                removed.extend(_diff['removed'])
                diff_files['updated'].extend(_diff['updated'])
            else:
                diff_files['updated'].append(path + item['name'])
        diff_files['added'].extend(added)
        diff_files['removed'].extend(removed)
        return diff_files

    @staticmethod
    def diff(o, n):
        cmd = ["svn", "diff", f"--old={o}", f"--new={n}", "--summarize"]
        proc = SVNCmdRunner(cmd)
        if proc.returncode != 0:
            raise CMDException("SVN", proc.error.split(':')[-1])
        return proc.output

    @staticmethod
    def mv(o, n, msg=None):
        if not msg:
            msg = f"mv {o} to {n}"
        cmd = ["svn", "mv", o, n, "-m", msg]
        proc = SVNCmdRunner(cmd)
        if "E160013" in proc.error:
            raise CMDException("Param Error", "Source folder is not exist")

    @staticmethod
    def get_externals(url, r=False):
        cmd = f"svn pg -R svn:externals {url} --xml" if r else f"svn pg svn:externals {url} --xml"
        proc = SVNCmdRunner(cmd)
        if proc.returncode != 0 and "W200017" in proc.error:
            return ""
        return proc.output

    @staticmethod
    def cp(s, n, r="HEAD", msg=None):
        if not msg:
            msg = f"cp"
        SVNCmdRunner(['svn', 'cp', '-r', r, s, n, '-m', msg], quiet=False)

    @staticmethod
    def pe(url, content, msg):
        SVNCmdRunner(['svn', 'pe', 'svn:externals', url, '--editor-cmd', f'echo {content} >', '-m', msg])

    @staticmethod
    def mkdir(url, msg=""):
        proc = SVNCmdRunner(
            ['svn', 'mkdir', url, '-m', fr'{msg}:mkdir'])
        if proc.returncode != 0 and "E160020" in proc.error:
            raise CMDException("Param", "directory already exist, you may try use --force")

    @staticmethod
    def rm(url, msg="rm"):
        SVNCmdRunner(['svn', 'rm', url, '-m', msg])

    @staticmethod
    def checkout(url):
        SVNCmdRunner(['svn', 'co', url], quiet=False)

    @staticmethod
    def switch(url):
        SVNCmdRunner(['svn', 'switch', url], quiet=False)

    @staticmethod
    def info():
        proc = SVNCmdRunner(['svn', 'info'])
        if proc.returncode != 0 and "E155007" in proc.error:
            raise CMDException("SVN", proc.error.split(":")[-1])
        result = proc.output.strip().splitlines()
        return {line.split(": ")[0].lower().replace(" ", "_"): line.split(": ")[1] for line in result}

    @staticmethod
    def export(url, local_path=None):
        cmd = ['svn', 'export', url] if not local_path else ['svn', 'export', url, local_path]
        proc = SVNCmdRunner(cmd)
        if proc.returncode != 0:
            raise CMDException("SVN", proc.error.strip().split(":")[-1])

    @staticmethod
    def add(path, force=False):
        cmd = ['svn', 'add', path] if not force else ['svn', 'add', path, "--force"]
        SVNCmdRunner(cmd, quiet=False)

    @staticmethod
    def commit(path, msg):
        cmd = ['svn', 'commit', path, "-m", msg]
        SVNCmdRunner(cmd, quiet=False)

    @staticmethod
    def cleanup():
        SVNCmdRunner(['svn', 'cleanup', '--remove-unversioned', '--remove-ignored'], quiet=False)

    @staticmethod
    def revert():
        SVNCmdRunner(['svn', 'revert', '-R', '.'], quiet=False)

    def mkdir_if_missing(self, path):
        if self.check_target_exist(path):
            return
        if path.endswith('/'):
            path = path[:-1]
        real_path, index = None, None
        parts = path.split('/')
        for i in range(len(parts), 0, -1):
            _url = '/'.join(parts[:i])
            if self.check_target_exist(_url):
                real_path = _url
                index = i
                break
        else:
            raise CMDException('Param', f'Check the targets:{path} exist')
        lst = parts[index:]
        while lst:
            real_path = os.path.join(real_path, lst[0]).replace('\\', '/')
            self.mkdir(real_path)
            lst = lst[1:]
