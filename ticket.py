from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.alert import Alert
import time
import uuid
import cv2
from PIL import Image
import base64
import json
import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


# 全局变量
chromedriver_path = "/opt/homebrew/bin/chromedriver"
web_url = "https://tixcraft.com/activity/detail/24_asmrmaxxx"
API_KEY = ''
client_key = ''
usemastcard = False
cardnum = ''
selectDay = 2

# 初始化 WebDriver
def init_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.debugger_address = "localhost:9014"
    chrome_options.add_argument("--disable-features=SharedArrayBuffer")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# 打开网页并加载元素
def load_page(driver, url):
    driver.get(url)
    while True:
        try:
            game_list = click_buyload(driver)
            # 等待按钮加载完成
            button_loaded = click_table_button(game_list, driver)
            if button_loaded:
                return game_list
            else:
                print("Button not loaded, retrying... (load_page)")
                #time.sleep(0.1)  # 如果按钮未加载，稍作等待再重试
        except Exception as e:
            print(f"loadpage error {e}")
            #time.sleep(0.1)

def click_buyload(driver):
    tab_func = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, "tab-func"))
            )
    buy = tab_func.find_element(By.CLASS_NAME, "buy")
    buy.click()
    
    gameListContainer = WebDriverWait(driver,3).until(
                EC.presence_of_element_located((By.ID, "gameListContainer"))
            )
    game_list = WebDriverWait(driver,3).until(
                EC.presence_of_element_located((By.ID, "gameList"))
            )
    return game_list
                    
def click_table_button(game_list, driver):
    try:
        row_index = selectDay-1
         # 显式等待表格出现
        table = WebDriverWait(game_list, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'table'))
        )
        tbody = table.find_element(By.TAG_NAME, 'tbody')
        
         # 使用 WebDriverWait 等待所有行的存在
        trs = WebDriverWait(tbody, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, 'tr'))
        )
        # 确保 row_index 不超过行数
        if row_index < len(trs):
            tds = trs[row_index].find_elements(By.TAG_NAME, 'td')
        else:   
            tds = trs[0].find_elements(By.TAG_NAME, 'td') 

    
        if len(tds) >= 4:
            fourth_td = tds[3]
            button = WebDriverWait(fourth_td, 10).until(
                EC.element_to_be_clickable((By.TAG_NAME, 'button'))
            )
            if button:
                # 移动到按钮位置
                actions = ActionChains(driver)
                actions.move_to_element(button).perform()
                button.click()
                
                if usemastcard: 
                    mastercard_process(driver)
                    
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "mobileWizard"))
                )
                print("New page loaded, continuing operations...")
                return True 
    except Exception as e:
        print(f"No button found yet: {time.time()}, (click_table_button)")
    
    return False

# 选择座位
def select_seat(driver, selectseat):
    groups = ['group_1','group_2','group_3', 'group_4', 'group_5', 'group_6']
    clicked = False
    selectItem = '0'

    for group_id in groups:
        if clicked:
            break
        
        group_area = selectseat.find_element(By.ID, group_id)
        lis = group_area.find_elements(By.TAG_NAME, 'li')
        
        for li in lis:
            a_tag = li.find_elements(By.TAG_NAME, 'a')
            if not a_tag:
                continue
            try:
                actions = ActionChains(driver)
                actions.move_to_element(li).perform()
                li.click()
                selectItem = group_id.split('_')[1]
                clicked = True
                break
            except Exception as e:
                continue

    if clicked:
        page2 = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "selectqty"))
        )
        return int(selectItem) - 1, page2
    else:
        print("未能点击任何li元素")
        return None, None

# 选择票数
def select_ticket(page2, selectItem, driver):
     # 找到 ticketPriceList 这个表格
    ticketPriceList = page2.find_element(By.ID, 'ticketPriceList')
    
    # 从 ticketPriceList 中查找所有的 select 元素
    select_elements = ticketPriceList.find_elements(By.TAG_NAME, 'select')
    
     # 遍历 select 元素，选择所需的票数
    for select_element in select_elements:
        select = Select(select_element)
        options = select.options
        last_option_value = int(options[-1].get_attribute('value'))

        # 选择票数逻辑
        if last_option_value > 2:
            select.select_by_value('2')
        else:
            select.select_by_value(str(last_option_value))

    checkbox = page2.find_element(By.ID, 'TicketForm_agree')    

    if not checkbox.is_selected():
        driver.execute_script("arguments[0].click();", checkbox)
    else:
        print("Checkbox was already checked")

def getCaptchaImage(driver):
    
    captcha_image = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "TicketForm_verifyCode-image"))
    )
    uid = uuid.uuid4()
    driver.save_screenshot(f"{uid}.png")
    image = Image.open(f"{uid}.png")
    cropped_image = image.crop((1064, 1193, 1300, 1387))
    cropped_image.save(f"{uid}_cropped2.png")
    
    return f"{uid}_cropped2.png"
    
# 获取并处理验证码
def handle_captcha(imagePath):
  
    image = cv2.imread(imagePath, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"图像文件 '{imagePath}' 无法加载。请检查文件路径和格式。")

    encoded_string = None
    with open(imagePath, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())

    dictionary = {
        'contents': [
            {
                'parts': [
                    {'text': '請直接說出看到的文字,不要有多餘的回應'},
                    {
                        'inline_data': {
                            'mime_type': 'image/jpeg',
                            'data': encoded_string.decode('utf-8')
                        }
                    }
                ]
            }
        ]
    }

    return dictionary


# 调用API识别验证码
def recognize_captcha(dictionary):
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}", 
        json=dictionary
    )
    response_json = response.json()

    def get_value(data, key):
        if isinstance(data, dict):
            for k, v in data.items():
                if k == key:
                    return v
                else:
                    value = get_value(v, key)
                    if value is not None:
                        return value
        elif isinstance(data, list):
            for v in data:
                value = get_value(v, key)
                if value is not None:
                    return value
        return None

    response_text = get_value(response_json, "text")
    return response_text.replace(" ", "").replace("\n", "").replace("\t", "")


def recognize_2captcha(imagePath):
    sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

    from twocaptcha import TwoCaptcha

    api_key = os.getenv('APIKEY_2CAPTCHA', client_key)

    solver = TwoCaptcha(api_key)

    try:
        result = solver.normal(f"{imagePath}")
        code_value = result['code']
        print(f"{result}")  
        return code_value
  
    except Exception as e :
        print(f"No button found yet: {e}")  


def recognize_2captchaV2(imagePath):
    start_time = time.time()
    # API 密钥
    
    
    # 读取并转换图像为 base64
    with open(imagePath, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
    
    # 创建任务的请求数据
    create_task_payload = {
        "clientKey": client_key,
        "task": {
            "type": "ImageToTextTask",
            "body": f"data:image/png;base64,{image_base64}",
            "numeric": 2
            
        }
    }
    
    # 第一次 API 调用: 创建任务
    create_task_url = "https://api.2captcha.com/createTask"
    response = requests.post(create_task_url, json=create_task_payload)
    task_response = response.json()
    
    # 检查创建任务是否成功
    if task_response.get("errorId") != 0:
        print(f"Error creating task: {task_response.get('errorDescription')}")
        return None
    
    task_id = task_response.get("taskId")
    print(f"Captcha task_id: {task_id}")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Execution task_id time: {elapsed_time:.2f} seconds")
    time.sleep(0.8)  # 等待 5 秒钟后重试
    # 第二次 API 调用: 获取任务结果
    get_task_result_url = "https://api.2captcha.com/getTaskResult"
    
    while True:
        get_task_payload = {
            "clientKey": client_key,
            "taskId": task_id
        }
        response = requests.post(get_task_result_url, json=get_task_payload)
        task_result = response.json()
        
        # 检查任务是否完成
        if task_result.get("status") == "ready":
            text = task_result["solution"]["text"]
              # 记录结束时间
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Captcha recognized: {text}")
            print(f"Execution time: {elapsed_time:.2f} seconds")
            return text
        
        # 任务尚未完成，等待几秒后重试
        print("Waiting for captcha to be solved...")
        time.sleep(0.2)  # 等待 5 秒钟后重试
  
  
# 填写验证码并提交表单
def submit_form(driver, ocr_str):
    input_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "TicketForm_verifyCode"))
    )
    input_box.send_keys(ocr_str)

    form = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "form-ticket-ticket"))
    )
    submit_button = form.find_element(By.XPATH, './/button[@type="submit"]')
    actions = ActionChains(driver)
    actions.move_to_element(submit_button).perform()
    submit_button.click()

def mastercard_process(driver):
    try:
        promo_page = WebDriverWait(driver, 2).until(
        EC.presence_of_element_located((By.ID, "promo-page")))
         # 找到输入框元素
        input_element = promo_page.find_element(By.NAME, 'checkCode')
        # 向输入框中输入代码
        input_element.send_keys(cardnum)
    
        # 找到提交按钮并点击
        submit_button = promo_page.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()
        
        # 显式等待 alert 弹出，最多等 5 秒
        WebDriverWait(driver, 5).until(EC.alert_is_present())
        
        # 切换到弹出的 alert 弹窗并点击确认按钮
        alert = Alert(driver)
        alert.accept()
  
    except Exception as e :
        print(f"Dont Need MasterCard Process {e}")  
     
    return

# 主程序流程
def main():
    driver = init_driver()
    
    game_list = load_page(driver, web_url)
    selectseat = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "selectseat"))
    )
    selectItem, page2 = select_seat(driver, selectseat)
    
    if page2:
        select_ticket(page2, selectItem, driver)
        imagePath = getCaptchaImage(driver)
        ocr_str = recognize_2captchaV2(imagePath)
        #dictionary = handle_captcha(imagePath)
        #ocr_str = recognize_captcha(dictionary)
        submit_form(driver, ocr_str)
    
    driver.quit()

if __name__ == "__main__":
    main()
