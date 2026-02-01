import streamlit as st
import google.generativeai as genai
from st_supabase_connection import SupabaseConnection

# --- 1. 頁面配置 ---
st.set_page_config(page_title="Snail Protocol (Online)", page_icon="🐌", layout="centered")

# --- 2. 連接配置 ---
# 初始化 Supabase 連接
# 注意：這裡會自動去讀取 .streamlit/secrets.toml 裡的配置
conn = st.connection("supabase", type=SupabaseConnection)

# 初始化 Gemini
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("請配置 GOOGLE_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. 核心函數：修復了這裡的語法錯誤 ---

def load_story():
    """從 Supabase 讀取所有劇情"""
    # 舊寫法 (錯誤): conn.query(...) 
    # 新寫法 (正確): 直接調用 Supabase 的 select 語法
    # .order("created_at") 確保劇情按時間順序排列
    try:
        response = conn.table("story_logs").select("*").order("created_at").execute()
        return response.data
    except Exception as e:
        st.error(f"讀取數據庫出錯: {e}")
        return []

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

# 如果數據庫是空的，初始化第一條
if not story_data:
    intro_text = "【服務器廣播】鏈接建立。我是想吃螺螄粉的AI。誰能給我送個外賣？"
    add_entry("assistant", intro_text)
    st.rerun()

# 顯示所有歷史消息
for msg in story_data:
    avatar = "🐌" if msg['role'] == "assistant" else "🧑‍💻"
    with st.chat_message(msg['role'], avatar=avatar):
        st.markdown(msg['content'])

# --- 5. 交互邏輯 ---

if user_input := st.chat_input("貢獻你的劇情 (將被永久記錄)..."):
    
    # 1. 用戶回合：寫入數據庫
    add_entry("user", user_input)
    st.rerun()

# 檢查是否輪到 AI 回復 (最後一條是 User 發的)
if story_data and story_data[-1]['role'] == "user":
    with st.chat_message("assistant", avatar="🐌"):
        with st.spinner("AI 正在讀取全球數據庫並思考..."):
            
            # 取最近 20 條作為上下文
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
            
            try:
                response = model.generate_content(prompt)
                ai_reply = response.text
                
                st.markdown(ai_reply)
                
                # 2. AI 回合：寫入數據庫
                add_entry("assistant", ai_reply)
                st.rerun()
                
            except Exception as e:
                st.error(f"AI 掉線了: {e}")

if st.button("🔄 刷新查看最新劇情"):
    st.rerun()
