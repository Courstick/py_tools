#!/usr/bin/env python3
# coding:utf-8

import os


def sort_version(version_list, reverse=False):
    """
      对版本号列表进行排序。

      args:
        version_list: 版本号列表。
        reverse: 是否逆序排序。

      returns:
        排序后的版本号列表。
    """
    try:
        [version_list.remove(i) for i in version_list if i.endswith("_tmp/")]
        version_list.remove("current/")
    except ValueError:
        pass
    version_list = [version.replace("/", "") for version in version_list if version]
    version_list = [[int(part) for part in version.split(".")] for version in version_list]
    sorted_version_list = sorted(version_list, reverse=reverse)
    sorted_version_list = [".".join(str(part) for part in version) for version in sorted_version_list]
    return sorted_version_list


def resolve_relative_path(base_path, rel_path):
    return os.path.normpath(os.path.join(base_path, rel_path))
