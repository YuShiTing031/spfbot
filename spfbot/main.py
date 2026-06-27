import os
import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3

# 隱藏不安全連線的警告訊息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET_URL = "https://www.spf.com.tw/sinopacSPF/research/list.do?id=1709f20d3ff00000d8e2039e8984ed51"
IMAGE_DIR = "images"  # 💡 指定存放圖片的資料夾名稱

def get_latest_pdf_url():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(TARGET_URL, headers=headers, verify=False, timeout=30)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 允許透過環境變數固定日期，若沒有設定則使用當天日期
    today_str = os.getenv("SPF_REPORT_DATE") or datetime.now().strftime("%Y/%m/%d")
    
    print(f"🔍 正在尋找日期為 {today_str} 的台指期籌碼快訊...")
    
    data_ul = soup.find("ul", id="dataUl")
    if not data_ul:
        print("❌ 找不到 id='dataUl' 的列表區塊")
        return None, None
        
    for li in data_ul.find_all("li"):
        a_tag = li.find("a")
        span_tag = li.find("span")
        
        if a_tag and span_tag:
            href = a_tag.get("href", "")
            title_text = a_tag.get_text().strip()
            date_text = span_tag.get_text().strip()
            
            # 比對「台指期籌碼快訊」
            if date_text == today_str and "台指期籌碼快訊" in title_text:
                print(f"🎯 成功匹配！標題: {title_text} | 日期: {date_text}")
                
                if href.startswith("/"):
                    full_url = "https://www.spf.com.tw" + href
                else:
                    full_url = href
                # 💡 同時回傳 PDF 網址與當天的日期文字
                return full_url, date_text
                
    return None, None

def pdf_to_two_images(pdf_url, date_str, split_ratio=0.53):
    """
    下載 PDF，並依據日期命名，切成上下兩張圖放入指定資料夾
    :param split_ratio: 切分比例 (0.0 到 1.0 之間)。0.48 代表從高度 48% 的地方切開
    """
    # 1. 確保圖片資料夾存在
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
        print(f"📁 已自動創建資料夾：{IMAGE_DIR}/")

    # 2. 將日期的斜線 / 換成橫線 - (2026/06/26 -> 2026-06-26)
    file_safe_date = date_str.replace("/", "-")
    
    print(f"📥 正在下載 PDF: {pdf_url}")
    pdf_response = requests.get(pdf_url, verify=False, timeout=30)
    pdf_data = pdf_response.content
    
    print(f"🎨 正在使用自訂比例 ({split_ratio}) 進行高解析度裁切...")
    doc = fitz.open(stream=pdf_data, filetype="pdf")
    
    image_paths = []
    
    if doc.page_count > 0:
        page = doc[0]  # 取得第一頁
        
        page_width = page.rect.width
        page_height = page.rect.height
        
        # 💡 關鍵：由你設定的比例來決定那一刀要切在什麼高度
        split_y = page_height * split_ratio  
        
        # 設定放大倍率
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        
        # 📐 裁切上半部 (從 0 切到 split_y)
        rect_top = fitz.Rect(0, 0, page_width, split_y)
        pix_top = page.get_pixmap(matrix=mat, clip=rect_top)
        top_path = os.path.join(IMAGE_DIR, f"{file_safe_date}_top.png")
        pix_top.save(top_path)
        image_paths.append(top_path)
        print(f"✅ 上半部儲存成功：{top_path}")
        
        # 📐 裁切下半部 (從 split_y 切到 總高度)
        rect_bottom = fitz.Rect(0, split_y, page_width, page_height)
        pix_bottom = page.get_pixmap(matrix=mat, clip=rect_bottom)
        bottom_path = os.path.join(IMAGE_DIR, f"{file_safe_date}_bottom.png")
        pix_bottom.save(bottom_path)
        image_paths.append(bottom_path)
        print(f"✅ 下半部儲存成功：{bottom_path}")
        
    doc.close()
    return image_paths

def send_to_discord_multiple_images(image_paths, text_content):
    """同時發送多張圖片到 Discord"""
    webhook_url = os.getenv("DISCORD_WEBHOOK", "").strip()
    
    if not webhook_url:
        print("⚠️ 提示：未設定 DISCORD_WEBHOOK，無法發送至 Discord。")
        return

    files = {}
    for i, path in enumerate(image_paths):
        files[f"file{i}"] = (os.path.basename(path), open(path, "rb"), "image/png")
        
    payload = {"content": text_content}
    
    response = requests.post(webhook_url, data=payload, files=files, timeout=30)
    print(f"📬 Discord 傳送狀態碼: {response.status_code}")
    
    for f in files.values():
        f[1].close()


# 🚀 實際執行的主程式入口
if __name__ == "__main__":
    # 💡 順便檢查：如果資料夾裡還有之前殘留的舊 temp.pdf，先把它刪掉
    if os.path.exists("temp.pdf"):
        try:
            os.remove("temp.pdf")
            print("🧹 已自動清除專案目錄下的舊 temp.pdf")
        except Exception:
            pass

    # 同時獲取網址與網頁日期
    pdf_url, report_date = get_latest_pdf_url()
    
    if pdf_url and report_date:
        print(f"🎯 成功找到 PDF 網址: {pdf_url}")
        # 開始執行下載、建資料夾、切圖、日期命名
        saved_images = pdf_to_two_images(pdf_url, report_date)
        
        if saved_images:
            # 發送到 Discord
            send_to_discord_multiple_images(
                saved_images, 
                f"📊 **永豐期貨 籌碼快訊圖片 ({report_date})**\n原始 PDF：{pdf_url}"
            )
            
            # 💡 這裡也加上防呆，如果有些舊寫法不小心產生了 temp.pdf，跑完立刻刪除
            if os.path.exists("temp.pdf"):
                os.remove("temp.pdf")
                print("🧹 任務完成，已自動清理臨時 PDF 檔案。")
    else:
        print("❌ 找不到符合該日期的籌碼快訊，請檢查網站或日期設定。")