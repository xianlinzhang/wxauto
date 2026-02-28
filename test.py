import requests
import threading
import time
import json

from core.redisClient import redisClient
from core.print import print_info, print_error
from wxauto import WeChat


class WeChatMonitor:
    def __init__(self, wx_instance):
        self.wx = wx_instance

    def start_session_monitor(self):
        """启动后台线程监控微信session"""
        self.start_monitoring()
        thread = threading.Thread(target=self._session_monitor_worker, daemon=False)
        thread.start()

    def _session_monitor_worker(self):
        """后台监控微信session的工作者函数"""
        url = "http://127.0.0.1:5030/api/v1/session"

        IgnoreUsernames = "brandsessionholder,gh_edac0ec6a0ba,newsapp,gh_b6f1d17d2ffc,gh_315e955abdf5,brandservicesessionholder"
        # IgnoreUsernames = ""
        params = {
            "format": "json",
            "HasUnreadCount": "1",
            "IgnoreUsernames": IgnoreUsernames
        }

        print_info(f"is_monitoring {self.is_monitoring()}")

        while self.is_monitoring():
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    # 处理返回的数据，可以根据需要进行相应操作
                    data = response.json()
                    self._handle_session_data(data)
            except Exception as e:
                print_error(f"监控请求出错: {e}")
                self.stop_monitoring()

            # 等待2分钟
            time.sleep(120)

    def _handle_session_data(self, data):
        """处理session数据，可根据需要自定义实现"""
        # 这里可以添加处理逻辑，比如根据未读消息数量执行相应操作
        print_info(f"获取到session数据: {data}")

        # 循环处理items中的每个项目
        for item in data.get("items", []):
            # 构造chatlog API的请求参数
            chatlog_params = {
                "time": "last-2d",
                "talker": item["userName"],
                "sender": item["userName"],
                # "limit": item["UnreadCount"],
                "format": "json"
            }

            # 请求chatlog API
            try:
                chatlog_response = requests.get(
                    "http://127.0.0.1:5030/api/v1/chatlog",
                    params=chatlog_params,
                    timeout=10
                )
                if chatlog_response.status_code == 200:
                    chatlog_data = chatlog_response.json()
                    print_info(f"获取到聊天记录: {chatlog_data}")

                    # 如果chatlog_data是一个列表，循环处理每个消息的content
                    if isinstance(chatlog_data, list):
                        # 将chatlog_data 数据放到redis 中, 键为item["userName"]，值为chatlog_data, 需要和redis 已有的值进行合并，根据seq区分是否重复的
                        # 从Redis获取已有的数据
                        existing_data = redisClient.get(item["userName"])
                        if existing_data:
                            try:
                                existing_data = json.loads(existing_data)
                                # 确保existing_data是列表格式
                                if not isinstance(existing_data, list):
                                    existing_data = [existing_data]
                            except (json.JSONDecodeError, TypeError):
                                existing_data = []
                        else:
                            existing_data = []

                        # 创建一个集合来存储已有的seq值，用于快速去重
                        existing_seqs = {msg.get("seq") for msg in existing_data if
                                         isinstance(msg, dict) and "seq" in msg}

                        needAutoReplyFreeRide = False
                        autoReplyContent = '好的，收到，我们会及时发布的哈'
                        # 合并新数据，只添加seq不重复的消息
                        for message in chatlog_data:
                            if isinstance(message, dict) and "seq" in message:
                                if message["seq"] not in existing_seqs:
                                    if "提供车" in message["content"] or "求车" in message["content"]:
                                        needAutoReplyFreeRide = True
                                        self._send_to_free_ride_api(message, autoReplyContent)
                                        message['autoReplayContent'] = autoReplyContent
                                        message['autoReplayStatus'] = 1
                                    else :
                                        print_info(f"content: {message['content']} ; 不是提供车、求车信息")
                                        message['autoReplayContent'] = ""
                                        message['autoReplayStatus'] = 0

                                    message["autoCheck"] = 1
                                    existing_seqs.add(message["seq"])
                                    existing_data.append(message)

                        # 求车和拼车信息自动回复
                        if needAutoReplyFreeRide:
                            self.auto_reply_request_and_deal_free_ride(item, autoReplyContent)

                        # 将合并后的数据存回Redis
                        redisClient.set(item["userName"], json.dumps(existing_data, ensure_ascii=False))

            except Exception as e:
                print_error(f"获取聊天记录出错: {e}")

        # 最小化
        # self.wx.ClickMinimizeIcon()

    def _send_to_free_ride_api(self, item, autoReplyContent):
        """发送数据到拼车信息API"""
        url = "https://wemprss.liancb.cn/api/v1/wx/free-ride"

        from datetime import datetime

        # 假设 item['time'] 的值是 "2025-08-30T00:55:29+08:00"
        time_str = item['time']

        # 解析时间字符串
        dt = datetime.fromisoformat(time_str)

        # 格式化为年月日
        push_date = dt.strftime("%Y-%m-%d")

        payload = {
            "original_content": item['content'],
            "car_type": "",
            "departure": "",
            "destination": "",
            "time_str": "",
            "hours_str": "",
            "phone": "",
            "num_people": "",
            "push_date": push_date
        }

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
            "Connection": "keep-alive",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            print_info(f"发送拼车信息结果: {response.text}")

        except Exception as e:
            print_error(f"发送拼车信息出错: {e}")

    def auto_reply_request_and_deal_free_ride(self, item, autoReplyContent):

        # 自动回复
        userName = item['userName']
        contact = self.get_contact_or_update_from_redis(userName)
        if contact:
            print_info(f"对{userName}发送自动回复: {autoReplyContent}")

            talker = contact.get('remark') if contact.get('remark') else contact.get("nickName")

            self.wx.SendMsg(autoReplyContent, who=talker)
        else:
            print_error(f"未找到{userName}联系人信息")

    def get_contact_or_update_from_redis(self, username):
        """从Redis中获取联系人信息，如果不存在则更新并返回"""
        # http://127.0.0.1:5030/api/v1/contact?format=json&isFriend=1

        # 先尝试从Redis中获取联系人信息
        contacts_data = redisClient.get("Contacts")

        if contacts_data:
            try:
                contacts = json.loads(contacts_data)
                if isinstance(contacts, list):
                    # 查找指定username的联系人
                    for contact in contacts:
                        if isinstance(contact, dict) and contact.get("userName") == username:
                            return contact
            except (json.JSONDecodeError, TypeError):
                pass

        # 如果Redis中没有数据或未找到指定联系人，则从API获取并更新Redis
        try:
            url = "http://127.0.0.1:5030/api/v1/contact"
            params = {
                "format": "json",
                "isFriend": "1"
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                contacts = data.get("items", [])

                # 将联系人数据存入Redis
                redisClient.set("Contacts", json.dumps(contacts, ensure_ascii=False))

                # 查找并返回指定username的联系人
                for contact in contacts:
                    if isinstance(contact, dict) and contact.get("userName") == username:
                        return contact
        except Exception as e:
            print_error(f"获取联系人信息出错: {e}")

        # 如果未找到指定联系人，返回None
        return None

    def stop_monitoring(self):
        """停止监控"""
        redisClient.set("WeChatMonitorStatus", "0")

    def start_monitoring(self):
        """停止监控"""
        redisClient.set("WeChatMonitorStatus", "1")

    def is_monitoring(self):
        """判断是否正在监控"""
        status = redisClient.get("WeChatMonitorStatus")

        # 处理各种可能的数据类型
        if status is None:
            return False
        elif isinstance(status, bytes):
            status = status.decode('utf-8')

        return str(status) == "1"


if __name__ == '__main__':
    wx = WeChat(debug = True)

    # 创建并启动监控器
    # monitor = WeChatMonitor(wx_instance=wx)
    # monitor.start_session_monitor()


    # 发布朋友圈信息
    message = """招聘：
后厨工、
操作工、
煮面工。
月薪3000+。
岗位要求：35岁以下，手脚勤快，认字等，有经验者优先。
联系方式：13122033112(陈店长)(微信同号，有意联系)
工作地点：广昌县颐和花园刘文祥麻辣烫"""
    wx.MomentsReleaseMessage(message)

    # wx.ignoreUpdate()
