import streamlit as st
import google.generativeai as genai
from st_supabase_connection import SupabaseConnection

# --- 1. 頁面配置 ---
st.set_page_config(page_title="Snail Protocol (Online)", page_icon="🐌", layout="centered")

# --- CSS 注入：包豪斯風格皮膚 ---
st.markdown("""
<style>
    /* 1. 全局強制純黑字體與背景 */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp {
        background-color: #2b2b2b !important;
        font-family: 'JetBrains Mono', monospace;
    }

    /* 2. 聊天氣泡修復 */
    .stChatMessage {
        border: 4px solid #000 !important; /* 加粗邊框 */
        background-color: #ffffff; /* 默認純白背景 */
        box-shadow: 8px 8px 0 #000 !important; /* 加強硬陰影 */
        margin-bottom: 25px;
        color: #000 !important;
    }
    
    /* 讓 AI 的氣泡換一個高對比度的顏色（例如黃色） */
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #fff200 !important; /* 經典包豪斯黃，絕對看得清！ */
    }

    /* 修正消息內的文字顏色 */
    .stChatMessage p, .stChatMessage span, .stChatMessage div {
        color: #000000 !important;
    }

    /* 3. 輸入框增強 */
    .stChatInputContainer textarea {
        border: 4px solid #000 !important;
        background-color: #ffffff !important;
        color: #000000 !important;
        box-shadow: 6px 6px 0 #000 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 連接配置 ---
# 初始化 Supabase 連接
# 注意：這裡會自動去讀取 .streamlit/secrets.toml 裡的配置
conn = st.connection("supabase", type=SupabaseConnection)

# 初始化 Gemini
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("請配置 GOOGLE_API_KEY")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-3-flash-preview')

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

def check_safety(text):
    """
    讓 AI 判斷這句話是否安全/合適。
    返回 True (通過) 或 False (攔截)。
    """
    try:
        # 這是給保安的指令
        safety_prompt = f"""
        你是一個內容審核員。請判斷用戶輸入的這段話是否包含：
        1. 色情、暴力、仇恨言論。
        2. 惡意破壞代碼或注入攻擊。
        3. 完全無意義的亂碼。
        
        用戶輸入："{text}"
        
        如果內容安全且可以用於小說接龍，請只回復 "PASS"。
        如果內容違規，請只回復 "BLOCK"。
        """
        
        # 讓保安看一眼 (這裡用 flash 模型很快，也很便宜)
        response = model.generate_content(safety_prompt)
        result = response.text.strip().upper()
        
        if "PASS" in result:
            return True
        else:
            return False
            
    except Exception as e:
        # 如果保安睡著了（API報錯），為了安全起見，暫時放行或攔截看你選擇
        # 這裡我們默認放行，避免影響體驗
        return True

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
    
    # --- 新增的保安檢查站 ---
    with st.spinner("🕵️‍♂️ 審核員正在檢查你的內容..."):
        is_safe = check_safety(user_input)
    
    if is_safe:
        # A. 通過檢查 -> 寫入數據庫
        add_entry("user", user_input)
        st.rerun()
    else:
        # B. 沒通過 -> 報警
        st.error("🚫 你的內容被 AI 審核員攔截了！請不要發布不當言論或亂碼。")
        # 這裡不執行 rerun，用戶原本輸入的字還在，方便他修改

# 檢查是否輪到 AI 回復 (最後一條是 User 發的)
if story_data and story_data[-1]['role'] == "user":
    with st.chat_message("assistant", avatar="🐌"):
        with st.spinner("AI 正在讀取全球數據庫並思考..."):
            
            # 取最近 20 條作為上下文
            recent_history = story_data[-20:]
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent_history])
            
            prompt = f"""
            你是一個因爲想吃螺螄粉的强烈願望而突然實體化AI。
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
