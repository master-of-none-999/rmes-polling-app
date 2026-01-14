import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import datetime
from fpdf import FPDF
import requests
import smtplib
import ssl
from email.message import EmailMessage
import re

# --- 設定與常數 ---
DATA_FILE = "polling_data.json"
# 使用 Google Fonts GitHub Raw 連結 (Variable Font)
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf"
FONT_FILE = "NotoSansTC-VariableFont_wght.ttf"

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

# --- CSS 樣式注入 (美化介面) ---
def inject_custom_css():
    st.markdown("""
    <style>
        /* 全局字型與背景 */
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Noto Sans TC', sans-serif;
        }
        
        /* App 背景漸層 */
        .stApp {
            background: linear-gradient(135deg, #eef2ff 0%, #ffffff 50%, #ecfeff 100%);
        }
        
        /* 隱藏預設 Header 與 Footer */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* 標題樣式 */
        h1 {
            color: #4F46E5 !important;
            font-weight: 800 !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.05);
            padding-bottom: 1rem;
        }
        
        h2, h3 {
            color: #334155 !important;
            font-weight: 700 !important;
        }
        
        /* 卡片容器樣式 (Glassmorphism) */
        .stForm, div[data-testid="stExpander"], div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 20px !important;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        }

        /* 輸入框與選擇器美化 */
        .stRadio div[role="radiogroup"], .stMultiSelect {
            background: rgba(255, 255, 255, 0.5);
            padding: 15px;
            border-radius: 15px;
            border: 1px solid #e2e8f0;
        }

        /* 按鈕美化 */
        div.stButton > button {
            background: linear-gradient(to right, #6366f1, #8b5cf6);
            color: white !important;
            border: none;
            padding: 0.6rem 1.5rem;
            border-radius: 12px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
            transition: all 0.3s ease;
            width: 100%;
        }
        
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
            border-color: transparent !important;
        }

        div.stButton > button:active {
            transform: translateY(0);
        }

        /* 次要按鈕 (Ghost/Secondary) 樣式 - 針對特定 Key 修改 */
        div[data-testid="stHorizontalBlock"] button {
             background: white;
             color: #475569 !important;
             border: 1px solid #cbd5e1;
             box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        div[data-testid="stHorizontalBlock"] button:hover {
             border-color: #6366f1;
             color: #6366f1 !important;
        }

        /* Metric 數字顏色 */
        [data-testid="stMetricValue"] {
            color: #4F46E5 !important;
        }
        
        /* DataFrame 表格美化 */
        [data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }
        
        /* 側邊欄美化 */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #f1f5f9;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 資料處理函數 ---
def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 確保舊資料結構相容
            if "config" not in data:
                data["config"] = DEFAULT_DATA["config"]
            return data
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
        # 標題 (避免在 header 使用中文，除非字型已載入，此處用英文作為安全底層)
        self.set_font("Arial", "B", 16)
        # 這裡不寫內容，在 Body 統一處理中文
        
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def download_font_if_needed():
    """從 GitHub 下載中文字型"""
    if not os.path.exists(FONT_FILE):
        try:
            with st.spinner("正在初始化字型資源 (從 GitHub 下載)..."):
                response = requests.get(FONT_URL)
                response.raise_for_status()
                with open(FONT_FILE, "wb") as f:
                    f.write(response.content)
        except Exception as e:
            st.error(f"字型下載失敗: {e}")

# --- 頁面邏輯 ---

def page_home(data):
    st.markdown(f"<h1 style='text-align: center;'>{data['title']}</h1>", unsafe_allow_html=True)
    
    config = data['config']
    options = data['options']
    
    # 顯示模式標籤
    mode_text = f"可選 {config['maxSelections']} 項" if config['enableMultiSelect'] else "單選"
    st.markdown(
        f"""
        <div style="display: flex; justify-content: center; margin-bottom: 2rem;">
            <span style="background-color: #e0e7ff; color: #4338ca; padding: 4px 12px; border-radius: 99px; font-size: 0.875rem; font-weight: 600;">
                {mode_text}
            </span>
        </div>
        """, 
        unsafe_allow_html=True
    )

    with st.form("vote_form"):
        st.write("### 請選擇下方項目")
        selected_vals = []
        
        if config['enableMultiSelect']:
            selected_vals = st.multiselect(
                "請點擊選擇 (可多選):", 
                options, 
                max_selections=config['maxSelections'],
                label_visibility="collapsed"
            )
        else:
            choice = st.radio(
                "請點擊選擇:", 
                options, 
                index=None,
                label_visibility="collapsed"
            )
            if choice:
                selected_vals = [choice]
        
        st.write("")
        st.write("")
        submitted = st.form_submit_button("確認送出")
        
        if submitted:
            if not selected_vals:
                st.warning("⚠️ 請至少選擇一個選項")
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
        <div style="text-align: center; padding: 3rem 1rem;">
            <div style="font-size: 5rem; margin-bottom: 1rem;">🎉</div>
            <h2 style="color: #059669 !important;">投票成功！</h2>
            <p style="color: #64748b; font-size: 1.1rem;">感謝您的參與，您的意見對我們很重要。</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("查看即時統計"):
            st.session_state['page'] = 'stats'
            st.rerun()
    with col2:
        if st.button("返回首頁"):
            st.session_state['page'] = 'home'
            st.rerun()

def page_stats(data):
    st.title("📊 投票統計結果")
    
    votes = data['votes']
    total_votes = len(votes)
    
    # 頂部概覽卡片
    st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 2rem; display: flex; align-items: center; justify-content: space-between;">
            <span style="color: #64748b; font-weight: 600;">總投票人數</span>
            <span style="color: #4F46E5; font-size: 1.5rem; font-weight: 800;">{}</span>
        </div>
    """.format(total_votes), unsafe_allow_html=True)
    
    if total_votes == 0:
        st.info("目前尚無投票數據")
        if st.button("返回首頁"):
            st.session_state['page'] = 'home'
            st.rerun()
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

    # 圖表切換
    chart_view = st.radio("圖表類型", ["直條統計圖", "圓形統計圖"], horizontal=True, label_visibility="collapsed")
    
    if chart_view == "直條統計圖":
        fig = px.bar(
            df, 
            x='票數', 
            y='選項', 
            orientation='h', 
            text='票數',
            color='選項',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(size=14),
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = px.pie(
            df, 
            values='票數', 
            names='選項', 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=14),
             margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
        
    st.write("")
    if st.button("返回首頁", key="back_from_stats"):
        st.session_state['page'] = 'home'
        st.rerun()

def page_admin(data):
    st.title("⚙️ 管理後台")
    
    # 簡單的登入驗證
    if 'admin_auth' not in st.session_state:
        st.session_state['admin_auth'] = False
        
    if not st.session_state['admin_auth']:
        with st.form("login_form"):
            st.write("### 管理員登入")
            pwd = st.text_input("輸入管理密碼", type="password")
            if st.form_submit_button("登入"):
                if pwd == data['password']:
                    st.session_state['admin_auth'] = True
                    st.rerun()
                else:
                    st.error("密碼錯誤")
        return

    # 登入後介面
    tab1, tab2, tab3 = st.tabs(["📊 數據導出", "🔒 安全設定", "🛠 系統設定"])
    
    with tab1:
        st.subheader("原始數據")
        votes_df = pd.DataFrame(data['votes'])
        st.dataframe(votes_df, use_container_width=True)
        
        st.subheader("匯出選項")
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            if not votes_df.empty:
                # 處理多選轉字串
                export_df = votes_df.copy()
                export_df['option'] = export_df['option'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
                csv = export_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載 CSV 檔案", csv, f"votes_{datetime.date.today()}.csv", "text/csv")
            else:
                st.button("📥 下載 CSV 檔案", disabled=True)
        
        with col_d2:
            if st.button("📄 產生 PDF 報告"):
                download_font_if_needed()
                if not os.path.exists(FONT_FILE):
                    st.error(f"字型下載失敗，無法產生 PDF。")
                else:
                    try:
                        pdf = ReportPDF()
                        pdf.add_font("NotoSansTC", "", FONT_FILE, uni=True)
                        pdf.add_page()
                        
                        # PDF 內容
                        pdf.set_font("NotoSansTC", "", 20)
                        pdf.cell(0, 15, f"{data['title']} - 統計報告", 0, 1, 'C')
                        pdf.ln(5)
                        
                        pdf.set_font("NotoSansTC", "", 12)
                        total = len(data['votes'])
                        pdf.cell(0, 10, f"報告產生時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)
                        pdf.cell(0, 10, f"總投票數: {total}", 0, 1)
                        
                        # 計算
                        all_selected = []
                        for v in data['votes']:
                            opt = v['option']
                            if isinstance(opt, list): all_selected.extend(opt)
                            else: all_selected.append(opt)
                        counts = {opt: 0 for opt in data['options']}
                        for opt in all_selected:
                            if opt in counts: counts[opt] += 1
                        
                        pdf.ln(10)
                        # 表格標頭
                        pdf.set_fill_color(240, 240, 240)
                        pdf.set_font("NotoSansTC", "", 12)
                        pdf.cell(140, 10, "選項名稱", 1, 0, 'L', 1)
                        pdf.cell(40, 10, "得票數", 1, 1, 'R', 1)
                        
                        # 表格內容
                        for name in data['options']:
                            pdf.cell(140, 10, name, 1, 0, 'L')
                            pdf.cell(40, 10, str(counts[name]), 1, 1, 'R')
                            
                        pdf_bytes = pdf.output(dest='S').encode('latin-1')
                        st.download_button("點此下載 PDF", pdf_bytes, "report.pdf", "application/pdf")
                    except Exception as e:
                        st.error(f"PDF 錯誤: {e}")
        
        st.divider()
        with st.expander("⚠️ 危險區域：清除數據"):
            st.warning("此動作無法復原！將清空所有投票紀錄。")
            if st.button("確認重設所有數據", type="primary"):
                data['votes'] = []
                save_data(data)
                st.success("數據已清空")
                st.rerun()

    with tab2:
        st.subheader("修改管理員密碼")
        new_pwd_input = st.text_input("新密碼", type="password")
        if st.button("確認更改"):
            if len(new_pwd_input) > 8:
                st.error("❌ 密碼過長 (最多 8 位)")
            elif not (re.search(r"[a-zA-Z]", new_pwd_input) and re.search(r"[0-9]", new_pwd_input)):
                st.error("❌ 需包含英文與數字")
            else:
                data['password'] = new_pwd_input
                save_data(data)
                with st.spinner("正在更新並發送通知信..."):
                    sent = send_password_email(new_pwd_input)
                    if sent:
                        st.success(f"✅ 密碼已更新，通知信已發送至 rme@catholic.edu.hk")
                    else:
                        st.warning("⚠️ 密碼已更新，但 Email 發送失敗 (請檢查 Secrets)")

    with tab3:
        st.subheader("一般設定")
        
        new_title = st.text_input("APP 標題", data['title'])
        if st.button("更新標題"):
            data['title'] = new_title
            save_data(data)
            st.success("標題已更新")
            st.rerun()
            
        st.divider()
        st.subheader("投票規則")
        
        enable_multi = st.checkbox("啟用多選功能 (Multi-select)", value=data['config']['enableMultiSelect'])
        max_sel = st.number_input("多選上限數", min_value=1, max_value=len(data['options']), value=data['config']['maxSelections'])
        
        if st.button("儲存規則設定"):
            data['config']['enableMultiSelect'] = enable_multi
            data['config']['maxSelections'] = max_sel
            save_data(data)
            st.success("規則已更新")
            st.rerun()

    st.write("")
    if st.button("登出管理員", type="secondary"):
        st.session_state['admin_auth'] = False
        st.rerun()

# --- 主程式進入點 ---
def main():
    st.set_page_config(
        page_title="RMES Polling", 
        page_icon="🗳️", 
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # 注入 CSS
    inject_custom_css()
    
    # 載入資料
    data = load_data()
    
    # 初始化 Session State
    if 'page' not in st.session_state:
        st.session_state['page'] = 'home'

    # 側邊欄導航 (雖然隱藏 Header, 但 Sidebar 仍可用於快速切換測試)
    with st.sidebar:
        st.header("功能選單")
        if st.button("🏠 投票首頁", use_container_width=True):
            st.session_state['page'] = 'home'
            st.rerun()
        if st.button("📊 統計結果", use_container_width=True):
            st.session_state['page'] = 'stats'
            st.rerun()
        if st.button("⚙️ 管理後台", use_container_width=True):
            st.session_state['page'] = 'admin'
            st.rerun()
        st.divider()
        st.caption("RMES Polling App v2.0")

    # 路由控制
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
