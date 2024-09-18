import os
import csv
from linebot.api import LineBotApiError
import math
import numpy as np
from datetime import datetime, timedelta
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import matplotlib.patches as mpatches
from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
import pyimgur
import time
import schedule 
import re
from matplotlib import rcParams
from threading import Lock
from apscheduler.schedulers.background import BackgroundScheduler
from linebot.models import TextSendMessage, MessageEvent, TextMessage,DatetimePickerAction, TemplateSendMessage, ButtonsTemplate,FlexSendMessage
import matplotlib.font_manager as fm
from matplotlib.font_manager import FontProperties

CLIENT_ID = "122aba7e3e3f13a"
PATH = 'report2.png'
gettime = "08:00" #先定義一個初始值

app = Flask(__name__)

line_bot_api = LineBotApi("+vszRtjsTxuPM6653PLxHCoGzgbRMKVkTOd8XwdbIlpQ1cqv8LQ3z2F5C2Zdi2hMvWomMnloLp8/40rNFdCQkm4f6v1kte5s1+76wS+9kQ+M1rtvBVjujh12WpDB1Qc9Z/2NpB+NX5D3THH76HDAYwdB04t89/1O/w1cDnyilFU=")
handler = WebhookHandler("9a31037c985e085e319ec091700885c8")

@ app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'
@ handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id  #獲取用戶的User ID
    print(f"User ID: {user_id}")  # print User ID 到控制台

    """根據用戶的消息來處理註冊、查詢報告等功能"""
    user_id = event.source.user_id  # 獲取使用者的 LINE UID
    user_message = event.message.text.strip()  # 獲取並去除前後空格的消息
    users = load_user_data()  # 從 CSV 加載使用者資料
    user_record = next((user for user in users if user['uid'] == user_id), None)  # 查找當前使用者的記錄
    answer = qa_dict.get(user_message, None)  
    if answer:
        response_message = TextSendMessage(text=answer)
        line_bot_api.reply_message(event.reply_token, response_message)

    if user_message.lower() == "start":
        if user_record:
            # 已註冊使用者，回應其角色
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"你已經註冊過了，你的角色是：{user_record['role']}")
            )
        else:
            # 未註冊使用者，提示註冊
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請回覆 'register doctor' 或 'register patient' 來進行註冊。")
            )
    elif user_message.lower().startswith("register "):
        # 處理註冊請求
        role = user_message.split(" ")[1]  # 獲取角色（醫師或病患）
        if role.lower() not in ["doctor", "patient"]:
            # 如果角色無效，回應錯誤信息
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入正確的角色：doctor 或 patient。")
            )
            return
        if user_record:
            # 已註冊的使用者不能更改角色
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="你已經註冊過了，不能更改角色。")
            )
            return

        try:
            # 從 LINE 獲取使用者的顯示名稱
            profile = line_bot_api.get_profile(user_id)
            user_name = profile.display_name
        except LineBotApiError:
            user_name = "Unknown"

        # 記錄註冊時間並更新資料
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_user = {
            'uid': user_id,
            'name': user_name,
            'role': role.capitalize(),
            'registration_time': current_time,
            'last_update_time': current_time,
            'report_steps': '',
            'report_heart_rate': ''
        }
        users.append(new_user)
        save_user_data(users)  
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"你已成功註冊為 {role.capitalize()}。")
        )
    elif user_message == '查看所有病患報告':
        # 醫師查看所有病患報告的請求
        if user_record and user_record['role'] == 'Doctor':
            patient_reports = get_all_patient_reports(users)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=patient_reports)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="您沒有權限查看所有病患報告。")
            )
    elif user_message.startswith("查詢病患"):
        # 醫師查詢特定病患報告的請求
        if user_record and user_record['role'] == 'Doctor':
            try:
                patient_name = user_message[5:].strip()  # 獲取病患名稱
                if not patient_name:
                    raise ValueError("未提供病患名稱")

                # 調試信息，列出所有病患名稱以確認
                print(f"查詢的病患名稱: {patient_name}")
                print(f"CSV 中的病患名稱列表: {[user['name'] for user in users]}")

                patient_report = get_patient_report_by_name(users, patient_name)
                if patient_report:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=patient_report)
                    )
                else:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"找不到名為 {patient_name} 的病患。")
                    )
            except ValueError:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請提供病患名字。例如：'查詢病患 張三'")
                )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="您沒有權限查詢病患報告。")
            )
    elif user_message == '查看我的報告':
        # 病患查看自己報告的請求
        if user_record and user_record['role'] == 'Patient':
            patient_report = get_patient_report(user_record)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=patient_report)
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="只有病患可以查看自己的報告。")
            )
    ###先註解掉不然會跟其他指令發生衝突
    # else:
    #     # 未知指令的處理
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         TextSendMessage(text="未知的指令，請發送 'start' 開始或 'register doctor' 或 'register patient' 進行註冊。")
    #     )
    if event.message.text == "a":
        msg = (TextSendMessage(text='這是測試aaa'))
        line_bot_api.reply_message(event.reply_token, msg)
    elif event.message.text == '榮譽勳章':
        reply_message = TextSendMessage(
            text="請選擇你想查看的內容：",
            quick_reply=get_quick_reply_buttons()
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
    elif user_message == '今日步數':
        send_today_steps(event)
    elif user_message == "勳章款式":
        send_badge_styles(event)
    elif user_message == "已達成勳章":
        send_achieved_badges(event)
    # elif user_message == "特殊勳章":
    #     line_bot_api.reply_message(
    #         event.reply_token,
    #         TextSendMessage(text="特殊勳章還在研發中")
    #     )
    elif user_message == "5000步勳章":
        send_5000_steps_badge(event)
    elif user_message == "8000步勳章":
        send_8000_steps_badge(event)
    elif user_message == "10000步勳章":
        send_10000_steps_badge(event)
    elif event.message.text == '日報表顯示': #快速選單內容
        message = TextSendMessage(
        text='請選擇一個選項',
        quick_reply=QuickReply(
           items=[
                QuickReplyButton(
                    action=MessageAction(label="心率", text="日報表心率")
                ),
                QuickReplyButton(
                    action=MessageAction(label="睡眠", text="日報表睡眠")
                ),
                QuickReplyButton(
                    action=MessageAction(label="活動", text="日報表活動")
                ),
                QuickReplyButton(
                    action=MessageAction(label="疲勞", text="日報表疲勞")
                ),
                QuickReplyButton(
                    action=MessageAction(label="全部", text="日報表全部")
                )
            ]
        )
        )
        line_bot_api.reply_message(event.reply_token, message)
    elif event.message.text == '周報表顯示': #快速選單內容
        message = TextSendMessage(
        text='請選擇一個選項',
        quick_reply=QuickReply(
           items=[
                QuickReplyButton(
                    action=MessageAction(label="心率", text="周報表心率")
                ),
                QuickReplyButton(
                    action=MessageAction(label="睡眠", text="周報表睡眠")
                ),
                QuickReplyButton(
                    action=MessageAction(label="活動", text="周報表活動")
                ),
                QuickReplyButton(
                    action=MessageAction(label="疲勞", text="周報表疲勞")
                ),
                QuickReplyButton(
                    action=MessageAction(label="全部", text="周報表全部")
                )
            ]
        )
        )
        line_bot_api.reply_message(event.reply_token, message)
    elif event.message.text == '報表設定': #快速選單內容
        message = TextSendMessage(
        text='請選擇一個選項',
        quick_reply=QuickReply(
           items=[
                QuickReplyButton(
                    action=MessageAction(label="早上8:00傳送報表", text="早上8:00傳送報表")
                ),
                QuickReplyButton(
                    action=MessageAction(label="中午12:00傳送報表", text="中午12:00傳送報表")
                ),
                QuickReplyButton(
                    action=MessageAction(label="下午16:00傳送報表", text="下午16:00傳送報表")
                ),
                QuickReplyButton(
                    action=MessageAction(label="晚上20:00傳送報表", text="晚上20:00傳送報表")
                )
            ]
        )
        )
        line_bot_api.reply_message(event.reply_token, message)
    elif event.message.text == '日報表心率':
        buttons_template = ButtonsTemplate(
            text="請選擇日期",
            actions=[
                DatetimePickerAction(
                    label="選擇日期",
                    data="report_type=heartrateday&action=select_date",
                    mode="date"  # "datetime" 可以用來選擇日期和時間，"time" 只選擇時間
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇日期",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    elif event.message.text =='周報表心率':
        buttons_template = ButtonsTemplate(
            text="請選擇日期",
            actions=[
                DatetimePickerAction(
                    label="選擇日期",
                    data="report_type=heartrateweek&action=select_date",
                    mode="date"  # "datetime" 可以用來選擇日期和時間，"time" 只選擇時間
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇日期",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    elif event.message.text =='日報表睡眠':
        buttons_template = ButtonsTemplate(
            text="請選擇日期",
            actions=[
                DatetimePickerAction(
                    label="選擇日期",
                    data="report_type=sleepday&action=select_date",
                    mode="date"  # "datetime" 可以用來選擇日期和時間，"time" 只選擇時間
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇日期",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    elif event.message.text =='周報表睡眠':
        buttons_template = ButtonsTemplate(
            text="請選擇日期",
            actions=[
                DatetimePickerAction(
                    label="選擇日期",
                    data="report_type=sleepweek&action=select_date",
                    mode="date"  # "datetime" 可以用來選擇日期和時間，"time" 只選擇時間
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇日期",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    elif event.message.text =='日報表活動':
        buttons_template = ButtonsTemplate(
            text="請選擇日期",
            actions=[
                DatetimePickerAction(
                    label="選擇日期",
                    data="report_type=activityday&action=select_date",
                    mode="date"  # "datetime" 可以用來選擇日期和時間，"time" 只選擇時間
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇日期",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    elif event.message.text =="周報表活動":
        buttons_template = ButtonsTemplate(
            text="請選擇日期",
            actions=[
                DatetimePickerAction(
                    label="選擇日期",
                    data="report_type=activityweek&action=select_date",
                    mode="date"  # "datetime" 可以用來選擇日期和時間，"time" 只選擇時間
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇日期",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    elif event.message.text =='日報表疲勞':
        buttons_template = ButtonsTemplate(
            text="請選擇日期",
            actions=[
                DatetimePickerAction(
                    label="選擇日期",
                    data="report_type=fatigueday&action=select_date",
                    mode="date"  # "datetime" 可以用來選擇日期和時間，"time" 只選擇時間
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇日期",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)          
    elif event.message.text =='周報表疲勞':
        buttons_template = ButtonsTemplate(
            text="請選擇日期",
            actions=[
                DatetimePickerAction(
                    label="選擇日期",
                    data="report_type=fatigueweek&action=select_date",
                    mode="date"  # "datetime" 可以用來選擇日期和時間，"time" 只選擇時間
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇日期",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    elif event.message.text =='日報表全部':
        buttons_template = ButtonsTemplate(
            text="請選擇日期",
            actions=[
                DatetimePickerAction(
                    label="選擇日期",
                    data="report_type=allreportday&action=select_date",
                    mode="date"  # "datetime" 可以用來選擇日期和時間，"time" 只選擇時間
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇日期",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    elif event.message.text =='周報表全部':
        buttons_template = ButtonsTemplate(
            text="請選擇日期",
            actions=[
                DatetimePickerAction(
                    label="選擇日期",
                    data="report_type=allreportweek&action=select_date",
                    mode="date"  # "datetime" 可以用來選擇日期和時間，"time" 只選擇時間
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="請選擇日期",
            template=buttons_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    elif event.message.text == "早上8:00傳送報表":
        global gettime
        gettime = "08:00"
        with open("./user_ids.txt", "a") as file:
            file.write(user_id + "," + gettime + "\n")
    elif event.message.text == "中午12:00傳送報表":
        gettime = "12:00"
        with open("./user_ids.txt", "a") as file:
            file.write(user_id + "," + gettime + "\n")
    elif event.message.text == "下午16:00傳送報表":
        gettime = "16:00"
        with open("./user_ids.txt", "a") as file:
            file.write(user_id + "," + gettime + "\n")
    elif event.message.text == "晚上20:00傳送報表":
        gettime = "20:00"
        with open("./user_ids.txt", "a") as file:
            file.write(user_id + "," + gettime + "\n")
    elif event.message.text == 'QA': #QA快速選單內容
        message = TextSendMessage(
        text='請選擇一個選項',
        quick_reply=QuickReply(
            items=[
                QuickReplyButton(
                    action=MessageAction(label="心率", text="心率常見問題")
                ),
                QuickReplyButton(
                    action=MessageAction(label="睡眠", text="睡眠常見問題")
                ),
                QuickReplyButton(
                    action=MessageAction(label="活動", text="活動常見問題")
                ),
                QuickReplyButton(
                    action=MessageAction(label="疲勞", text="疲勞常見問題")
                )
            ]
        )
        )
        line_bot_api.reply_message(event.reply_token, message)
    elif event.message.text == '睡眠常見問題':
        flex_sleep_qa(event)
    elif event.message.text == '心率常見問題':
        flex_hr_qa(event)
    elif event.message.text == '活動常見問題':
        flex_activity_qa(event)
    elif event.message.text == '疲勞常見問題':
        flex_fatigue_qa(event)
    else : 
        msg2 = (TextSendMessage(text='失敗'))
        line_bot_api.reply_message(event.reply_token, msg2)
#榮譽勳章
def get_quick_reply_buttons():
    quick_reply_buttons = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="今日步數", text="今日步數")),
        QuickReplyButton(action=MessageAction(label="勳章款式", text="勳章款式")),
        QuickReplyButton(action=MessageAction(label="已達成勳章", text="已達成勳章")),
        # QuickReplyButton(action=MessageAction(label="特殊勳章", text="特殊勳章"))
    ])
    return quick_reply_buttons
def send_badge_styles(event):
    quick_reply_buttons = QuickReply(items=[
        QuickReplyButton(action=MessageAction(label="5000步勳章", text="5000步勳章")),
        QuickReplyButton(action=MessageAction(label="8000步勳章", text="8000步勳章")),
        QuickReplyButton(action=MessageAction(label="10000步勳章", text="10000步勳章")),
        # QuickReplyButton(action=MessageAction(label="特殊勳章圖", text="特殊勳章圖")),
    ])
    reply_message = TextSendMessage(text="請選擇一個勳章類型：", quick_reply=quick_reply_buttons)
    line_bot_api.reply_message(event.reply_token, reply_message)
def award_badge_manually(event):
    try:
        achieved_badges = "5000步勳章 連續1天"
        with open('achieved_badges.txt', 'a') as file:
            file.write(f"{achieved_badges}\n")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"強制給予勳章：{achieved_badges}！")
        )
    except Exception as e:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"發生錯誤: {str(e)}")
        )
def remove_all_badges(event):
    try:
        if os.path.exists('achieved_badges.txt'):
            os.remove('achieved_badges.txt')
            response_message = "所有勳章已被移除。"
        else:
            response_message = "尚未有勳章記錄。"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_message)
        )
    except Exception as e:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"發生錯誤: {str(e)}")
        )
def send_today_steps(event):
    try:
        data = pd.read_csv("./dailyActivity.csv")
        df = pd.DataFrame(data)
        df['ActivityDate'] = pd.to_datetime(df['ActivityDate'])
        df.set_index('ActivityDate', inplace=True)
        
        #today = pd.to_datetime('today').normalize()
        today = '2024-05-27'
        df_today = df.loc[today]
        
        total_steps = df_today['Step'].sum()
        
        if total_steps >= 5000:
            reply_text = f'今日步數：{total_steps} 步\n很棒！已達成每日基礎步數。'
        else:
            steps_to_5000 = 5000 - total_steps
            reply_text = f'今日步數：{total_steps} 步\n還差 {steps_to_5000} 步達到5000步'
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as e:
        error_message = f'處理數據時發生錯誤：{str(e)}'
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=error_message)
        )
#已達成的勳章
def send_achieved_badges(event):
    try:
        # 定義正則表達式來提取步數和連續天數
        badge_pattern = re.compile(r'(\d+)步勳章 連續(\d+)天')

        if os.path.exists('achieved_badges.txt'):
            with open('achieved_badges.txt', 'r') as file:
                achieved_badges = file.readlines()

            # 去除重複的勳章
            unique_badges = list(dict.fromkeys(achieved_badges))

            # 提取步數和連續天數並排序
            badges_info = []
            for badge in unique_badges:
                match = badge_pattern.search(badge)
                if match:
                    steps = int(match.group(1))
                    days = int(match.group(2))
                    badges_info.append((steps, days, badge.strip()))
            # 根據步數和連續天數進行排序（升序）
            badges_info.sort(key=lambda x: (x[0], x[1]))

            # 生成排序後的勳章文本
            if badges_info:
                achieved_badges_text = '\n'.join(badge for _, _, badge in badges_info)
            else:
                achieved_badges_text = '尚未達成任何勳章。'
        else:
            achieved_badges_text = '尚未達成任何勳章。'
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"已達成的勳章：\n{achieved_badges_text}")
        )
    except Exception as e:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"發生錯誤: {str(e)}")
        )
def send_5000_steps_badge(event):
    try:
        image_carousel_template = ImageCarouselTemplate(
            columns=[
                ImageCarouselColumn(
                    image_url="https://i.imgur.com/1bQ0rHo.jpeg",
                    action=MessageAction(label="5000步 1天", text="查看5000步勳章 連續1天")
                ),
                ImageCarouselColumn(
                    image_url="https://i.imgur.com/GmnnrJN.png",
                    action=MessageAction(label="5000步 7天", text="查看5000步勳章 連續7天")
                ),
                ImageCarouselColumn(
                    image_url="https://i.imgur.com/GmnnrJN.png",
                    action=MessageAction(label="5000步 14天", text="查看5000步勳章 連續14天")
                ),
                ImageCarouselColumn(
                    image_url="https://i.imgur.com/GmnnrJN.png",
                    action=MessageAction(label="5000步 30天", text="查看5000步勳章 連續30天")
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="5000步勳章款式",
            template=image_carousel_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"發生錯誤: {str(e)}"))
def send_8000_steps_badge(event):
    try:
        image_carousel_template = ImageCarouselTemplate(
            columns=[
                ImageCarouselColumn(
                    image_url="https://i.imgur.com/GmnnrJN.png",
                    action=MessageAction(label="8000步 1天", text="查看8000步勳章 連續1天")
                ),
                ImageCarouselColumn(
                    image_url="https://i.imgur.com/GmnnrJN.png",
                    action=MessageAction(label="8000步 7天", text="查看8000步勳章 連續7天")
                ),
                ImageCarouselColumn(
                    image_url="https://i.imgur.com/GmnnrJN.png",
                    action=MessageAction(label="8000步 14天", text="查看8000步勳章 連續14天")
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="8000步勳章款式",
            template=image_carousel_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"發生錯誤: {str(e)}"))
def send_10000_steps_badge(event):
    try:
        image_carousel_template = ImageCarouselTemplate(
            columns=[
                ImageCarouselColumn(
                    image_url="https://i.imgur.com/GmnnrJN.png",
                    action=MessageAction(label="10000步 1天", text="查看10000步勳章 連續1天")
                ),
                ImageCarouselColumn(
                    image_url="https://i.imgur.com/GmnnrJN.png",
                    action=MessageAction(label="10000步 7天", text="查看10000步勳章 連續7天")
                )
            ]
        )
        template_message = TemplateSendMessage(
            alt_text="10000步勳章款式",
            template=image_carousel_template
        )
        line_bot_api.reply_message(event.reply_token, template_message)
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"發生錯誤: {str(e)}"))
# 檢查是否達成勳章
def check_and_send_badges():
    try:
        # 讀取CSV文件創建DataFrame
        data = pd.read_csv('./dailyActivity.csv')
        df = pd.DataFrame(data)
        
        # 确保 'ActivityDate' 列是日期格式
        df['ActivityDate'] = pd.to_datetime(df['ActivityDate'])
        df['Date'] = df['ActivityDate'].dt.date
        
        # 按日期分组記算每天的步数總和
        df_daily = df.groupby('Date')['Step'].sum().reset_index()
        df_daily.set_index('Date', inplace=True)

        #today = pd.to_datetime('today').normalize()
        today = '2024-05-27'  # 用于測試
        today_date = pd.to_datetime(today).date()

        # 定義不同天數和步數的勳章圖片
        badge_images = {
            (5000, 30): 'https://i.imgur.com/GmnnrJN.png',
            (5000, 14): 'https://i.imgur.com/GmnnrJN.png',
            (5000, 7): 'https://i.imgur.com/GmnnrJN.png',
            (8000, 30): 'https://i.imgur.com/GmnnrJN.png',
            (8000, 14): 'https://i.imgur.com/GmnnrJN.png',
            (8000, 7): 'https://i.imgur.com/GmnnrJN.png',
            (10000, 30): 'https://i.imgur.com/GmnnrJN.png',
            (10000, 14): 'https://i.imgur.com/GmnnrJN.png',
            (10000, 7): 'https://i.imgur.com/GmnnrJN.png'
        }

        # 加载已发送的勳章列表
        if os.path.exists('achieved_badges.txt'):
            with open('achieved_badges.txt', 'r') as file:
                sent_badges = set(line.strip() for line in file.readlines())
        else:
            sent_badges = set()
        
        # Check for 7 consecutive days with less than 5000 steps
        seven_days_ago = today_date - timedelta(days=7)
        df_last_seven_days = df_daily.loc[seven_days_ago:today_date]

        if all(df_last_seven_days['Step'] < 5000) and df_daily.loc[today_date, 'Step'] >= 5000:
            welcome_back_image_url = 'https://i.imgur.com/4Jg0TSW.jpeg'
            line_bot_api.broadcast(TextSendMessage(text=f"歡迎回來！今天你已經達到{df_daily.loc[today_date, 'Step']}步！"))
            line_bot_api.broadcast(ImageSendMessage(original_content_url=welcome_back_image_url, preview_image_url=welcome_back_image_url))

        # 保存已發送的勳章列表
        sent_badges = set()

        # 檢查過去30天、14天和7天的步数
        for steps in [10000, 8000, 5000]:  # 先檢查10000步，再檢查8000步，最後檢查5000步
            for days in [30, 14, 7]:
                start_date = today_date - timedelta(days=days-1)
                df_period = df_daily.loc[start_date:today_date]

                # 確保在過去的 days 天内，每天步數至少為 steps
                if len(df_period) == days and all(df_period['Step'] >= steps):
                    badge = f"{steps}步勳章 連續{days}天"
                    image_url = badge_images[(steps, days)]

                    # 确保不重复发送相同勋章
                    if badge not in sent_badges:
                        # 發送勳章信息和圖片
                        line_bot_api.broadcast(TextSendMessage(text=f"恭喜！你已連續{days}天每天達到至少{steps}步，獲得{badge}！"))
                        line_bot_api.broadcast(ImageSendMessage(original_content_url=image_url, preview_image_url=image_url))

                        # 紀錄達成的勳章
                        with open('achieved_badges.txt', 'a') as file:
                            file.write(f"{badge}\n")

                        # 標記勳章已發送
                        sent_badges.add(badge)
        # 檢查今天的步数
        total_steps = df_daily.loc[today_date, 'Step']
        # 檢查並發送今天的勳章
        badges_today = []
        if total_steps >= 10000:
            badges_today.append(("10000步勳章 連續1天", 'https://i.imgur.com/GmnnrJN.png'))
        if total_steps >= 8000:
            badges_today.append(("8000步勳章 連續1天", 'https://i.imgur.com/GmnnrJN.png'))
        if total_steps >= 5000:
            badges_today.append(("5000步勳章 連續1天", 'https://i.imgur.com/1bQ0rHo.jpeg'))
        for badge, image_url in badges_today:
            if badge not in sent_badges:
                line_bot_api.broadcast(TextSendMessage(text=f"恭喜！你今天的步數已達到{total_steps}步，獲得{badge}！"))
                line_bot_api.broadcast(ImageSendMessage(original_content_url=image_url, preview_image_url=image_url))
                # 紀錄達成的勳章
                with open('achieved_badges.txt', 'a') as file:
                    file.write(f"{badge}\n")
                # 標記勳章為已發送
                sent_badges.add(badge)
    except Exception as e:
        error_message = f'檢查勳章時發生錯誤：{str(e)}'
        print(error_message)
        with open('error_log.txt', 'a') as log_file:
            log_file.write(f"{pd.to_datetime('today')}: {error_message}\n")
# 設定每天晚上10點檢查
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_badges, 'cron', hour=22, minute=00)
scheduler.start()

def send_scheduled_message(user_id):
    try:
        message = TextSendMessage(text="這是一條定時訊息")
        line_bot_api.push_message(user_id, message)
        print(f"Message sent to {user_id}")
    except Exception as e:
        print(f"發送訊息時出現錯誤: {e}")

def schedule_jobs():
    file_path = "./user_ids.txt"
    if not os.path.exists(file_path):
        print("File not found!")
        return
    
    # Step 1: 读取文件内容并将其存储在字典中
    user_data = {}
    with open(file_path, "r") as file:
        lines = file.readlines()
    
    for line in lines:
        user_id, gettime = line.strip().split(',')
        # Step 2: 更新字典，以保留最新的时间
        user_data[user_id] = gettime

    # Step 3: 將更新後的資料寫回txt檔
    with open(file_path, "w") as file:
        for user_id, gettime in user_data.items():
            file.write(f"{user_id},{gettime}\n")

    # Step 4: 為每個不同的user_id安排定時
    for user_id, gettime in user_data.items():
        print(f"Scheduling message for {user_id} at {gettime}")
        schedule.every().day.at(gettime).do(send_scheduled_message, user_id=user_id)

def check_for_updates():
    schedule_jobs()  # 更新排程
#群組
# 用於防止多線程下競爭條件的鎖
csv_lock = Lock()

def load_user_data():
    """從 CSV 檔案讀取使用者資料，如果檔案不存在則返回空列表"""
    try:
        with open('user_data1111.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            return list(reader)
    except FileNotFoundError:
        return []
def save_user_data(users):
    """將使用者資料儲存到 CSV 檔案，確保多線程下的資料安全性"""
    try:
        with csv_lock:
            with open('user_data1111.csv', 'w', newline='', encoding='utf-8') as file:
                fieldnames = ['uid', 'name', 'role', 'registration_time', 'last_update_time', 'report_steps', 'report_heart_rate']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(users)
            app.logger.info(f"User data saved successfully.")
    except Exception as e:
        app.logger.error(f"Error saving user data to CSV: {e}")
def get_all_patient_reports(users):
    """獲取所有病患的報告"""
    patients = [user for user in users if user['role'] == 'Patient']
    report_texts = []
    for patient in patients:
        report = f"病患 {patient['name']} 的報告: 步數: {patient['report_steps']}, 心率: {patient['report_heart_rate']}."
        report_texts.append(report)
    return "\n".join(report_texts)
def get_patient_report(patient):
    """獲取單個病患的報告"""
    return f"你的報告: 步數: {patient['report_steps']}, 心率: {patient['report_heart_rate']}."
def get_patient_report_by_name(users, patient_name):
    """通過病患名字獲取病患的報告"""
    patient = next((user for user in users if user['role'] == 'Patient' and user['name'] == patient_name), None)
    if patient:
        return f"病患 {patient['name']} 的報告: 步數: {patient['report_steps']}, 心率: {patient['report_heart_rate']}."
    return None

@handler.add(PostbackEvent)
def handle_postback(event):
    #日心律
    def funheartrateday(start_date):
        data = pd.read_csv('./heartrate.csv')
        data2 = pd.read_csv('./arrhythmia.csv')
        df = pd.DataFrame(data)
        dfArrhythmia = pd.DataFrame(data2)
        # start_date = '2024-05-22'
        yesterday = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

        font_prop = FontProperties(fname='./NotoSansTC-VariableFont_wght.ttf', size=12)


        df['時間'] = pd.to_datetime(df['時間'])
        dfArrhythmia['時間'] = pd.to_datetime(dfArrhythmia['時間'])
        df.set_index('時間', inplace=True)
        dfArrhythmia.set_index('時間', inplace=True)
        df_week = df.loc[start_date]

        dfArrhythmia_today = dfArrhythmia.loc[start_date]
        dfArrhythmia_yesterday = dfArrhythmia.loc[yesterday]
        avgHeartrate = int(np.average(df_week['量測值']))

        # 使用 resample 進行重採樣，使用均值
        df_hr = df_week.resample('15min').mean()
        df_clean = df_hr.dropna()

        # resample 心律不整
        dfArrhythmia_today = dfArrhythmia_today.resample('15min').apply(lambda x: 'v' if 'v' in x['心律不整'].values else 'x')
        dfArrhythmia_today = dfArrhythmia_today.to_frame(name='心律不整')
        dfArrhythmia_yesterday = dfArrhythmia_yesterday.resample('15min').apply(lambda x: 'v' if 'v' in x['心律不整'].values else 'x')
        dfArrhythmia_yesterday = dfArrhythmia_yesterday.to_frame(name='心律不整')

        # 計算心律不整次數
        arrhythmia_alert_count = dfArrhythmia_today[dfArrhythmia_today['心律不整'] == 'v'].shape[0]
        arrhythmia_alert_count_yesterday = dfArrhythmia_yesterday[dfArrhythmia_yesterday['心律不整'] == 'v'].shape[0]
        arrhythmia_alert_count_dif = arrhythmia_alert_count - arrhythmia_alert_count_yesterday
        #print(arrhythmia_alert_count_yesterday)
        # 計算各個範圍內的數量
        total_count = len(df_clean)
        rest = len(df_clean[df_clean['量測值'] < 94])
        lowExer = len(df_clean[(df_clean['量測值'] >= 94) & (df_clean['量測值'] <= 113)])
        highExer = len(df_clean[df_clean['量測值'] > 113])

        # 計算百分比
        restPercentage = round((rest / total_count) * 100, 1)
        lowExerPercentage = round((lowExer / total_count) * 100, 1)
        highExerPercentage = round((highExer / total_count) * 100, 1)

        # 用插值法將有空缺的數據補上
        df_hr_interpolate = df_week.resample('15min').mean().interpolate()

        # plt.style.use('seaborn-v0_8')
        #matplotlib.rc('font', family='Microsoft JhengHei')

        # 創建圖表
        fig, ax1 = plt.subplots(figsize=(10, 6))

        # 繪製心率折線圖
        ax1.plot(df_hr_interpolate.index, df_hr_interpolate['量測值'], label='缺失數據推測值', linestyle='--', color = "#D9006C")
        ax1.plot(df_hr.index, df_hr['量測值'], label='平均心率', color='#1f77b4')

        # 標記心律不整時間點
        arrhythmia_times = dfArrhythmia_today[dfArrhythmia_today['心律不整'] == 'v'].index
        arrhythmia_values = df_hr.loc[arrhythmia_times]['量測值']
        ax1.scatter(arrhythmia_times, arrhythmia_values, color='red',marker='x', label='心律不整', zorder=5)


        # Extract month and day for the title
        month = datetime.strptime(start_date, '%Y-%m-%d').month
        day = datetime.strptime(start_date, '%Y-%m-%d').day
        title_date = f'{month}月{day}日 心率'


        ax1.set_title(title_date, fontproperties=font_prop)
        ax1.set_xlabel('時間', fontproperties=font_prop)
        ax1.set_ylabel('心率', fontproperties=font_prop)
        # ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        # ax1.xaxis.set_major_locator(mdates.HourLocator(interval=1))  # 每小時一個標記
        ax1.xaxis.set_major_locator(mdates.HourLocator(interval=2))  # 每2小時顯示一次標記
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # 格式化為 時:分 的形式
        ax1.set_xlim([datetime.strptime(start_date, '%Y-%m-%d'), datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=1)])  # 設置x軸顯示範圍為00:00到24:00
        ax1.legend(prop=font_prop)

        # 在圖表上添加文本
        summary_text1 = f"今日心律不整警示：{arrhythmia_alert_count}次"
        if arrhythmia_alert_count_dif > 0  :
            summary_text1 = f"今日心律不整警示：{arrhythmia_alert_count}次，比昨日多{arrhythmia_alert_count_yesterday}次\n如這症狀持續許久，請尋求醫療協助。"
        summary_text2 = f"平均心率:{avgHeartrate}下"
        summary_text3 = f"休息心率(<94bpm)比例：{restPercentage}%"
        summary_text4 = f"輕度運動心率(94~113bpm)比例：{lowExerPercentage}%"
        summary_text5 = f"中、重度運動心率(>114bpm)比例：{highExerPercentage}%"

        fig.text(0.07, 0.18, summary_text1, ha='left', fontsize=12, fontproperties=font_prop)
        fig.text(0.47, 0.15, summary_text3, ha='left', fontsize=12, fontproperties=font_prop)
        fig.text(0.47, 0.1, summary_text4, ha='left', fontsize=12, fontproperties=font_prop)
        fig.text(0.47, 0.05, summary_text5, ha='left', fontsize=12, fontproperties=font_prop)

        # 添加心率區間線條
        left, bottom, width, height = 0.04, 0, 0.4, 0.15
        ax2 = fig.add_axes([left, bottom, width, height])

        # 繪製不同顏色的線段表示心率區間
        ax2.plot([0, 1], [0, 0], color='lightblue', linewidth=15)
        ax2.plot([1, 2], [0, 0], color='lightgreen', linewidth=15)
        ax2.plot([2, 3], [0, 0], color='lightcoral', linewidth=15)

        # 顯示心率區間標記
        ax2.text(0.5, 0.02, '偏慢', horizontalalignment='center', fontsize=12, color='blue', fontproperties=font_prop)
        ax2.text(1.5, 0.02, '心率正常', horizontalalignment='center', fontsize=12, color='green', fontproperties=font_prop)
        ax2.text(2.5, 0.02, '偏快', horizontalalignment='center', fontsize=12, color='red', fontproperties=font_prop)

        # 計算 avgHeartrate 在哪段線上的位置
        if avgHeartrate <= 60:
            avg_x = avgHeartrate / 60 * 1
            color = 'blue'
        elif avgHeartrate <= 100:
            avg_x = 1 + (avgHeartrate - 60) / 40 * 1
            color = 'green'
        else:
            avg_x = 2 + (avgHeartrate - 100) / 40 * 1
            color = 'red'

        # 標記 avgHeartrate 的位置
        ax2.plot(avg_x, 0, marker='o', markersize=10, color=color)
        ax2.text(avg_x, 0.05, summary_text2, horizontalalignment='center', fontsize=12, color=color, fontproperties=font_prop)

        # 隱藏坐標軸
        ax2.axis('off')

        def autopct_format(pct):
            return ('%1.1f%%' % pct) if pct > 0 else ''

        # 圓餅圖
        pie_ax = fig.add_axes([0.73, 0.05, 0.23, 0.23])

        pie_colors = ["#46a5d3","#ffda55","#cc0001"]
        pie_ax.pie([restPercentage, lowExerPercentage, highExerPercentage], colors = pie_colors, autopct=autopct_format, startangle=180 )

        handles = [mpatches.Patch(color=color, label=label) for label, color in zip(['休息', '輕度運動', '中、重度運動'], pie_colors)]
        fig.legend(handles= handles, loc='lower right',frameon = True, bbox_to_anchor=(1, 0), edgecolor='gray', facecolor='white', framealpha=1,prop=font_prop)

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.3)

        # 保存和顯示圖形
        plt.savefig('report.png')
        im = pyimgur.Imgur(CLIENT_ID)
        PATH = 'report.png'
        uploaded_image = im.upload_image(PATH)
        #儲存imgur連結
        heartratedayimgurl = uploaded_image.link
    
        heartrateday_image_message = ImageSendMessage(
        original_content_url=heartratedayimgurl,
        preview_image_url=heartratedayimgurl
        )
        #取得回傳值:heartrateday_image_message
        return heartrateday_image_message
    #周心律
    def funheartrateweek(start_date):
        data = pd.read_csv('./heartrate.csv')
        df = pd.DataFrame(data)

        # start_date = '2024-05-21'
        end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')
        # end_date = '2024-05-27'
        df['時間'] = pd.to_datetime(df['時間'])
        df.set_index('時間', inplace=True)
        df_week = df.loc[start_date:end_date]

        font_prop = FontProperties(fname='./NotoSansTC-VariableFont_wght.ttf', size=12)###

        # 使用 resample 進行重採樣，使用均值
        df_hr = df_week.resample('h').mean()
        #用插值法將有空缺的數據補上
        df_hr_interpolate = df_week.resample('h').mean().interpolate()
        df_clean = df_hr.dropna()

        # 計算各個範圍內的數量
        total_count = len(df_clean)
        rest = len(df_clean[df_clean['量測值'] < 94])
        lowExer = len(df_clean[(df_clean['量測值'] >= 94) & (df_clean['量測值'] <= 113)])
        highExer = len(df_clean[df_clean['量測值'] > 113])
        avgHeartrate = int(np.average(df_week['量測值']))

        # 計算百分比
        restPercentage = round((rest / total_count) * 100, 1)
        lowExerPercentage = round((lowExer / total_count) * 100, 1)
        highExerPercentage = round((highExer / total_count) * 100, 1)

        # plt.style.use('seaborn-v0_8')
        #matplotlib.rc('font', family='Microsoft JhengHei')
        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(df_hr_interpolate.index,df_hr_interpolate['量測值'],label='缺失數據推測值', linestyle='--', color = "#D9006C")
        ax1.plot(df_hr.index,df_hr['量測值'], label='平均心率(小時)')
        ax1.set_title('心率周報表', fontproperties=font_prop)
        ax1.set_xlabel('日期時間', fontproperties=font_prop)
        ax1.set_ylabel('心率', fontproperties=font_prop)
        ax1.legend(prop=font_prop)

        # 在圖表上添加文本
        summary_text1 = "本周心律不整警示：3次"
        summary_text2 = f"平均心率：{avgHeartrate}下"
        summary_text3 = f"休息心率(<94bpm)比例：{restPercentage}%"
        summary_text4 = f"輕度運動心率(94~113bpm)比例：{lowExerPercentage}%"
        summary_text5 = f"中、重度運動心率(>114bpm)比例：{highExerPercentage}%"

        fig.text(0.07, 0.18, summary_text1, ha='left', fontsize=12, fontproperties=font_prop)
        #fig.text(0.07, 0.15, summary_text2, ha='left', fontsize=12, fontproperties=font_prop)
        fig.text(0.47, 0.15, summary_text3, ha='left', fontsize=12, fontproperties=font_prop)
        fig.text(0.47, 0.1, summary_text4, ha='left', fontsize=12, fontproperties=font_prop)
        fig.text(0.47, 0.05, summary_text5, ha='left', fontsize=12, fontproperties=font_prop)
        # 添加心率區間線條
        left, bottom, width, height = 0.04, 0, 0.4, 0.15
        ax2 = fig.add_axes([left, bottom, width, height])

        # 繪製不同顏色的線段表示心率區間
        ax2.plot([0, 1], [0, 0], color='lightblue', linewidth=15)
        ax2.plot([1, 2], [0, 0], color='lightgreen', linewidth=15)
        ax2.plot([2, 3], [0, 0], color='lightcoral', linewidth=15)

        # 顯示心率區間標記
        ax2.text(0.5, 0.02, '偏慢', horizontalalignment='center', fontsize=12, color='blue', fontproperties=font_prop)
        ax2.text(1.5, 0.02, '心率正常', horizontalalignment='center', fontsize=12, color='green', fontproperties=font_prop)
        ax2.text(2.5, 0.02, '偏快', horizontalalignment='center', fontsize=12, color='red', fontproperties=font_prop)

        # 計算 avgHeartrate 在哪段線上的位置
        if avgHeartrate <= 60:
            avg_x = avgHeartrate / 60 * 1
            color = 'blue'
        elif avgHeartrate <= 100:
            avg_x = 1 + (avgHeartrate - 60) / 40 * 1
            color = 'green'
        else:
            avg_x = 2 + (avgHeartrate - 100) / 40 * 1
            color = 'red'

        # 標記 avgHeartrate 的位置
        ax2.plot(avg_x, 0, marker='o', markersize=10, color=color)
        ax2.text(avg_x, 0.05, summary_text2, horizontalalignment='center', fontsize=12, color=color, fontproperties=font_prop)

        # 隱藏坐標軸
        ax2.axis('off')

        def autopct_format(pct):
            return ('%1.1f%%' % pct) if pct > 0 else ''

        # 圓餅圖
        pie_ax = fig.add_axes([0.73, 0.05, 0.23, 0.23])

        pie_colors = ["#46a5d3","#ffda55","#cc0001"]
        pie_ax.pie([restPercentage, lowExerPercentage, highExerPercentage], colors = pie_colors, autopct=autopct_format, startangle=180 )

        handles = [mpatches.Patch(color=color, label=label) for label, color in zip(['休息', '輕度運動', '中、重度運動'], pie_colors)]
        fig.legend(handles= handles, loc='lower right',frameon = True, bbox_to_anchor=(1, 0), edgecolor='gray', facecolor='white', framealpha=1, prop=font_prop)

        #plt.grid(True)

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.3)
        plt.savefig('reportHeartrateweek.png')
        im = pyimgur.Imgur(CLIENT_ID)
        PATH = 'reportHeartrateweek.png'
        uploaded_image = im.upload_image(PATH, title=plt.title)

        #儲存imgur連結
        heartrateweekimgurl = uploaded_image.link

        heartrateweek_image_message = ImageSendMessage(
        original_content_url=heartrateweekimgurl,
        preview_image_url=heartrateweekimgurl
        )
        return heartrateweek_image_message
    #日活動
    def funactivityday(start_date):
        data = pd.read_csv('./dailyActivity.csv')
        df = pd.DataFrame(data)
        #print(df)
        df['ActivityDate'] = pd.to_datetime(df['ActivityDate'])
        df.set_index('ActivityDate', inplace = True)
        # specific_time = '2024-05-27'
        df_yesterday = df.loc[start_date]

        font_prop = FontProperties(fname='./NotoSansTC-VariableFont_wght.ttf', size=12)

        #抓久坐警示csv
        datawarning = pd.read_csv('./warning.csv')
        df2 = pd.DataFrame(datawarning)
        df2['ActivityDate'] = pd.to_datetime(df2['ActivityDate'])
        
        df2.set_index('ActivityDate', inplace = True)
        df2_yesterday = df2.loc[start_date]
        #print(df2_yesterday)
        #df2_yesterday.set_index('ActivityDate', inplace = True)
        StandUpAlert = df2_yesterday['StandUpAlert']
        #print(StandUpAlert)

        #將數據間隔整理為固定1小時                
        df_hourly = df_yesterday.resample('h').sum()
        df_yesterday_hourly = df_yesterday.resample('h').sum()

        #matplotlib.rc('font', family='Microsoft JhengHei')
        plt.figure(figsize=(10, 6))
        bars = plt.bar(df_hourly.index,df_hourly['Step'],width=0.03, color='#60b8b3')
        #print(df_hourly['Step'])

        plt.xlabel('時間', fontproperties=font_prop)
        plt.ylabel('步數', fontproperties=font_prop)

        #顯示總和步數
        total_steps = df_hourly['Step'].sum()
        total_steps_yesterday = df_yesterday_hourly['Step'].sum()
        steps_difference = total_steps - total_steps_yesterday


        # Extract month and day for the title
        month = datetime.strptime(start_date, '%Y-%m-%d').month
        day = datetime.strptime(start_date, '%Y-%m-%d').day
        title_date = f'{month}月{day}日 活動'
        # plt.title(f'昨日活動 (總步數: {total_steps:.0f})')
        # Set the title
        plt.title(title_date, fontproperties=font_prop)

        # 自訂標籤：只顯示偶數小時的標籤
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=2))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # 格式化為 時:分 的形式

        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.0f}', ha='center', va='bottom', fontsize=10, fontproperties=font_prop)
            
        plt.tight_layout() 

        summary_text1 = f'昨日久坐提醒: {StandUpAlert} 次'

        if steps_difference > 0:
            summary_text2 = f'總步數: {total_steps:.0f}步，比前一天多了 {steps_difference} 步。'
        else:
            summary_text2 = f'總步數: {total_steps:.0f}步，比前一天少了 {-steps_difference} 步。'

        if total_steps >= 8000 and StandUpAlert == 0:
            summary_text3 = '恭喜你！你已經達成了8000步的目標。繼續保持這種健康的生活方式，你的身體會感謝你的！'
        elif total_steps >= 8000 and StandUpAlert > 0: 
            summary_text3 = '恭喜你！你已經達成了8000步的目標。'
        else:
            summary_text3 = f'還差 {8000 - total_steps} 步就能達成目標8000步，繼續加油！'
        plt.figtext(0.07, 0.15, summary_text1, ha='left', fontsize=12, fontproperties=font_prop)
        plt.figtext(0.07, 0.1, summary_text2, ha='left', fontsize=12, fontproperties=font_prop)
        plt.figtext(0.07, 0.05, summary_text3, ha='left', fontsize=12, fontproperties=font_prop)
        plt.subplots_adjust(bottom=0.3)

        # output_path_activt_day="C:/Users/user/Desktop/image/report2.png"
        # plt.savefig(output_path_activt_day, bbox_inches='tight')
        plt.savefig('report2.png')
        PATH = 'report2.png'

        im = pyimgur.Imgur(CLIENT_ID)
        uploaded_image = im.upload_image(PATH, title=plt.title)
        #儲存imgur連結
        activitydayimgurl = uploaded_image.link
        activityday_image_message = ImageSendMessage(
        original_content_url=activitydayimgurl,
        preview_image_url=activitydayimgurl
        )
        return activityday_image_message
    #周活動
    def funactivityweek(start_date):

        # Load step count CSV
        data = pd.read_csv('./Activity.csv')
        df = pd.DataFrame(data)
        df['ActivityDate'] = pd.to_datetime(df['ActivityDate'])
        df.set_index('ActivityDate', inplace=True)

        font_prop = FontProperties(fname='./NotoSansTC-VariableFont_wght.ttf', size=12)###

        end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')
        df_week = df.loc[start_date:end_date]

        lastweek_start_date = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
        lastweek_end_date = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

        # Resample data to daily intervals
        df_daliy = df_week.resample('d').sum()


        df_prev_week = df.loc[lastweek_start_date:lastweek_end_date]
        df_prev_week = df_prev_week.resample('d').sum()

        avgStep_lastweek = int(np.average(df_prev_week['Step']))


        matplotlib.rc('font', family='Microsoft JhengHei')
        plt.figure(figsize=(10, 6))
        bars = plt.bar(df_daliy.index, df_daliy['Step'], width=0.8, align='center', color='#60b8b3')

        plt.title('活動周報表', fontproperties=font_prop)
        plt.xlabel('日期', fontproperties=font_prop)
        plt.ylabel('步數', fontproperties=font_prop)

        # Calculate and plot the average step line
        avgStep = int(np.average(df_daliy['Step']))
        plt.axhline(y=avgStep, color='r', linestyle='--')

        # Add text with a white background behind it
        plt.text(df_daliy.index[-1], avgStep, f' 平均值: {avgStep}', color='black', va='bottom', ha='left', fontsize=12,
                bbox=dict(facecolor='white', edgecolor='none', alpha=0.8), fontproperties=font_prop)

        # Add bar labels
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, height, f'{height:.0f}', ha='center', va='bottom', fontsize=10, fontproperties=font_prop)

        summary_text1 = ''
        avgStepDif = avgStep - avgStep_lastweek
        if avgStepDif > 0:
            summary_text1 = f"平均步數比上禮拜多了{avgStepDif}步，繼續保持!"
        elif avgStepDif <= 0:
            summary_text1 = f"平均步數比上禮拜少了{-avgStepDif}步，動起來吧！健康生活從多走一步開始。"
        plt.figtext(0.07, 0.15, summary_text1, ha='left', fontsize=12, fontproperties=font_prop)
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.3)
        # plt.grid(True)
        # plt.legend()
        plt.savefig('reportActivityweek.png')

        im = pyimgur.Imgur(CLIENT_ID)
        PATH = 'reportActivityweek.png'
        uploaded_image = im.upload_image(PATH, title=plt.title)
        #儲存imgur連結
        activityweekimgurl = uploaded_image.link
        activityweekimage_message = ImageSendMessage(
        original_content_url=activityweekimgurl,
        preview_image_url=activityweekimgurl
        )
        return activityweekimage_message
    #日疲勞
    def funfatigueday(start_date):
        # 抓疲勞csv
        df = pd.read_csv('./fatigue.csv')
        # start_date = '2024-05-21'
        # end_date = '2024-05-27'
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        # 將每小時數據重整
        df_hr = df.resample('1h').mean()
        df_yesterday = df_hr.loc[start_date]

        font_prop = FontProperties(fname='./NotoSansTC-VariableFont_wght.ttf', size=8)

        bins = [0, 23, 27, 31, 35, 100] 
        labels = [0, 1, 2, 3, 4]

        # 把數據變好看
        df_yesterday['fatigue'] = pd.cut(df_yesterday['fatigue'], bins=bins, labels=labels, right=False)

        # 創建完整的一天的時間索引
        full_index = pd.date_range(start=start_date, end=pd.to_datetime(start_date) + timedelta(hours=23), freq='h')

        # 將數據對齊到完整索引上
        df_yesterday = df_yesterday.reindex(full_index)
        df_yesterday.index = df_yesterday.index.strftime('%H:%M')
        df_yesterday.reset_index(inplace=True)
        print(df_yesterday)

        # 抓疲勞警示csv
        datawarning = pd.read_csv('./warning.csv')
        df2 = pd.DataFrame(datawarning)
        df2['ActivityDate'] = pd.to_datetime(df2['ActivityDate'])
        df2.set_index('ActivityDate', inplace = True)
        df2_yesterday = df2.loc[start_date]
        FatigueAlert = int(df2_yesterday['FatigueAlert'])

        rcParams['font.family'] = 'Microsoft JhengHei'

        def render_mpl_table(data, col_width=2.0, row_height=0.5, font_size=12,
                            header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
                            bbox=[0, 0, 1, 1], ax=None, col_labels=None, **kwargs):
            if ax is None:
                size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
                fig, ax = plt.subplots(figsize=(size[0], size[1] + 3))  # 增加圖像的高度
                ax.axis('off')

            if col_labels is None:
                col_labels = data.columns

            mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=col_labels, **kwargs)

            mpl_table.auto_set_font_size(False)
            mpl_table.set_fontsize(font_size)

            max_data_value = 5  # 把數據最大值設定好 控制顏色範圍

            for k, cell in mpl_table._cells.items():
                cell.set_edgecolor(edge_color)
                if k[0] == 0:
                    cell.set_text_props(weight='bold', color='w', fontproperties=font_prop)
                    cell.set_facecolor(header_color)
                else:
                    if k[1] == 1:  # Only apply color to the 'Data' column
                        cell_value = data.values[k[0] - 1, k[1]]
                        cell_value = float(cell_value)
                        color = plt.cm.Reds(cell_value / max_data_value)
                        cell.set_facecolor(color)
                        cell.set_text_props(color='black', fontproperties=font_prop)
                    else:
                        cell.set_facecolor(row_colors[k[0] % len(row_colors)])
            

            fig.subplots_adjust(top=0.75)  # 調整頂部

            date_object=datetime.strptime(start_date,'%Y-%m-%d')
            #提取月份和日期
            month=date_object.month
            day=date_object.day
            # 在左上角加上標題
            plt.figtext(0.15, 0.8,f'{month}月{day}日疲勞指數',fontsize=13, weight='bold', ha='left', fontproperties=font_prop)
            plt.figtext(0.5, 0.76, f'疲勞警示:{FatigueAlert}次', fontsize=12, ha='center', fontproperties=font_prop)
            # 加上圖例
            legend_labels = [
                "nan: 未測得數據",
                "疲勞指數 0: 精神飽滿",
                "疲勞指數 1: 精神不錯",
                "疲勞指數 2: 一般",
                "疲勞指數 3: 疲勞",
                "疲勞指數 4: 過於疲勞"
            ]
            colors = [plt.cm.Reds(i / max_data_value) for i in range(max_data_value)]
            patches = [plt.plot([], [], marker="s", ls="", color='white', markersize=5, label=legend_labels[0])[0]]
            patches += [plt.plot([], [], marker="s", ls="", color=colors[i], markersize=5, label=legend_labels[i+1])[0] for i in range(len(colors))]


            # 調整圖例大小、位置
            plt.subplots_adjust(bottom=0.4)
            plt.legend(handles=patches, loc='upper right', bbox_to_anchor=(1.0, 1.3), fontsize=8, prop=font_prop)
                
            plt.savefig("colored_table.png", dpi=200, bbox_inches='tight')
            im = pyimgur.Imgur(CLIENT_ID)
            PATH = 'colored_table.png'
            uploaded_image=im.upload_image(PATH) #定義upload_image

            #儲存imgur連結
            fatiguedayimgurl = uploaded_image.link
            fatigueday_image_message = ImageSendMessage(
            original_content_url=fatiguedayimgurl,
            preview_image_url=fatiguedayimgurl
            )
            return fatigueday_image_message
        # 設置新的列標籤
        new_col_labels = ['時間', '疲勞指數']
        return render_mpl_table(df_yesterday, col_labels=new_col_labels)
    #周疲勞
    def funfatigueweek(start_date):
        data= pd.read_csv('./fatigue.csv')
        df = pd.DataFrame(data)
        df['datetime'] = pd.to_datetime(df['datetime'])
        # start_date = '2024-05-21'
        df.set_index('datetime', inplace=True)
        df.sort_index(inplace=True)

        end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')
        df = df.loc[start_date:end_date]

        font_prop = FontProperties(fname='./NotoSansTC-VariableFont_wght.ttf', size=12)

        #rcParams['font.family'] = 'Microsoft JhengHei'
        # 以一天為間隔重新採樣數據，分別計算最大值和平均值
        sampled_max_df = df.resample('1D').max()
        sampled_mean_df = df.resample('1D').mean()
        # 創建分區的函數
        def partition_values(value):
            if value <= 23:
                return [value, 0, 0, 0, 0]
            elif value <= 27:
                return [23, value-23, 0, 0, 0]
            elif value <= 31:
                return [23, 4, value-27, 0, 0]
            elif value <= 35:
                return [23, 4, 4, value-31, 0]
            else:
                return [23, 4, 4, 4, value-35]

        # 分解每個最大值為不同區間
        partitions = np.array([partition_values(val) for val in sampled_max_df['fatigue']])

        # 繪製堆疊條形圖
        x = np.arange(len(sampled_max_df.index))
        width = 0.3

        plt.figure(figsize=(10, 6))
        colors = [plt.cm.Reds(i / 5) for i in range(5)]
        plt.bar(x, partitions[:, 0], width, label='精神飽滿', color=colors[0])
        plt.bar(x, partitions[:, 1], width, bottom=partitions[:, 0], label='精神不錯', color=colors[1])
        plt.bar(x, partitions[:, 2], width, bottom=partitions[:, 0] + partitions[:, 1], label='一般', color=colors[2])
        plt.bar(x, partitions[:, 3], width, bottom=partitions[:, 0] + partitions[:, 1] + partitions[:, 2], label='疲勞', color=colors[3])
        plt.bar(x, partitions[:, 4], width, bottom=partitions[:, 0] + partitions[:, 1] + partitions[:, 2] + partitions[:, 3], label='過於疲勞', color=colors[4])

        # 添加平均值的散點圖
        plt.scatter(x, sampled_mean_df['fatigue'], color='black', label='平均值', zorder=5)

        # 設置Y軸範圍和標記
        plt.ylim(0, 50)
        plt.yticks(np.arange(0, 51, 5))

        plt.xlabel('日期', fontproperties=font_prop)
        plt.ylabel('疲勞指數', fontproperties=font_prop)
        plt.title('疲勞周報表', fontproperties=font_prop)
        plt.xticks(x, sampled_max_df.index.strftime('%Y-%m-%d'), fontproperties=font_prop)

        plt.legend(prop=font_prop)
        plt.grid(axis='y')
        plt.savefig("colored_tableweek.png", bbox_inches='tight')
        # plt.savefig("colored_table.png")
        im = pyimgur.Imgur(CLIENT_ID)
        PATH = 'colored_tableweek.png'
        uploaded_image = im.upload_image(PATH, title=plt.title)

        #儲存imgur連結
        fatigueweekimgurl = uploaded_image.link
        fatigueweekimage_message = ImageSendMessage(
        original_content_url=fatigueweekimgurl,
        preview_image_url=fatigueweekimgurl
        )
        return fatigueweekimage_message
    #日睡眠
    def funsleepday(start_date):
        # 重新讀取使用者上傳的 CSV 檔案
        file_path = './sleep.csv'
        df = pd.read_csv(file_path, encoding='big5')

        font_prop = FontProperties(fname='./NotoSansTC-VariableFont_wght.ttf')
        
        # 將 StartTime 和 EndTime 轉換為 datetime 格式
        df['StartTime'] = pd.to_datetime(df['StartTime'])
        df['EndTime'] = pd.to_datetime(df['EndTime'])
        df['Duration'] = pd.to_numeric(df['Duration'])

        # start_date = '2024-05-21'
        # 將字串轉換為 datetime
        date_object = datetime.strptime(start_date, '%Y-%m-%d')
        # 計算前一天
        previous_day = date_object - timedelta(days=1)
        # 將 datetime 對象轉換為字串
        previous_day = previous_day.strftime('%Y-%m-%d')

        # 創建一個空的列表來儲存結果
        split_sleep_data = []

        # 遍歷每一行，處理跨午夜的情況
        for index, row in df.iterrows():
            start = row['StartTime'].date()
            end = row['EndTime'].date()
            
            # 如果睡眠跨越午夜，將其分割
            if start != end:
                # 計算當天剩餘的時間（直到午夜）
                midnight = pd.Timestamp.combine(start + pd.Timedelta(days=1), pd.Timestamp.min.time())
                duration_until_midnight = (midnight - row['StartTime']).total_seconds() / 60
                
                # 第一部分：當天的時間
                split_sleep_data.append({
                    'Date': start,
                    'State': row['State'],
                    'StartTime': row['StartTime'],
                    'Duration': duration_until_midnight
                })
                
                # 第二部分：跨午夜後的時間
                split_sleep_data.append({
                    'Date': end,
                    'State': row['State'],
                    'StartTime': midnight,
                    'Duration': row['Duration'] - duration_until_midnight
                })
            else:
                # 如果沒有跨越午夜，直接加入結果
                split_sleep_data.append({
                    'Date': start,
                    'State': row['State'],
                    'StartTime': row['StartTime'],
                    'Duration': row['Duration']
                })

        # 將結果轉換為 DataFrame
        split_sleep_df = pd.DataFrame(split_sleep_data)

        # 定義換日時間點
        cutoff_time = pd.Timestamp('18:00:00').time()

        # 根據 StartTime 的時間來判斷並調整日期
        def adjust_date(row):
            if row['StartTime'].time() >= cutoff_time:
                return row['StartTime'].date()
            else:
                return (row['StartTime'] - pd.Timedelta(days=1)).date()

        # 應用函數來調整日期
        split_sleep_df['SleepDate'] = split_sleep_df.apply(adjust_date, axis=1)

        # 篩選出所有深眠、淺眠，以及深眠和淺眠之間的清醒數據
        filtered_sleep_data = []

        # 遍歷數據行
        for i in range(len(split_sleep_df)):
            current_row = split_sleep_df.iloc[i]
            
            if current_row['State'] in ['深眠', '淺眠']:
                filtered_sleep_data.append(current_row)
            elif current_row['State'] == '醒':
                if i > 0 and i < len(split_sleep_df) - 1:
                    previous_row = split_sleep_df.iloc[i - 1]
                    next_row = split_sleep_df.iloc[i + 1]
                    if (previous_row['State'] in ['深眠', '淺眠'] and
                        next_row['State'] in ['深眠', '淺眠']):
                        filtered_sleep_data.append(current_row)

        # 將結果轉換為 DataFrame
        filtered_sleep_df = pd.DataFrame(filtered_sleep_data)

        # 更新日期欄位
        filtered_sleep_df = filtered_sleep_df[['SleepDate', 'State', 'StartTime', 'Duration']]
        filtered_sleep_df['StartTime'] = pd.to_datetime(filtered_sleep_df['StartTime'])
        print(filtered_sleep_df)

        filtered_sleep_df['SleepDate'] = filtered_sleep_df['SleepDate'].astype(str)
        filtered_sleep_df.set_index('StartTime', inplace=True)

        # 顯示調整後的資料

        #daily_sleep_df = filtered_sleep_df.loc[start_date]
        yesterday_sleep_df = filtered_sleep_df.loc[filtered_sleep_df['SleepDate'] == previous_day]
        daily_sleep_df = filtered_sleep_df[filtered_sleep_df['SleepDate'] == start_date]
        print(daily_sleep_df)

        # 準備數據
        start_times = daily_sleep_df.index
        durations = daily_sleep_df['Duration']
        states = daily_sleep_df['State']

        # 設置顏色映射
        color_map = {
            '淺眠': '#60b8b3',  # 淺綠色
            '深眠': '#437e7b',  # 深綠色
            '醒': '#FF8040'    # 橘色
        }
        colors = [color_map[state] for state in states]

        # 創建 Broken Barh 圖並設置 x 軸的 label limit
        fig, ax = plt.subplots(figsize=(10, 6))
        rcParams['font.sans-serif'] = ['Microsoft JhengHei']
        rcParams['axes.unicode_minus'] = False
        # 每個條形的起始時間和持續時間
        bars = [(mdates.date2num(start_time), duration) for start_time, duration in zip(start_times, durations)]

        # 繪製 Broken Barh 圖
        ax.broken_barh(bars, (0, 1), facecolors=colors)

        # 設置 x 軸格式化器和每小時標籤
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))

        # 設置 x 軸範圍為開始和結束時間
        last_start_time = start_times.max()
        last_duration_minutes = durations.iloc[-1]

        # 計算最後一個資料點的結束時間
        last_end_time = last_start_time + pd.Timedelta(minutes=last_duration_minutes)
        ax.set_xlim(mdates.date2num(start_times.min()), mdates.date2num(last_end_time))

        # 獲取所有x軸標籤
        ticks = list(ax.get_xticks())

        # 添加開始和結束時間標籤
        ticks.insert(0, mdates.date2num(start_times.min()))
        ticks.append(mdates.date2num(last_end_time))

        # 獲取開始時間的分鐘數和小時數
        start_minute = start_times.min().minute
        start_hour = start_times.min().hour

        # 檢查並移除第一個標籤
        if len(ticks) > 1:
            first_tick_time = mdates.num2date(ticks[1])  
            if first_tick_time.minute == 0 and first_tick_time.hour == start_hour + 1 and start_minute > 40:
                ticks.pop(1)  # 刪除標籤

        # 檢查並移除尾標籤（檢查倒數第二個標籤，即最後一個整點標籤前的標籤）
        if len(ticks) > 2:
            last_tick_time = mdates.num2date(ticks[-2])  # 檢查倒數第二個標籤（最後一個整點標籤）
            last_end_minute = last_tick_time.minute
            if last_tick_time.minute == 0 and last_end_time.minute < 20:
                ticks.pop(-2)  # 刪除最後一個整點標籤

        # 設置x軸標籤
        ax.set_xticks(ticks)

        # 添加標籤和標題
        ax.set_xlabel('時間', fontproperties=font_prop)
        ax.set_yticks([])
        month = datetime.strptime(start_date, '%Y-%m-%d').month
        day = datetime.strptime(start_date, '%Y-%m-%d').day
        title_date = f'{month}月{day}日 睡眠'
        ax.set_title(title_date, fontproperties=font_prop)

        # 將'持續時間'列轉換為數字
        daily_sleep_df['Duration'] = pd.to_numeric(daily_sleep_df['Duration'], errors='coerce')

        # 根據'狀態'分組並計算'持續時間'的總和
        state_duration = daily_sleep_df.groupby('State')['Duration'].sum()
        yesterday_state_duration = yesterday_sleep_df.groupby('State')['Duration'].sum()
        # 計算總持續時間
        total_duration = state_duration.sum()
        yesterday_total_duration = yesterday_state_duration.sum()
        # print(f"2{total_duration}")
        # 計算每個狀態持續時間的百分比
        state_percentage = (state_duration / total_duration) * 100
            
        # 將百分比四捨五入到小數點後一位
        state_percentage = state_percentage.round(1)
        # print(f"4{state_percentage}")
        # 提取每個狀態的持續時間
        shallow_sleep_duration = int(state_duration.get('淺眠', 0))
        deep_sleep_duration = int(state_duration.get('深眠', 0))
        awake_duration = int(state_duration.get('醒', 0))
        total_sleep_duartion = shallow_sleep_duration + deep_sleep_duration

        wake_count = 0
        # 遍歷 'State' 列，遇到 '醒' 時計數器加 1
        for state in daily_sleep_df['State']:
            if state == '醒':
                wake_count += 1
        print(wake_count)
        yesterday_shallow_sleep_duration = int(yesterday_state_duration.get('淺眠', 0))
        yesterday_deep_sleep_duration = int(yesterday_state_duration.get('深眠', 0))
        yesterday_total_sleep_duration = yesterday_shallow_sleep_duration + yesterday_deep_sleep_duration

        total_sleep_duration_gap = total_sleep_duartion - yesterday_total_sleep_duration

        # 圖表底下的講解
        # summary_text1 = '昨日睡眠時長:X小時X分、淺眠時長:X小時X分、深眠時長:X小時X分、轉醒次數:X次'
        summary_text1 = f'總睡眠時長：{total_sleep_duartion//60}小時{total_sleep_duartion%60}分'
        if(total_sleep_duration_gap > 60):
            summary_text1 += f'，比昨日多睡了{total_sleep_duration_gap//60}小時{total_sleep_duration_gap%60}分'
        elif(total_sleep_duration_gap > 0):
            summary_text1 += f'，比昨日多睡了{total_sleep_duration_gap%60}分'
        elif(total_sleep_duration_gap < -60):
            summary_text1 += f'，比昨日少睡了{-total_sleep_duration_gap//60}小時{-total_sleep_duration_gap%60}分'
        elif(total_sleep_duration_gap < 0):
            summary_text1 += f'，比昨日少睡了{-total_sleep_duration_gap%60}分'

        summary_text2 = f'淺眠時長：{shallow_sleep_duration//60}小時{shallow_sleep_duration%60}分'
        if(deep_sleep_duration//60 == 0):
            summary_text3 = f'深眠時長：{deep_sleep_duration%60}分'
        else:
            summary_text3 = f'深眠時長：{deep_sleep_duration//60}小時{deep_sleep_duration%60}分'

        if(awake_duration//60 == 0):
            summary_text4 = f'轉醒時長：{awake_duration%60}分'
        else:
            summary_text4 = f'轉醒時長：{awake_duration // 60}小時{awake_duration % 60}分'    

        if(wake_count > 0):
            summary_text5 = f'轉醒次數：{wake_count}次'
        plt.figtext(0.07, 0.45, summary_text1, ha='left', fontsize=12, fontproperties=font_prop)
        plt.figtext(0.07, 0.4, summary_text5, ha='left', fontsize=12, fontproperties=font_prop)
        plt.figtext(0.07, 0.3, summary_text2, ha='left', fontsize=12, fontproperties=font_prop)
        plt.figtext(0.07, 0.25, summary_text3, ha='left', fontsize=12, fontproperties=font_prop)
        plt.figtext(0.07, 0.2, summary_text4, ha='left', fontsize=12, fontproperties=font_prop)

        # 添加圖例，順序為淺眠、深眠、醒
        legend_labels = ['淺眠', '深眠', '醒']
        legend_colors = [color_map[label] for label in legend_labels]
        legend_patches = [plt.Rectangle((0, 0), 1, 1, facecolor=color) for color in legend_colors]
        #plt.legend(legend_patches, legend_labels, loc='center left', bbox_to_anchor=(1, 0.5))
        plt.legend(legend_patches, legend_labels, prop=font_prop)

        # 在右下角添加圓餅圖
        pie_ax = fig.add_axes([0.5, 0.05, 0.4, 0.4])  # [left, bottom, width, height]
        labels = ['淺眠', '深眠', '醒']
        sizes = [shallow_sleep_duration, deep_sleep_duration, awake_duration]
        colors = ['#60b8b3', '#437e7b', '#FF8040']
        
        # 應用 font_prop 到圓餅圖的標籤
        texts = pie_ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
        for text in texts[1]:  # texts[1] 包含標籤
            text.set_fontproperties(font_prop)
        for text in texts[2]:  # texts[2] 包含百分比
            text.set_fontproperties(font_prop)
        
        # 顯示圖表
        # plt.xticks(rotation=45)
        plt.tight_layout()
        plt.subplots_adjust(top=0.94, bottom=0.64)
        # plt.subplots_adjust(bottom=0.7)
        plt.savefig('reportSleep.png')
        PATH = 'reportSleep.png'

        im = pyimgur.Imgur(CLIENT_ID)
        uploaded_image = im.upload_image(PATH, title=plt.title)

        #儲存imgur連結
        sleepdayimgurl = uploaded_image.link
    
        sleepday_image_message = ImageSendMessage(
        original_content_url=sleepdayimgurl,
        preview_image_url=sleepdayimgurl
        )
        return sleepday_image_message
    #周睡眠
    def funsleepweek(start_date):
        # 抓睡覺資料
        file_path = './sleep.csv'
        df = pd.read_csv(file_path, encoding='big5')
        # 排除清醒資料
        df = df[df['State'] != '醒']
        # start_date = pd.to_datetime('2024-05-28')
        end_date = pd.to_datetime(start_date) + pd.Timedelta(days=6)

        font_prop = FontProperties(fname='./NotoSansTC-VariableFont_wght.ttf', size=12)


        # 定義一個函數來拆分跨天的資料
        def split_overnight_rows(row):
            start = datetime.strptime(row['StartTime'], '%Y/%m/%d %H:%M')
            end = datetime.strptime(row['EndTime'], '%Y/%m/%d %H:%M')
            
            # 如果開始和結束日期不同，表示跨天
            if start.date() != end.date():
                # 當天午夜
                midnight = datetime(start.year, start.month, start.day) + timedelta(days=1)

                # 第一筆資料：從開始時間到午夜
                row1 = row.copy()
                row1['EndTime'] = midnight.strftime('%Y/%m/%d %H:%M')
                row1['Duration'] = (midnight - start).seconds // 60  # 分鐘數
                
                # 第二筆資料：從午夜到結束時間
                row2 = row.copy()
                row2['StartTime'] = midnight.strftime('%Y/%m/%d %H:%M')
                row2['Duration'] = (end - midnight).seconds // 60  # 分鐘數
                
                return [row1, row2]
            else:
                return [row]

        # 拆分跨天的資料
        new_rows = []
        for index, row in df.iterrows():
            new_rows.extend(split_overnight_rows(row))

        # 創建新的DataFrame
        df_sleep = pd.DataFrame(new_rows)

        # 讓StartTime 是string
        df_sleep['StartTime'] = df_sleep['StartTime'].astype(str)


        # 拆分日期和時間
        df_sleep['Date'] = df_sleep['StartTime'].str.split(' ').str[0]
        df_sleep['Time'] = df_sleep['StartTime'].str.split(' ').str[1]
        def time_to_minutes(time_str):
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes

        # 把time改成分鐘數
        df_sleep['Time'] = df_sleep['Time'].apply(time_to_minutes)


        # 選擇取樣時間
        df_sleep['Date'] = pd.to_datetime(df_sleep['Date'])

        df_sleep_yesterday = df_sleep[(df_sleep['Date'] >= pd.to_datetime(start_date) - pd.Timedelta(days= 7)) & (df_sleep['Date'] <= pd.to_datetime(end_date) - pd.Timedelta(days= 7))]
        print(df_sleep_yesterday)
        # print(df_sleep)
        df_sleep = df_sleep[(df_sleep['Date'] >= pd.to_datetime(start_date)) & (df_sleep['Date'] <= pd.to_datetime(end_date))]
        unique_dates = df_sleep['Date'].dt.strftime('%Y-%m-%d').unique()[::-1]


        # print(df_sleep)

        # 創建圖表

        color_map = {
            '淺眠': '#60b8b3',  # 淺綠色
            '深眠': '#437e7b',  # 深綠色
        ##    '醒': '#fd7706'    # 橘色
        }

        fig, ax = plt.subplots(figsize=(10, 6))
        rcParams['font.sans-serif'] = ['Microsoft JhengHei']
        rcParams['axes.unicode_minus'] = False
        # 畫圖
        for i, date in enumerate(unique_dates):
            day_df = df_sleep[df_sleep['Date'] == date]
            for state, color in color_map.items():
                state_df = day_df[day_df['State'] == state]
                xranges = [(row['Time'], row['Duration']) for _, row in state_df.iterrows()]
                ax.broken_barh(xranges, (i * 10, 9), facecolors=color, label=state if i == 0 else "")

        # x軸
        time_labels = [f'{hour}:00' for hour in range(0, 25, 2)]
        time_ticks = [hour * 60 for hour in range(0, 25, 2)]
        ax.set_xticks(time_ticks)
        ax.set_xticklabels(time_labels)
        ax.set_xlim([0,1440])

        # 設置y軸以反序顯示日期
        ax.set_yticks([i * 10 + 5 for i in range(len(unique_dates))])
        ax.set_yticklabels(unique_dates)

        # 創建圖利
        handles = [plt.Rectangle((0,0),1,1, color=color_map[state]) for state in color_map]
        labels = color_map.keys()
        ax.legend(handles, labels, title="State", bbox_to_anchor=(1, 1), loc='upper left')

        # 添加標籤和標題
        ax.set_xlabel('時間', fontproperties=font_prop)
        ax.set_ylabel('日期', fontproperties=font_prop)
        ax.set_title('睡眠周報表', fontproperties=font_prop)
        ax.grid(True)

        # 將'持續時間'列轉換為數字
        df_sleep['Duration'] = pd.to_numeric(df_sleep['Duration'], errors='coerce')
        df_sleep_yesterday['Duration'] = pd.to_numeric(df_sleep_yesterday['Duration'], errors='coerce')
        # 根據'狀態'分組並計算'持續時間'的總和
        state_duration = df_sleep.groupby('State')['Duration'].sum()
        yesterday_state_duration = df_sleep_yesterday.groupby('State')['Duration'].sum()
        # print(f"state_duration{state_duration}")
        # 計算總持續時間
        total_duration = state_duration.sum()
        # print(f"2{total_duration}")
        # 計算每個狀態持續時間的百分比
        state_percentage = (state_duration / total_duration) * 100
            
        # 將百分比四捨五入到小數點後一位
        state_percentage = state_percentage.round(1)
        # print(f"4{state_percentage}")
        # 提取每個狀態的持續時間
        shallow_sleep_duration = int(state_duration.get('淺眠', 0)/7)
        deep_sleep_duration = int(state_duration.get('深眠', 0)/7)
        total_sleep_duration = shallow_sleep_duration + deep_sleep_duration


        yesterday_shallow_sleep_duration = int(yesterday_state_duration.get('淺眠', 0)/7)
        yesterday_deep_sleep_duration = int(yesterday_state_duration.get('深眠', 0)/7)
        yesterday_total_sleep_duration = yesterday_shallow_sleep_duration + yesterday_deep_sleep_duration
        #awake_duration = int(state_duration.get('醒', 0)/7)
        sleep_duration_gap = total_sleep_duration - yesterday_total_sleep_duration

        # 圖表底下的講解
        summary_text1 = f'本週平均睡眠時長：{total_sleep_duration//60}小時{total_sleep_duration%60}分'
        if(sleep_duration_gap > 60):
            summary_text1 += f'，比上週多睡了{sleep_duration_gap//60}小時{sleep_duration_gap%60}分'
        elif(sleep_duration_gap > 0):
            summary_text1 += f'，比上週多睡了{sleep_duration_gap%60}分'
        elif(sleep_duration_gap < -60):
            summary_text1 += f'，比上週少睡了{-sleep_duration_gap//60}小時{-sleep_duration_gap%60}分'
        elif(sleep_duration_gap < 0):
            summary_text1 += f'，比上週少睡了{-sleep_duration_gap%60}分'
        summary_text2 = f'平均淺眠時長：{shallow_sleep_duration//60}小時{shallow_sleep_duration%60}分'
        if(deep_sleep_duration//60 == 0):
            summary_text3 = f'平均深眠時長：{deep_sleep_duration%60}分'
        else:
            summary_text3 = f'平均深眠時長：{deep_sleep_duration//60}小時{deep_sleep_duration%60}分'
        if(shallow_sleep_duration + deep_sleep_duration >= 420):
            summary_text5 = '已睡足平均所需之7小時！'
        else:
            summary_text5 = '睡眠不足每日所需之最少7小時睡眠，請多加注意。'
        # if(awake_duration//60 == 0):
        #     summary_text4 = f'平均轉醒時長:{awake_duration%60}分'
        # else:
        #     summary_text4 = f'平均轉醒時長:{awake_duration // 60}小時{awake_duration % 60}分'    
        plt.figtext(0.07, 0.35, summary_text1, ha='left', fontsize=12, fontproperties=font_prop)
        plt.figtext(0.07, 0.3, summary_text2, ha='left', fontsize=12, fontproperties=font_prop)
        plt.figtext(0.07, 0.25, summary_text3, ha='left', fontsize=12, fontproperties=font_prop)
        #plt.figtext(0.07, 0.2, summary_text4, ha='left', fontsize=12)
        plt.figtext(0.07, 0.2, summary_text5, ha='left', fontsize=12, fontproperties=font_prop)

        # 添加圖例，順序為淺眠、深眠、醒
        #legend_labels = ['淺眠', '深眠', '醒']
        legend_labels = ['淺眠', '深眠']
        legend_colors = [color_map[label] for label in legend_labels]
        legend_patches = [plt.Rectangle((0, 0), 1, 1, facecolor=color) for color in legend_colors]
        plt.legend(legend_patches, legend_labels, loc='center left', bbox_to_anchor=(1, 0.5))

        # 在右下角添加圓餅圖
        pie_ax = fig.add_axes([0.5, 0.05, 0.4, 0.4])  # [left, bottom, width, height]
        #labels = ['淺眠', '深眠', '醒']
        labels = ['淺眠', '深眠']
        #sizes = [shallow_sleep_duration, deep_sleep_duration, awake_duration]
        sizes = [shallow_sleep_duration, deep_sleep_duration]
        #colors = ['#cadff0', '#2050bc', '#fd7706']
        # colors = ['#cadff0', '#2050bc']
        colors = ['#60b8b3', '#437e7b']
        pie_ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
        # pie_ax.set_title('睡眠狀態', y=-0.1)


        plt.tight_layout()
        plt.subplots_adjust(bottom=0.5)
        plt.savefig('Sleepweekreport.png')
        PATH = 'Sleepweekreport.png'

        im = pyimgur.Imgur(CLIENT_ID)
        uploaded_image = im.upload_image(PATH, title=plt.title)
        #儲存imgur連結
        sleepweekimgurl = uploaded_image.link
    
        sleepweek_image_message = ImageSendMessage(
        original_content_url=sleepweekimgurl,
        preview_image_url=sleepweekimgurl
        )
        return sleepweek_image_message
    #提取用戶選擇的日期和報告類型
    data = event.postback.data
    params = event.postback.params
    if params and 'date' in params:
        selected_date = params['date']
        report_type = data.split('&')[0].split('=')[1]  # 提取报告類型
        try:
            # 将选择的日期转换为 YYYY-MM-DD 格式
            start_date = datetime.strptime(selected_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            
            # line_bot_api.reply_message(
            #     event.reply_token,
            #     TextSendMessage(text=f"你選擇的日期是: {start_date}")
            # )
            #根據不同類型傳報表
            if report_type == "heartrateday":
                try:
                    report_image_message =funheartrateday(start_date)
                    line_bot_api.reply_message(event.reply_token, report_image_message)
                except KeyError:
                # 找不到對應的日期，回應用戶
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"抱歉，{start_date} 沒有數據。")
                    )
            elif report_type =="heartrateweek":
                try:
                    report_image_message =funheartrateweek(start_date)  
                    line_bot_api.reply_message(event.reply_token, report_image_message) 
                except KeyError:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"抱歉，{start_date} 沒有數據。")
                    )
            elif report_type =="sleepday":
                try:
                    report_image_message =funsleepday(start_date)  
                    line_bot_api.reply_message(event.reply_token, report_image_message)
                except KeyError:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"抱歉，{start_date} 沒有數據。")
                    )
            elif report_type =="sleepweek":
                try:
                    report_image_message =funsleepweek(start_date) 
                    line_bot_api.reply_message(event.reply_token, report_image_message)
                except KeyError:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"抱歉，{start_date} 沒有數據。")
                    )
            elif report_type =="activityday":
                try:
                    report_image_message =funactivityday(start_date)  
                    line_bot_api.reply_message(event.reply_token, report_image_message)
                except KeyError:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"抱歉，{start_date} 沒有數據。")
                    )
            elif report_type =="activityweek":
                try:
                    report_image_message =funactivityweek(start_date) 
                    line_bot_api.reply_message(event.reply_token, report_image_message)  
                except KeyError:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"抱歉，{start_date} 沒有數據。")
                    ) 
            elif report_type =="fatigueday":
                try:
                    report_image_message =funfatigueday(start_date) 
                    line_bot_api.reply_message(event.reply_token, report_image_message) 
                except KeyError:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"抱歉，{start_date} 沒有數據。")
                    )
            elif report_type =="fatigueweek":
                try:
                    report_image_message =funfatigueweek(start_date) 
                    line_bot_api.reply_message(event.reply_token, report_image_message)
                except KeyError:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=f"抱歉，{start_date} 沒有數據。")
                    )
            elif report_type =="allreportday":
                report_image_message1 =funfatigueday(start_date)     
                report_image_message2 =funsleepday(start_date)     
                report_image_message3 =funactivityday(start_date)     
                report_image_message4 =funheartrateday(start_date)  
                messages=[report_image_message1,report_image_message2,report_image_message3,report_image_message4]
                line_bot_api.reply_message(event.reply_token, messages) 
            elif report_type =="allreportweek":
                report_image_message1 =funfatigueweek(start_date)     
                report_image_message2 =funsleepweek(start_date)     
                report_image_message3 =funactivityweek(start_date)     
                report_image_message4 =funheartrateweek(start_date)  
                messages=[report_image_message1,report_image_message2,report_image_message3,report_image_message4]
                line_bot_api.reply_message(event.reply_token, messages) 
        except ValueError as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"日期格式錯誤: {e}")
            )
def load_qa_data(): #把QA CSV用成DICT
    data = pd.read_csv('./q_a.csv', encoding='big5')
    qa_dict = {row['Question']: row['Answer'] for index, row in data.iterrows()}
    return qa_dict
qa_dict = load_qa_data()  

def flex_hr_qa(event):
    data = pd.read_csv('./q_a.csv', encoding='big5')
    df = pd.DataFrame(data)
    df_heartrate = df[df["Type"] == "心率"]
    carousel_contents = []

    count = 0
    while count < len(df_heartrate):
        bubble_contents = []
        for _ in range(3):  # 每個 bubble 最多有 3 個按鈕
            if count < len(df_heartrate):
                bubble_contents.append({
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": df_heartrate["Question"].iloc[count],
                        "text": df_heartrate["Question"].iloc[count]
                    }
                })
                count += 1
            else:
                break
        while len(bubble_contents) < 3:
            bubble_contents.append( {
                "type": "button",
                "action": {
                "type": "message",
                "label": " ",
                "text": " "
                }
                },
            )

        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "常見問題",
                        "size": "xl",
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": "心率",
                        "size": "md",
                        "color": "#9C9C9C"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": bubble_contents
            },
            "styles": {
                "footer": {
                    "separator": True
                }
            }
        }
        carousel_contents.append(bubble)

    flex_message = FlexSendMessage(
        alt_text='hello',
        contents={
            "type": "carousel",
            "contents": carousel_contents
        }
    )
    line_bot_api.reply_message(event.reply_token, flex_message)

def flex_sleep_qa(event): 
    data = pd.read_csv('./q_a.csv', encoding='big5')
    df = pd.DataFrame(data)
    df_sleep = df[df["Type"] == "睡眠"]
    carousel_contents = []

    count = 0
    while count < len(df_sleep):
        bubble_contents = []
        for _ in range(3):  # 每個 bubble 最多有 3 個按鈕
            if count < len(df_sleep):
                bubble_contents.append({
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": df_sleep["Question"].iloc[count],
                        "text": df_sleep["Question"].iloc[count]
                    }
                })
                count += 1
            else:
                break
        while len(bubble_contents) < 3:
            bubble_contents.append( {
                "type": "button",
                "action": {
                "type": "message",
                "label": " ",
                "text": " "
                }
                },
            )
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "常見問題",
                        "size": "xl",
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": "睡眠",
                        "size": "md",
                        "color": "#9C9C9C"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": bubble_contents
            },
            "styles": {
                "footer": {
                    "separator": True
                }
            }
        }
        carousel_contents.append(bubble)

    flex_message = FlexSendMessage(
        alt_text='hello',
        contents={
            "type": "carousel",
            "contents": carousel_contents
        }
    )
    line_bot_api.reply_message(event.reply_token, flex_message)

def flex_activity_qa(event):
    data = pd.read_csv('./q_a.csv', encoding='big5')
    df = pd.DataFrame(data)
    df_activity = df[df["Type"] == "活動"]
    carousel_contents = []

    count = 0
    while count < len(df_activity):
        bubble_contents = []
        for _ in range(3):  # 每個 bubble 最多有 3 個按鈕
            if count < len(df_activity):
                bubble_contents.append({
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": df_activity["Question"].iloc[count],
                        "text": df_activity["Question"].iloc[count]
                    }
                })
                count += 1
            else:
                break
        while len(bubble_contents) < 3:
            bubble_contents.append( {
                "type": "button",
                "action": {
                "type": "message",
                "label": " ",
                "text": " "
                }
                },
            )
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "常見問題",
                        "size": "xl",
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": "活動",
                        "size": "md",
                        "color": "#9C9C9C"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": bubble_contents
            },
            "styles": {
                "footer": {
                    "separator": True
                }
            }
        }
        carousel_contents.append(bubble)

    flex_message = FlexSendMessage(
        alt_text='hello',
        contents={
            "type": "carousel",
            "contents": carousel_contents
        }
    )
    line_bot_api.reply_message(event.reply_token, flex_message)

def flex_fatigue_qa(event):
    data = pd.read_csv('./q_a.csv', encoding='big5')
    df = pd.DataFrame(data)
    df_fatigue = df[df["Type"] == "疲勞"]
    carousel_contents = []

    count = 0
    while count < len(df_fatigue):
        bubble_contents = []
        for _ in range(3):  # 每個 bubble 最多有 3 個按鈕
            if count < len(df_fatigue):
                bubble_contents.append({
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": df_fatigue["Question"].iloc[count],
                        "text": df_fatigue["Question"].iloc[count]
                    }
                })
                count += 1
            else:
                break
        while len(bubble_contents) < 3:
            bubble_contents.append( {
                "type": "button",
                "action": {
                "type": "message",
                "label": " ",
                "text": " "
                }
                },
            )
        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "常見問題",
                        "size": "xl",
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": "疲勞",
                        "size": "md",
                        "color": "#9C9C9C"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": bubble_contents
            },
            "styles": {
                "footer": {
                    "separator": True
                }
            }
        }
        carousel_contents.append(bubble)

    flex_message = FlexSendMessage(
        alt_text='hello',
        contents={
            "type": "carousel",
            "contents": carousel_contents
        }
    )
    line_bot_api.reply_message(event.reply_token, flex_message)

if __name__ == "__main__":
    schedule_jobs()
    schedule.every(5).minutes.do(check_for_updates)  # 每5分鐘檢查一次更新
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(1)

    import threading
    schedule_thread = threading.Thread(target=run_schedule)
    schedule_thread.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

