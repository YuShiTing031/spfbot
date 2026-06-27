import os
import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3
import easyocr
import numpy as np
import re
from PIL import Image

# 隱藏警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET_URL = "https://www.spf.com.tw/sinopacSPF/research/list.do?id=1709f20d3ff00000d8e2039e8984ed51"
IMAGE_DIR = "images" 
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

def get_latest_pdf_url():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(TARGET_URL, headers=headers, verify=False)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 自動獲取今天日期
    today_str = datetime.now().strftime("%Y/%m/%d")
    #today_str = "2026/06/26"
    print(f"🔍 正在尋找日期為 {today_str} 的籌碼快訊...")
    
    data_ul = soup.find("ul", id="dataUl")
    for li in data_ul.find_all("li"):
        a_tag, span_tag = li.find("a"), li.find("span")
        if a_tag and span_tag and span_tag.get_text().strip() == today_str:
            href = a_tag.get("href", "")
            return ("https://www.spf.com.tw" + href) if href.startswith("/") else href, today_str
    return None, None

def analyze_image_data(image_path):
    """OCR 辨識核心邏輯"""
    reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)
    results = reader.readtext(np.array(Image.open(image_path)), detail=0)
    text = "\n".join(results)
    
    data = {"大盤": "未找到", "外資": "未找到", "投信": "未找到", "自營": "未找到"}
    
    # 1. 抓取大盤點數 (只抓 20000~100000 的數字)
    for line in results:
        num = re.sub(r"[^\d.]", "", line)
        if num and 20000 < float(num) < 100000:
            data["大盤"] = num
            break
            
    # 2. 抓取法人數據
    for key in ["外資", "投信", "自營"]:
        match = re.search(fr"{key}買賣超[\s\S]*?([+-]?\d+[\d,]*\.\d+|[+-]?\d+)", text)
        if match:
            val = match.group(1)
            data[key] = f"{'+' if not val.startswith(('-', '+')) else ''}{val} 億"
            
    return data

def process_pdf(pdf_url, date_str):
    if not os.path.exists(IMAGE_DIR): os.makedirs(IMAGE_DIR)
    file_date = date_str.replace("/", "-")
    
    pdf_response = requests.get(pdf_url, verify=False)
    doc = fitz.open(stream=pdf_response.content, filetype="pdf")
    page = doc[0]
    
    # 切圖
    paths = []
    for i, rect in enumerate([fitz.Rect(0, 0, page.rect.width, page.rect.height*0.53), 
                              fitz.Rect(0, page.rect.height*0.53, page.rect.width, page.rect.height)]):
        path = os.path.join(IMAGE_DIR, f"{file_date}_{'top' if i==0 else 'bottom'}.png")
        page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect).save(path)
        paths.append(path)
    return paths

def send_to_discord(paths, report):
    files = {f"f{i}": (os.path.basename(p), open(p, "rb"), "image/png") for i, p in enumerate(paths)}
    requests.post(WEBHOOK_URL, data={"content": report}, files=files)
    for f in files.values(): f[1].close()

if __name__ == "__main__":
    url, date = get_latest_pdf_url()
    if url:
        paths = process_pdf(url, date)
        data = analyze_image_data(paths[0])
        
        report = (f"📊 **永豐籌碼分析 ({date})**\n"
                  f"📈 加權指數: {data['大盤']} 點\n"
                  f"💰 外資: {data['外資']} | 💼 投信: {data['投信']} | 🏢 自營: {data['自營']}")
        
        send_to_discord(paths, report)
        print("✅ 任務執行完畢，已發送至 Discord")
    else:
        print("❌ 今日尚無報告或找不到檔案")
