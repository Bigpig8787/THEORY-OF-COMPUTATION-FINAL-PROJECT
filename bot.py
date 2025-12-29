import discord
import requests
import json
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

LLM_API_URL = "YOUR_LLM_URL"        # OLLAMA LLM URL
LLM_API_KEY = "YOUR_LLM_KEY"        # OLLAMA LLM Service Key
SERPER_API_KEY = "YOUR_SERPER_KEY"  # Google Serper API Key
YOUTUBE_API_KEY = "YOUR_YOUTUBE_KEY" # YouTube Data API v3 Key
DISCORD_TOKEN = "YOUR_DISCORD_TOKEN" # Discord Bot Token
MODEL_NAME = "gpt-oss:120b"

def call_ollama(prompt, system_prompt="", json_mode=False):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }
    
    
    payload = {
        "model": MODEL_NAME, 
        "prompt": prompt,
        "system": system_prompt, 
        "stream": False
    }

    if json_mode:
        payload["format"] = "json"

    try:
        response = requests.post(LLM_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            print(f"Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None


def search_with_serper(query):
    serper_url = "https://google.serper.dev/search"
    
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    payload = json.dumps({
        "q": query,
        "num": 10
    })

    response = requests.post(serper_url, headers=headers, data=payload)
    
    if response.status_code == 200:
        results = response.json()
        search_context = ""
        for item in results.get('organic', []):
            search_context += f"標題: {item['title']}\n摘要: {item['snippet']}\n連結: {item['link']}\n\n"
        return search_context
    else:
        return "search fail"
    
def search_youtube(query):
    api_key = YOUTUBE_API_KEY
    base_url = "https://www.googleapis.com/youtube/v3/search"
    
    params = {
        'part': 'snippet',
        'q': query,
        'key': api_key,
        'maxResults': 3, # 抓前3部就好
        'type': 'video'
    }
    
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        videos = response.json().get('items', [])
        # 整理成 Discord 連結 (Discord 會自動展開影片)
        links = [f"https://www.youtube.com/watch?v={v['id']['videoId']}" for v in videos]
        return "\n".join(links)
    return "找不到影片 QQ"

def requests_classify(user_input):
    # 1. 呼叫 LLM
    response_str = call_ollama(user_input, ROUTER_PROMPT, json_mode=False)
    
    if not response_str:
        print(" API 回傳失敗")
        return "GENERAL", user_input

    print(f"LLM 原始回傳: {response_str}") 

    # 2. 設定預設值
    intent = "GENERAL"
    keyword = user_input

    # 3. 使用 Regex 解析
    try:
        # 抓取 intent:
        intent_match = re.search(r"intent:\s*([A-Z]+)", response_str, re.IGNORECASE)
        if intent_match:
            intent = intent_match.group(1).upper() # 強制轉大寫，確保是 VIDEO 不是 video

        # 抓取 keyword:
        keyword_match = re.search(r"keyword:\s*(.+)", response_str, re.DOTALL | re.IGNORECASE)
        if keyword_match:
            keyword = keyword_match.group(1).strip()
            
    except Exception as e:
        print(f"解析發生錯誤: {e}")

    if not keyword:
        keyword = user_input

    print(f"最終分析結果 -> 意圖: {intent}, 關鍵字: {keyword}")
    return intent, keyword

ROUTER_PROMPT = (
    "You are a K-pop intent classifier. "
    "Your ONLY task is to analyze the user input and output the result in a specific text format. "
    "Do NOT use JSON. Do NOT output Markdown. Do NOT explain. "
    "\n\n"
    "Output Format must be exactly like this:\n"
    "intent: <INTENT_CATEGORY>\n"
    "keyword: <SEARCH_KEYWORDS>"
    "\n\n"
    "Intent Categories:\n"
    "- VIDEO: performance, mv, fancam, cover, variety show.\n"
    "- SCHEDULE: concert, fan meeting, comeback date, ticket info, location.\n"
    "- GENERAL: profile, age, birthday, facts, or other questions.\n"
    "\n"
    "Examples:\n"
    "Input: '我想看海媛的直拍' -> Output:\nintent: VIDEO\nkeyword: NMIXX Haewon fancam\n\n"
    "Input: 'NewJeans 演唱會時間' -> Output:\nintent: SCHEDULE\nkeyword: NewJeans concert schedule"
)

keyword_system_prompt = (
            "You are a keyword extraction tool. \n"
            "Your ONLY task is to extract the search query from the user's input. \n"
            "Output ONLY the keywords. Do not explain. Do not apologize. Do not refuse. "
        )

answer_system_prompt = (
            "Role: You are a professional K-pop information organization assistant.\n"
            "Task: Summarize the provided SEARCH RESULTS to answer the USER QUESTION specifically.\n"
            "Output Language: Traditional Chinese (Taiwan).\n"
            "Rules:\n"
            "1. Relevance: Only include key points directly related to the question. Remove fluff or ads.\n"
            "2. Structure: Use clear bullet points and organize information chronologically if applicable.\n"
            "3. Honesty: If the provided data does not contain the answer, politely state that no relevant info was found.\n"
            "4. Tone: Maintain an objective, fluent, and helpful tone.\n"
            "5. The string length cannot exceed 800 characters."
        )

SCHEDULE_SYSTEM_PROMPT = (
    "你是一個專業的 K-pop 行程管理員。"
    "請根據提供的搜尋資料，整理出行程表，並遵守以下嚴格規則："
    "1. 【排序】：必須依照日期『由近到遠』排序 (Chronological Order)。"
    "2. 【格式】：請使用 Markdown 表格呈現，欄位順序為：『時間 | 地點 | 活動名稱 | 參加成員』。"
    "3. 【內容】：若搜尋結果中沒有地點或成員，請填寫『待定』或『全員』。"
    "4. 【日期格式】：請統一轉換為 `MM/DD (週X)` 的格式。"
    "5. 【語言】：使用台灣繁體中文。"
)

# client是跟discord連接，intents是要求機器人的權限
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents = intents)

# 調用event函式庫
@client.event
# 當機器人完成啟動
async def on_ready():
    print(f"目前登入身份 --> {client.user}")

@client.event
# 當頻道有新訊息
async def on_message(message):
    # 排除機器人本身的訊息，避免無限循環
    if message.author == client.user:
        return
    
    if client.user.mentioned_in(message):
        user_input = message.content.replace(f'<@{client.user.id}>', '').replace(f'<@!{client.user.id}>', '').strip()
        
        await message.channel.send(f"正在分析問題")

        # 第一階段: 分類要求
        
        category, keyword = requests_classify(user_input)

        # 第二階段: 執行對應function

        await message.channel.send(f"正在幫您收集資料")

        if category == 'GENERAL':

            print(keyword)
            search_results = search_with_serper(keyword)
            
            final_answer = call_ollama(search_results, f"here is question{user_input} and the promt{answer_system_prompt}") 
            
        
        elif category == 'VIDEO':
            final_answer = search_youtube(keyword)

        
        elif category == 'SCHEDULE':
            print(keyword)
            search_results = search_with_serper(keyword)
            
            final_answer = call_ollama(search_results, f"here is question{user_input} and the promt{SCHEDULE_SYSTEM_PROMPT}")

        await message.channel.send(final_answer)
        
        

client.run(DISCORD_TOKEN)