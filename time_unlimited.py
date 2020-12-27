import re
import csv
import random
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, NoSuchFrameException, TimeoutException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

def restart():
    global driver
    driver.close()
#    proxy = random.choice(proxies)
#    webdriver.DesiredCapabilities.Chrome['proxy'] = {
#        "httpProxy": proxy,
#        "ftpProxy": proxy,
#        "sslProxy": proxy,
#        "proxyType": "MANUAL",
#    }
#    driver = webdriver.Chrome(chrome_options=option)
    driver = webdriver.Chrome()
    print("restart browser")
#    print("restart browser,proxy: "+proxy)

def getinfo(row):
    if int(row['index']) % 50 == 0:
        restart()
    
    asin = row['asin']
    
    try:
        driver.get("http://www.amazon.cn/dp/" + asin)
    except WebDriverException:
        restart()
        driver.get("http://www.amazon.cn/dp/" + asin)
    
    retry = 0
    while retry < 4:
        if driver.title == ("Amazon CAPTCHA" or "亚马逊"):
            restart()
            driver.get("http://www.amazon.cn/dp/" + asin)
            retry += 1
        else:
            break
#        print("Go to Check!!!")
#        WebDriverWait(driver,3600).until(EC.title_contains("Kindle"))
    if driver.title == "找不到页面":
        return row
    
    name = driver.find_element_by_xpath("//span[@id='productTitle']").text
    try:
        author = driver.find_element_by_xpath("//span[@class='author notFaded']/a[@class='a-link-normal']").text
    except NoSuchElementException:
        author = ""
#    WebDriverWait(driver,15).until(EC.visibility_of_element_located((By.ID, 'detailBullets_feature_div')))
    if driver.find_elements_by_xpath("//div[@id='detailBullets_feature_div']"):
        content = driver.find_element_by_xpath("//div[@id='detailBullets_feature_div']").text
    else:
        content = driver.find_element_by_xpath("//table[@id='productDetailsTable']").text
    publisher = ""
    pubdate = ""
    for line in content.split('\n'):
        if re.search("出版社 :|出版社:", line):
            info = line.split('(')
            publisher = info[0][5:]
            pubdate = info[-1][:-1]
            break

    try:
        star = driver.find_element_by_xpath("//span[@data-hook='rating-out-of-text']").text.split('，')[0]
    except NoSuchElementException:
        star = "0"

    isbn = ""
    if driver.find_elements_by_xpath("//div[@id='ebooksSitbLogo']"):
        driver.find_element_by_xpath("//div[@id='ebooksImageBlock']").click()

    body = ""
    try:
        WebDriverWait(driver,25).until(EC.visibility_of_element_located((By.ID, 'sitbReaderKindleSample')))
        driver.switch_to.frame("sitbReaderFrame")
        body = driver.find_element_by_xpath("//body").text
    except TimeoutException:
        print(name + " read timeout")
    except NoSuchFrameException:
        body = driver.find_element_by_xpath("//div[@id='sitbReaderKindleSample']").text

    if body:
        for line in body.split('\n'):
            if re.search("ISBN", line, re.IGNORECASE):
                isbn = re.sub("\D", "", line)
                break
    print("{}: {} {} done!".format(row["index"], asin, name))
    row["name"] = name
    row["author"] = author
    row["publisher"] = publisher
    row["pubdate"] = pubdate
    row["star"] = star
    row["isbn"] = isbn
    return row

option = webdriver.ChromeOptions()
option.add_argument('headless')
driver = webdriver.Chrome()
# driver = webdriver.Chrome(options=option)

df = pd.read_csv("my_books5.csv", dtype=str, keep_default_na=False)
df1 = df.loc[28995:]
try:
    for index, row in df1.iterrows():
        df1.loc[index] = getinfo(row)
finally:
    df.to_csv("my_books6.csv", index=False)
    driver.close()