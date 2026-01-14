import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import datetime
from fpdf import FPDF
import urllib.request
import smtplib
import ssl
from email.message import EmailMessage
import re

# --- 設定與常數 ---
DATA_FILE = "polling_data.json"

# 【修正】改用台北黑體 (Taipei Sans) 的 TTF 版本，解決 404 和格式錯誤
FONT_URL = "https://raw.githubusercontent.com/bgp/taipei-sans/master/TaipeiSansTCBeta-Regular.ttf"
FONT_FILE = "TaipeiSansTCBeta-Regular.ttf"

DEFAULT_DATA = {
    "title": "目標與策略",
    "password": "admin123",
    "config": {
        "enableMultiSelect": False,
        "maxSelections": 3
    },
    "options": [
        "滿足所有持分者需要",
        "全體參與",
        "凝聚全校共識",
        "清晰的教學目標",
        "協同效應",
        "可見的教學成效",
        "整合內化",
        "與天主聖神一起工作"
    ],
    "votes": []
}

# --- 資料處理函數 ---
def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEFAULT_DATA

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def send_password_email(new_password):
    """發送密碼更新通知郵件"""
    try:
        email_user = st.secrets["gmail"]["user"]
        email_password = st.secrets["gmail"]["password"]
    except Exception:
        st.error("Secrets 設定錯誤：無法讀取 [gmail] 設定，請檢查 Streamlit Cloud 後台。")
        return False

    receiver_email = "rme@catholic.edu.hk"
    subject = "統計App密碼更新"
    body = f"您的管理員密碼已更新為: {new_password}"

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = email_user
    msg['To'] = receiver_email

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls(context=context)
            server.login(email_user, email_password)
            server.send_message(msg)
            return True
    except Exception as e:
        st.error(f"郵件發送失敗: {e}")
        return False

# --- PDF 產生類別 ---
class ReportPDF(FPDF):
    def header(self):
        # 標題
        if hasattr(self, 'report_title'):
             # 使用標準字型顯示英文標題 (避免無中文字型時亂碼)
             self.set_font("Arial", "B", 16)
             self.cell(0, 10, "Polling Report", 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def download_font_if_needed():
    """下載中文字型 (.ttf)"""
    if not os.path.exists(FONT_FILE):
        try:
            with st.spinner("正在下載中文字型 (Taipei Sans TC)..."):
                # 增加 header 避免被 github 擋下
                opener = urllib.request.build_opener()
                opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                urllib.request.install_opener(opener)
                urllib.request.urlretrieve(FONT_URL, FONT_FILE)
        except Exception as e:
            st.error(f"字型下載失敗: {e}")

# --- 頁面邏輯 ---

def page_home(data):
    # CSS 美化：將 Radio Button 變成卡片樣式
    st.markdown("""
    <style>
        div[role="radiogroup"] > label > div:first-of-type {
            display: none;
        }
        div[role="radiogroup"] {
            flex-direction: column;
            gap: 15px;
        }
        div[role="radiogroup"] > label {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            border: 2px solid #e9ecef;
            transition: all 0.3s;
            cursor: pointer;
            font-size: 18px;
            font-weight: bold;
            color: #495057;
            display: flex;
            justify-content: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        div[role="radiogroup"] > label:hover {
            background-color: #e9ecef;
            border-color: #4F46E5;
            transform: translateY(-2px);
        }
        /* 選中狀態通用嘗試 */
        div[role="radiogroup"] > label[data-baseweb="radio"] {
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"<h1 style='text-align: center; color: #4F46E5;'>{data['title']}</h1>", unsafe_allow_html=True)
    
    config = data['config']
    options = data['options']
    
    st.write("")
    mode_text = f"可選 {config['maxSelections']} 項" if config['enableMultiSelect'] else "單選"
    st.markdown(f"<div style='text-align: center; color: #64748B; margin-bottom: 20px;'>請選擇下方項目 ({mode_text})</div>", unsafe_allow_html=True)

    with st.form("vote_form"):
        selected_vals = []
        if config['enableMultiSelect']:
            selected_vals = st.multiselect("請選擇:", options, max_selections=config['maxSelections'])
        else:
            choice = st.radio("請選擇:", options, index=None)
            if choice:
                selected_vals = [choice]

        submitted = st.form_submit_button("確認送出", use_container_width=True, type="primary")
        
        if submitted:
            if not selected_vals:
                st.warning("請至少選擇一個選項")
            else:
                new_vote = {
                    "option": selected_vals if config['enableMultiSelect'] else selected_vals[0],
                    "timestamp": datetime.datetime.now().isoformat()
                }
                data['votes'].append(new_vote)
                save_data(data)
                st.session_state['page'] = 'success'
                st.rerun()

def page_success():
    st.markdown("""
    <div style="text-align: center; padding: 40px;">
        <h2 style="color: #10B981;">✅ 已成功投選！</h2>
        <p style="color: #64748B;">感謝您的參與。</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("統計圖", use_container_width=True):
            st.session_state['page'] = 'stats'
            st.rerun()
    with col2:
        if st.button("返回首頁", use_container_width=True):
            st.session_state['page'] = 'home'
            st.rerun()

def page_stats(data):
    st.title("投票統計結果")
    
    votes = data['votes']
    total_votes = len(votes)
    
    col_head_1, col_head_2 = st.columns([2, 1])
    with col_head_1:
        st.write("") 
    with col_head_2:
        st.metric("總投票人數", total_votes)
    
    if total_votes == 0:
        st.info("目前尚無投票數據")
        return

    # 統計邏輯
    all_selected = []
    for v in votes:
        opt = v['option']
        if isinstance(opt, list):
            all_selected.extend(opt)
        else:
            all_selected.append(opt)
            
    counts = {opt: 0 for opt in data['options']}
    for opt in all_selected:
        if opt in counts:
            counts[opt] += 1
            
    df = pd.DataFrame(list(counts.items()), columns=['選項', '票數'])
    df['百分比'] = (df['票數'] / total_votes * 100).round(1)
    df = df.sort_values(by='票數', ascending=True)

    col_chart, col_reset = st.columns([3, 1])
    
    with col_chart:
        chart_view = st.radio("圖表切換", ["直條統計圖", "圓形統計圖"], horizontal=True, label_visibility="collapsed")
    
    with col_reset:
        if st.button("重設", key="reset_btn_public"):
             st.info("請進入管理後台進行重設")

    if chart_view == "直條統計圖":
        fig = px.bar(df, x='票數', y='選項', orientation='h', text='票數', color='選項')
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = px.pie(df, values='票數', names='選項', hole=0.3)
        st.plotly_chart(fig, use_container_width=True)

def page_admin(data):
    st.title("管理後台")
    
    if 'admin_auth' not in st.session_state:
        st.session_state['admin_auth'] = False

    if not st.session_state['admin_auth']:
        pwd = st.text_input("輸入管理密碼", type="password")
        if st.button("登入"):
            if pwd == data['password']:
                st.session_state['admin_auth'] = True
                st.rerun()
            else:
                st.error("密碼錯誤")
        return

    # --- 登入後介面 ---
    tab1, tab2, tab3 = st.tabs(["統計與數據", "更改密碼", "系統設定"])

    with tab1:
        st.subheader("數據概覽")
        votes_df = pd.DataFrame(data['votes'])
        st.dataframe(votes_df, use_container_width=True)
        
        # CSV 下載
        if not votes_df.empty:
            export_df = votes_df.copy()
            export_df['option'] = export_df['option'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
            csv = export_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("下載 CSV", csv, f"votes_{datetime.date.today()}.csv", "text/csv")
        
        # PDF 下載
        if st.button("產生 PDF 統計報告"):
            download_font_if_needed()
            if not os.path.exists(FONT_FILE):
                st.error(f"無法找到字型檔 {FONT_FILE}，請稍後再試。")
            else:
                try:
                    pdf = ReportPDF()
                    pdf.report_title = data['title']
                    # 註冊中文字型 (Taipei Sans)
                    pdf.add_font("TaipeiSans", "", FONT_FILE, uni=True)
                    pdf.add_page()
                    
                    # 使用中文字型
                    pdf.set_font("TaipeiSans", "", 16)
                    pdf.cell(0, 10, f"{data['title']} - 統計報告", 0, 1, 'C')
                    pdf.ln(10)
                    
                    pdf.set_font("TaipeiSans", "", 12)
                    total = len(data['votes'])
                    pdf.cell(0, 10, f"總投票數: {total}", 0, 1)
                    
                    # 簡單統計
                    all_selected = []
                    for v in data['votes']:
                        opt = v['option']
                        if isinstance(opt, list): all_selected.extend(opt)
                        else: all_selected.append(opt)
                    counts = {opt: 0 for opt in data['options']}
                    for opt in all_selected:
                        if opt in counts: counts[opt] += 1
                        
                    pdf.ln(5)
                    pdf.set_fill_color(240, 240, 240)
                    pdf.cell(100, 10, "選項", 1, 0, 'L', 1)
                    pdf.cell(30, 10, "票數", 1, 1, 'R', 1)
                    
                    for name in data['options']:
                        pdf.cell(100, 10, name, 1, 0, 'L')
                        pdf.cell(30, 10, str(counts[name]), 1, 1, 'R')
                        
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    st.download_button("下載 PDF", pdf_bytes, "report.pdf", "application/pdf")
                except Exception as e:
                    st.error(f"PDF 產生發生錯誤: {e}")

        st.divider()
        with st.expander("⚠️ 重設所有數據"):
            st.warning("此動作無法復原！")
            if st.button("確認重設 (刪除所有票數)"):
                data['votes'] = []
                save_data(data)
                st.success("數據已清空")
                st.rerun()

    with tab2:
        st.subheader("修改管理員密碼")
        new_pwd_input = st.text_input("新密碼", type="password")
        if st.button("確認更改"):
            if len(new_pwd_input) > 8:
                st.error("密碼格式不符：長度不能超過 8 位")
            elif not (re.search(r"[a-zA-Z]", new_pwd_input) and re.search(r"[0-9]", new_pwd_input)):
                st.error("密碼格式不符：需包含英文與數字")
            else:
                data['password'] = new_pwd_input
                save_data(data)
                with st.spinner("正在發送通知郵件..."):
                    sent = send_password_email(new_pwd_input)
                    if sent:
                        st.success("密碼已更新並發送至電郵 rme@catholic.edu.hk")
                    else:
                        st.warning("密碼已更新，但電郵發送失敗 (請檢查 Secrets 設定)")

    with tab3:
        st.subheader("選項與標題設定")
        new_title = st.text_input("APP 標題", data['title'])
        if st.button("更新標題"):
            data['title'] = new_title
            save_data(data)
            st.success("標題已更新")

    st.write("")
    if st.button("登出"):
        st.session_state['admin_auth'] = False
        st.rerun()

# --- 主程式 ---
def main():
    st.set_page_config(page_title="RMES Polling", page_icon="🗳️", layout="centered")
    
    data = load_data()
    
    if 'page' not in st.session_state:
        st.session_state['page'] = 'home'

    with st.sidebar:
        st.title("功能選單")
        if st.button("🏠 投票首頁", use_container_width=True):
            st.session_state['page'] = 'home'
            st.rerun()
        if st.button("📊 統計結果", use_container_width=True):
            st.session_state['page'] = 'stats'
            st.rerun()
        if st.button("⚙️ 管理員登入", use_container_width=True):
            st.session_state['page'] = 'admin'
            st.rerun()
            
    if st.session_state['page'] == 'home':
        page_home(data)
    elif st.session_state['page'] == 'success':
        page_success()
    elif st.session_state['page'] == 'stats':
        page_stats(data)
    elif st.session_state['page'] == 'admin':
        page_admin(data)

if __name__ == "__main__":
    main()
