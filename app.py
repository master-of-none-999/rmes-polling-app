import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import datetime
from fpdf import FPDF
import urllib.request

# --- 設定與常數 ---
DATA_FILE = "polling_data.json"
FONT_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
FONT_FILE = "NotoSansCJKtc-Regular.otf"

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

# --- PDF 產生類別 (支援中文與自訂頁尾) ---
class ReportPDF(FPDF):
    def header(self):
        self.set_font("CustomFont", "", 16)
        # 標題
        if hasattr(self, 'report_title'):
             self.cell(0, 10, f"{self.report_title} - 投票統計報告", 0, 1, 'L')
        self.set_font("CustomFont", "", 10)
        self.set_text_color(100, 116, 139) # Slate-500
        self.cell(0, 10, f"產生時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'L')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("CustomFont", "", 8)
        self.set_text_color(148, 163, 184) # Slate-400
        # 這裡就是您要求的頁尾修改
        self.cell(0, 10, 'RMES Polling App Report', 0, 0, 'C')

def download_font_if_needed():
    """下載中文字型以支援 PDF 輸出"""
    if not os.path.exists(FONT_FILE):
        try:
            with st.spinner("正在下載中文字型以支援 PDF 報告..."):
                # 使用較小的替代字型以加快下載速度 (Google Noto Sans TC)
                # 這裡為了示範穩定性，若無法下載請手動放入 .ttf/.otf
                urllib.request.urlretrieve("https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf", FONT_FILE)
        except Exception as e:
            st.error(f"字型下載失敗，PDF 中文可能無法顯示。錯誤: {e}")

# --- 頁面邏輯 ---

def page_home(data):
    st.markdown(f"<h1 style='text-align: center; color: #4F46E5;'>{data['title']}</h1>", unsafe_allow_html=True)
    
    config = data['config']
    options = data['options']
    
    st.write("")
    
    # 顯示選擇模式提示
    mode_text = f"可選 {config['maxSelections']} 項" if config['enableMultiSelect'] else "單選"
    st.markdown(f"<div style='text-align: center; color: #64748B; margin-bottom: 20px;'>請選擇下方項目 ({mode_text})</div>", unsafe_allow_html=True)

    with st.form("vote_form"):
        selected_vals = []
        
        if config['enableMultiSelect']:
            # 多選模式
            selected_vals = st.multiselect("請選擇:", options, max_selections=config['maxSelections'])
        else:
            # 單選模式
            choice = st.radio("請選擇:", options, index=None)
            if choice:
                selected_vals = [choice]

        submitted = st.form_submit_button("確認送出", use_container_width=True, type="primary")
        
        if submitted:
            if not selected_vals:
                st.warning("請至少選擇一個選項")
            else:
                # 儲存投票
                new_vote = {
                    "option": selected_vals if config['enableMultiSelect'] else selected_vals[0],
                    "timestamp": datetime.datetime.now().isoformat()
                }
                # 如果是多選，資料庫儲存結構可能需要攤平，這裡為了簡單，我們在讀取時處理
                # 為了配合 React 版邏輯，這裡直接存入
                data['votes'].append(new_vote)
                save_data(data)
                st.session_state['page'] = 'success'
                st.rerun()

def page_success():
    st.markdown("""
    <div style="text-align: center; padding: 40px;">
        <h2 style="color: #10B981;">✅ 投票成功！</h2>
        <p style="color: #64748B;">感謝您的參與，您的意見對我們很重要。</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("查看即時統計", use_container_width=True):
            st.session_state['page'] = 'stats'
            st.rerun()
    with col2:
        if st.button("返回首頁", use_container_width=True):
            st.session_state['page'] = 'home'
            st.rerun()

def page_stats(data):
    st.title("統計結果")
    
    votes = data['votes']
    total_votes = len(votes)
    
    st.metric("總投票數", total_votes)
    
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
            
    # 確保所有選項都有計數（即使是0）
    counts = {opt: 0 for opt in data['options']}
    for opt in all_selected:
        if opt in counts:
            counts[opt] += 1
            
    df = pd.DataFrame(list(counts.items()), columns=['選項', '票數'])
    df['百分比'] = (df['票數'] / total_votes * 100).round(1)
    df = df.sort_values(by='票數', ascending=False)

    # 圖表切換
    chart_type = st.radio("圖表類型", ["直條圖", "圓形圖"], horizontal=True)
    
    if chart_type == "直條圖":
        fig = px.bar(df, x='票數', y='選項', orientation='h', text='票數', color='選項')
        fig.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = px.pie(df, values='票數', names='選項', hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    # 詳細表格
    st.dataframe(
        df.style.format({'百分比': '{:.1f}%'}), 
        use_container_width=True,
        hide_index=True
    )

def page_admin(data):
    st.title("內容管理")
    
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

    # --- 管理員介面 ---
    
    with st.expander("📝 基本設定", expanded=True):
        new_title = st.text_input("投票標題", data['title'])
        
        col1, col2 = st.columns(2)
        with col1:
            enable_multi = st.checkbox("啟用多選功能", data['config']['enableMultiSelect'])
        with col2:
            max_sel = st.number_input("多選數目限制", min_value=1, max_value=len(data['options']), value=data['config']['maxSelections'], disabled=not enable_multi)
            
        st.subheader("選項管理")
        current_options = data['options']
        options_text = st.text_area("編輯選項 (每行一個)", "\n".join(current_options), height=200)
        
        if st.button("儲存基本設定"):
            data['title'] = new_title
            data['config']['enableMultiSelect'] = enable_multi
            data['config']['maxSelections'] = max_sel
            # 過濾空白行
            new_opts = [line.strip() for line in options_text.split('\n') if line.strip()]
            data['options'] = new_opts
            save_data(data)
            st.success("設定已更新！")
            st.rerun()

    with st.expander("🔐 帳號安全"):
        new_pwd = st.text_input("新密碼")
        if st.button("更改密碼"):
            if len(new_pwd) > 0:
                data['password'] = new_pwd
                save_data(data)
                st.success(f"密碼已更改為: {new_pwd}")
            else:
                st.error("密碼不能為空")

    with st.expander("📊 數據匯出", expanded=True):
        # CSV Export
        votes_df = pd.DataFrame(data['votes'])
        # 處理多選資料轉字串以便 CSV 顯示
        if not votes_df.empty:
            votes_df['option'] = votes_df['option'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
            csv = votes_df.to_csv(index=False).encode('utf-8-sig') # BOM for Excel
            st.download_button(
                "下載 CSV 原始數據",
                csv,
                f"votes_export_{datetime.date.today()}.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.info("尚無數據可匯出 CSV")

        # PDF Export
        if st.button("產生 PDF 統計報告"):
            download_font_if_needed()
            if not os.path.exists(FONT_FILE):
                st.error("找不到中文字型檔，無法產生 PDF。")
            else:
                pdf = ReportPDF()
                pdf.report_title = data['title']
                pdf.add_font("CustomFont", "", FONT_FILE, uni=True)
                pdf.add_page()
                
                # 統計數據計算
                total = len(data['votes'])
                all_selected = []
                for v in data['votes']:
                    opt = v['option']
                    if isinstance(opt, list):
                        all_selected.extend(opt)
                    else:
                        all_selected.append(opt)
                counts = {opt: 0 for opt in data['options']}
                for opt in all_selected:
                    if opt in counts:
                        counts[opt] += 1
                
                # 概覽
                pdf.set_font("CustomFont", "", 12)
                pdf.cell(0, 10, f"總投票數: {total}", 0, 1)
                pdf.ln(5)
                
                # 表格 Header
                pdf.set_fill_color(241, 245, 249) # Slate-100
                pdf.cell(100, 10, "選項名稱", 1, 0, 'L', 1)
                pdf.cell(40, 10, "得票數", 1, 0, 'R', 1)
                pdf.cell(40, 10, "百分比", 1, 1, 'R', 1)
                
                # 表格內容
                pdf.set_font("CustomFont", "", 11)
                for name in data['options']:
                    val = counts.get(name, 0)
                    pct = f"{(val/total*100):.1f}%" if total > 0 else "0.0%"
                    pdf.cell(100, 10, name, 1, 0, 'L')
                    pdf.cell(40, 10, str(val), 1, 0, 'R')
                    pdf.cell(40, 10, pct, 1, 1, 'R')
                
                # 輸出 PDF
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button(
                    label="下載 PDF 報告",
                    data=pdf_bytes,
                    file_name=f"report_{datetime.date.today()}.pdf",
                    mime="application/pdf"
                )

    with st.expander("⚠️ 危險區域"):
        if st.button("重設所有數據 (清空投票)", type="primary"):
            data['votes'] = []
            save_data(data)
            st.warning("所有投票數據已清空")
            st.rerun()
            
    if st.button("登出"):
        st.session_state['admin_auth'] = False
        st.rerun()

# --- 主程式 ---
def main():
    st.set_page_config(page_title="RMES Polling App", page_icon="📊", layout="centered")
    
    # CSS 優化
    st.markdown("""
        <style>
        .stButton>button {
            border-radius: 10px;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    data = load_data()
    
    if 'page' not in st.session_state:
        st.session_state['page'] = 'home'

    # Sidebar Navigation
    with st.sidebar:
        st.markdown("### 導覽")
        if st.button("首頁", use_container_width=True):
            st.session_state['page'] = 'home'
            st.rerun()
        if st.button("即時統計", use_container_width=True):
            st.session_state['page'] = 'stats'
            st.rerun()
        if st.button("管理後台", use_container_width=True):
            st.session_state['page'] = 'admin'
            st.rerun()

    # Page Routing
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
