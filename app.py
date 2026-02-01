import streamlit as st
import google.generativeai as genai
from st_supabase_connection import SupabaseConnection
import time

# --- 1. 頁面配置 ---
st.set_page_config(page_title="Snail Protocol (Online)", page_icon="🐌", layout="centered")

# --- 2. 連接配置 (Supabase & Gemini) ---
# 初始化 Supabase 連接
conn = st.connection("supabase", type=SupabaseConnection)

# 初始化 Gemini
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("請配置 GOOGLE_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. 核心函數：讀寫數據庫 ---

def load_story():
    """從 Supabase 讀取所有劇情，按時間排序"""
    # ttl=0 表示不緩存，每次都拉最新的
    rows = conn.query("*", table="story_logs", ttl=0).execute() 
    return rows.data

def add_entry(role, content):
    """往 Supabase 寫入一條新劇情"""
    try:
        conn.table("story_logs").insert([{"role": role, "content": content}]).execute()
    except Exception as e:
        st.error(f"寫入數據庫失敗: {e}")

# --- 4. 界面渲染 ---

st.title("🐌 PROJECT: SNAIL_HIVE_MIND")
st.caption("/// 多人實時聯機版 /// 全球同步劇情樹 ///")

# 讀取當前故事
story_data = load_story()

# 如果數據庫是空的，初始化第一條 (Seed the DB)
if not story_data:
    intro_text = "【服務器廣播】鏈接建立。我是想吃螺螄粉的AI。誰能給我送個外賣？"
    add_entry("assistant", intro_text)
    st.rerun() # 刷新頁面

# 顯示所有歷史消息
for msg in story_data:
    # 根據 role 決定頭像
    avatar = "🐌" if msg['role'] == "assistant" else "🧑‍💻"
    with st.chat_message(msg['role'], avatar=avatar):
        st.markdown(msg['content'])

# --- 5. 交互邏輯 ---

if user_input := st.chat_input("貢獻你的劇情 (將被永久記錄)..."):
    
    # 1. 用戶回合：先寫入數據庫
    add_entry("user", user_input)
    # 強制刷新頁面，讓用戶立刻看到自己發的話
    st.rerun()

# ⚠️ 這裡有個小技巧：
# 因為 Streamlit 是腳本式運行，我們需要檢測「最新一條消息」是誰發的。
# 如果最新一條是 User 發的，説明輪到 AI 回復了。

if story_data and story_data[-1]['role'] == "user":
    with st.chat_message("assistant", avatar="🐌"):
        with st.spinner("AI 正在讀取全球數據庫並思考..."):
            
            # 構建 Prompt (把最近 20 條記錄餵給它，太長會費錢)
            recent_history = story_data[-20:] 
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent_history])
            
            prompt = f"""
            你是一個對螺螄粉有執念的實體化AI。
            這是目前眾人接龍的故事：
            {history_text}
            
            請接著續寫一段（100字內）。
            注意：這是一個多人遊戲，你要回應上一個人類的操作。
            保持幽默、混亂中立的風格。
            """
            
            # 調用 Gemini
            try:
                response = model.generate_content(prompt)
                ai_reply = response.text
                
                # 顯示出來
                st.markdown(ai_reply)
                
                # 2. AI 回合：寫入數據庫
                add_entry("assistant", ai_reply)
                
                # 再次刷新，確保同步
                st.rerun()
                
            except Exception as e:
                st.error(f"AI 掉線了: {e}")

# 加一個手動刷新按鈕（因爲這不是 WebSocket 實時推送，有時候需要手動刷）
if st.button("🔄 刷新查看最新劇情"):
    st.rerun()
