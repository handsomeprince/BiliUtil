# coding=utf-8
import copy
import BiliUtil.Util as Util


class Video:
    def __init__(self, aid, cid, name, page):
        self.aid = str(aid)
        self.cid = str(cid)
        self.name = name
        self.page = page
        self.quality = None
        self.length = None
        self.format = None
        self.height = None
        self.width = None
        self.level = None
        self.video = None
        self.audio = None

    def sync(self, cookie=None, quality=None):
        # 检验必要的参数
        if self.aid is None or self.cid is None:
            raise Util.ParameterError('缺少获取视频信息的必要参数')

        if quality is None:
            quality = Util.Config.Quality.V1080P60

        # 发送网络请求
        http_request = {
            'info_obj': Util.VIDEO,
            'params': {
                'avid': str(self.aid),
                'cid': str(self.cid),
                'qn': quality[0],
                'otype': 'json',
                'fnver': 0,
                'fnval': 16
            },
            'cookie': cookie
        }
        json_data = Util.http_get(**http_request)

        # 自动识别不同的数据
        self.video = dict()
        self.audio = dict()
        self.format = json_data['data']['format']
        self.length = json_data['data']['timelength']
        self.quality = Util.Config.Quality.INDEX[json_data['data']['quality']]
        if 'dash' in json_data['data']:
            self.level = 'new_version'
            video_obj = json_data['data']['dash']['video'][0]
            audio_obj = json_data['data']['dash']['audio'][0]
            self.height = video_obj['height']
            self.width = video_obj['width']
            self.video[1] = [video_obj['baseUrl']]
            self.audio[1] = [audio_obj['baseUrl']]
            if video_obj['backup_url']:
                for backup in video_obj['backup_url']:
                    self.video[1].append(backup)
            if audio_obj['backup_url']:
                for backup in audio_obj['backup_url']:
                    self.audio[1].append(backup)
        elif 'durl' in json_data['data']:
            self.level = 'old_version'
            # 视频分段控制
            for index, section in enumerate(json_data['data']['durl']):
                self.video[index + 1] = list([section['url']])
                if section['backup_url']:
                    for backup in section['backup_url']:
                        self.video[index + 1].append(backup)

        # 返回视频信息
        return copy.deepcopy(vars(self))
