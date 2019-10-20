# coding=utf-8
import os
import sys
import copy
import requests
import BiliUtil.Util as Util


class Task:
    def __init__(self, video, output, name, cover=None):
        self.video_info = copy.deepcopy(vars(video))
        del self.video_info['video']
        del self.video_info['audio']
        self.aid = video.aid
        self.level = video.level
        self.video = video.video
        self.audio = video.audio
        self.cover = cover
        self.name = name
        self.path = os.path.abspath(output)

    def start(self, show_process=True, no_repeat=True):
        """
        开始下载任务
        :param show_process: 是否显示下载进度信息
        :param no_repeat: 是否重复下载
        :return: 本次下载的视频所属的av号 / None
        """
        if not os.path.exists(self.path):
            os.makedirs(self.path)  # 创建基础路径
        # 保存视频封面
        if self.cover is not None and not os.path.exists(self.path + '/cover.jpg'):
            proxies = {
                'http': Util.Config.HTTP_PROXY,
                'https': Util.Config.HTTPS_PROXY
            }
            http_result = requests.get(self.cover, proxies=proxies)
            with open(self.path + '/cover.jpg', 'wb') as file:
                file.write(http_result.content)
        # 保存视频并转码
        if no_repeat and os.path.exists(os.path.abspath('{}/{}.mp4'.format(self.path, self.name))):
            return None
        section_list = []
        if self.level == 'old_version':
            for section in self.video:
                section_name = "%02d_%s" % (section, self.name)
                Util.aria2c_pull(self.aid, self.path, section_name + '.flv', self.video[section], show_process)
                section_list.append(section_name)
        elif self.level == 'new_version':
            for section in self.video:
                section_name = "%02d_%s" % (section, self.name)
                Util.aria2c_pull(self.aid, self.path, section_name + '.aac', self.audio[section], show_process)
                Util.aria2c_pull(self.aid, self.path, section_name + '.flv', self.video[section], show_process)
                section_list.append(section_name)
        Util.ffmpeg_merge(self.path, section_list, show_process)
        return self.aid
