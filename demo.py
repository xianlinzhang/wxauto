import time
import random

from wxauto import WeChat

wx = WeChat(debug = True)

# 发送消息
who = '主号'
for i in range(1):
    # 随机休眠1-5秒
    randomTime = random.randint(1, 5)
    print(f"随机休眠{randomTime}！")
    time.sleep(randomTime)

    wx.SendMsg(f'你好测试{i+1}', who)
#
# # 获取当前聊天页面（文件传输助手）消息，并自动保存聊天图片
# msgs = wx.GetAllMessage(savepic=True)
# for msg in msgs:
#     print(f"{msg[0]}: {msg[1]}")


# wx.AddNewFriend("16621053875", addmsg='您好，我是莲城宝平台客服，为您提供广昌相关发布和咨询信息', remark='16621053875', tags=['客户'])


print('wxauto测试完成！')
