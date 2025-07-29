import time
import random

from wxauto import WeChat

wx = WeChat(debug = True)

# 发送消息
who = '文件传输助手'
for i in range(1):
    # 随机休眠1-5秒
    randomTime = random.randint(1, 5)
    print(f"随机休眠{randomTime}！")
    time.sleep(randomTime)

    wx.SendMsg(f'你好测试{i+1}', who)
    
# 获取当前聊天页面（文件传输助手）消息，并自动保存聊天图片
msgs = wx.GetAllMessage(savepic=True)
for msg in msgs:
    print(f"{msg[0]}: {msg[1]}")


print('wxauto测试完成！')
