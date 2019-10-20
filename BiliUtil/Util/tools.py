# coding=utf-8
import os
import re
import sys
import time
import json
import requests
import subprocess
from urllib import parse
from fake_useragent import UserAgent


# from BiliUtil import http_proxy, https_proxy


class Config:
    SET_AS_NAME = 1
    SET_AS_CODE = 2
    SET_AS_PAGE = 3

    HTTP_PROXY = None  # http://user:pass@1.2.3.4:5678
    HTTPS_PROXY = None  # https://user:pass@1.2.3.4:5678

    class Quality:
        V360P = ('16', '流畅 360P')
        V480P = ('32', '清晰 480P')
        V720P = ('64', '高清 720P')
        V720P60 = ('74', '高清 720P60')
        V1080P = ('80', '高清 1080P')
        V1080Px = ('112', '高清 1080P+')
        V1080P60 = ('116', '高清 1080P60')
        INDEX = {
            16: V360P,
            32: V480P,
            64: V720P,
            74: V720P60,
            80: V1080P,
            112: V1080Px,
            116: V1080P60
        }


# ##################  Private  ###################

HEADER = {
    'Host': '',
    'Connection': 'keep-alive',
    'Accept': 'application/json, text/plain, */*',
    'User-Agent': '',
    'Origin': 'https://www.bilibili.com',
    'Referer': '',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
}
USER = {
    'url': 'http://api.bilibili.com/x/space/acc/info',
    'origin': 'https://space.bilibili.com',
    'referer': 'https://space.bilibili.com'
}
USER_VIDEO = {
    'url': 'http://space.bilibili.com/ajax/member/getSubmitVideos',
    'origin': 'https://space.bilibili.com',
    'referer': 'https://space.bilibili.com'
}
ALBUM = {
    'url': 'http://api.bilibili.com/x/web-interface/view',
    'origin': 'https://www.bilibili.com',
    'referer': 'https://www.bilibili.com/video'
}
VIDEO = {
    'url': 'http://api.bilibili.com/x/player/playurl',
    'origin': 'https://www.bilibili.com',
    'referer': 'https://www.bilibili.com/video'
}
CHANNEL = {
    'url': 'http://api.bilibili.com/x/space/channel/video',
    'origin': 'https://space.bilibili.com',
    'referer': 'https://space.bilibili.com'
}
CHANNEL_LIST = {
    'url': 'http://api.bilibili.com/x/space/channel/list',
    'origin': 'https://space.bilibili.com',
    'referer': 'https://space.bilibili.com'
}


def http_header(info_obj):
    header = HEADER.copy()
    useragent_path = os.path.dirname(__file__) + '/fake_useragent.json'
    header['Host'] = parse.urlparse(info_obj['url']).netloc
    header['User-Agent'] = UserAgent(path=useragent_path).random
    header['Origin'] = info_obj['origin']
    header['Referer'] = info_obj['referer']
    return header


def http_get(info_obj, params, cookie=None):
    # 获取代理配置
    proxies = {
        'http': Config.HTTP_PROXY,
        'https': Config.HTTPS_PROXY
    }

    # 获取请求头信息
    new_http_header = http_header(info_obj)
    if cookie is not None:
        if isinstance(cookie, dict):
            cookie = {
                'SESSDATA': cookie['SESSDATA']
            }
        elif isinstance(cookie, str) and len(cookie) > 0:
            for line in cookie.split(';'):
                name, value = line.strip().split('=', 1)
                if name == 'SESSDATA':
                    cookie = {
                        'SESSDATA': value
                    }
                    break
        else:
            cookie = dict()
    else:
        cookie = dict()

    # 尝试进行网络连接
    for times in range(5):
        try:
            http_result = requests.get(url=info_obj['url'], params=params, cookies=cookie,
                                       headers=new_http_header, timeout=5, proxies=proxies)
        except requests.exceptions:
            time.sleep(3)
            continue
        # 尝试理解并验证响应数据
        if http_result.status_code == 200:
            try:
                json_data = json.loads(http_result.text)
            except json.decoder.JSONDecodeError:
                time.sleep(1)
                continue
            if 'code' in json_data and json_data['code'] == 0:
                return json_data
            elif 'status' in json_data and json_data['status'] is True:
                return json_data
            elif json_data['code'] == -404 or json_data['code'] == -403:
                raise RunningError('请求对象异常或被锁定，无法获取')

    raise RunningError('多次网络请求均未能获得数据：{}'.format(info_obj['url']))


def legalize_name(name):
    legal_name = re.sub(r"[\/\\\:\*\?\"\<\>\|\s']", '_', name)
    legal_name = re.sub(r'[‘’]', '_', legal_name)
    if len(legal_name) == 0:
        return 'null'
    return legal_name


def aria2c_pull(aid, path, name, url_list, show_process=False):
    print(json.dumps(list(url_list)))
    # 设置输出信息
    if show_process:
        out_pipe = None
    else:
        out_pipe = subprocess.PIPE
    # 读取代理信息
    proxies = ''
    proxies += ' --http-proxy="{}"'.format(Config.HTTP_PROXY) if Config.HTTP_PROXY is not None else ""
    proxies += ' --https-proxy="{}"'.format(Config.HTTPS_PROXY) if Config.HTTPS_PROXY is not None else ""

    referer = 'https://www.bilibili.com/video/av' + str(aid)
    url = '"{}"'.format('" "'.join(url_list))  # 多个URL并发下载
    shell = 'aria2c -c -k 1M -x {} -d "{}" -o "{}" --referer="{}" {} {}'
    shell = shell.format(len(url_list), path, name, referer, proxies, url)
    process = subprocess.Popen(shell, stdout=out_pipe, stderr=out_pipe, shell=True)
    process.wait()


def ffmpeg_merge(path, section_list, show_process=False):
    if show_process:
        out_pipe = None
    else:
        out_pipe = subprocess.DEVNULL

    # 完成新版本文件的合并
    for name in section_list:
        flv_file = os.path.abspath('{}/{}.flv'.format(path, name))
        aac_file = os.path.abspath('{}/{}.aac'.format(path, name))
        if os.path.exists(flv_file):
            if os.path.exists(aac_file):
                shell = 'ffmpeg -i "{}" -i "{}" -c copy -f mp4 -y "{}"'
                shell = shell.format(flv_file, aac_file, flv_file)
                process = subprocess.Popen(shell, stdout=out_pipe, stderr=out_pipe, shell=True)
                process.wait()
                # os.remove(flv_file)
                # os.remove(aac_file)
            else:
                pass  # 无需合并的旧版本视频
        else:
            raise RunningError('找不到下载的视频文件')

    # """
    # 完成多个片段的合并
    # 拼接模板: ffmpeg -i 1.flv -i 2.flv
    # -filter_complex "[0:0] [0:1] [1:0] [1:1] concat=n=2:v=1:a=1 [v] [a]"
    # -map "[v]" -map "[a]" -f mp4 -c copy -y output.mp4
    # """
    # shell = 'ffmpeg {} -filter_complex "{} concat=n={}:v=1:a=1 [v] [a]" ' \
    #         '-map "[v]" -map "[a]" -f mp4 -y "{}.mp4"'
    # input_file = ['-i "{}.flv"'.format(os.path.abspath('{}/{}'.format(path, name))) for name in section_list]
    # input_track = ["[{}:0] [{}:1]".format(index, index) for index in range(len(section_list))]
    # mp4_file = os.path.abspath('{}/{}.mp4'.format(path, section_list[0][3:]))
    # shell = shell.format(" ".join(input_file), " ".join(input_track), len(section_list), mp4_file)

    """
    完成多个片段的合并
    拼接模板: ffmpeg -i  'concat:01_3947271.flv|02_3947271.flv'  -c copy -f mp4 -y test.mp4
    """
    shell = 'ffmpeg -i "concat:{}" -c copy -f mp4 -y {}.mp4'
    input_file = ['{}.flv'.format(name) for name in section_list]
    shell = shell.format("|".join(input_file), section_list[0][3:])

    process = subprocess.Popen(shell, cwd=path, stdout=out_pipe, stderr=out_pipe, shell=True)
    process.wait()
    sys.stdout.flush()


class ParameterError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class RunningError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
