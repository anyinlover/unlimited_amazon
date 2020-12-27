import re
from selenium import webdriver
from datetime import datetime
from selenium.common.exceptions import NoSuchElementException, NoSuchFrameException, TimeoutException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import pandas as pd


def get_isbns(driver, url):
    asins = set()
    driver.get(url)
    while True:
        books = driver.find_elements_by_xpath("//div[@class='s-main-slot s-result-list s-search-results sg-row']/div[@data-uuid]")
        for book in books:
            asins.add(book.get_attribute("data-asin"))
        try:
            driver.find_element_by_xpath("//li[@class='a-last']").click()
            WebDriverWait(driver,10).until(EC.visibility_of_element_located((By.CLASS_NAME, "a-pagination")))
        except NoSuchElementException:
            break
    
    return asins


def get_books(driver, douban_driver, book_url, asins):
    books = []
    for asin in asins:
        driver.get(book_url + asin)
        if driver.title == "Amazon CAPTCHA":
            print("Go to Check!!!")
            WebDriverWait(driver,3600).until(EC.title_contains("Kindle"))
        
        name = driver.find_element_by_xpath("//span[@id='productTitle']").text
        author = driver.find_element_by_xpath("//span[@class='author notFaded']/a[@class='a-link-normal']").text
        content = driver.find_element_by_xpath("//div[@id='detailBullets_feature_div']").text
        publisher = ""
        pubdate = ""
        for line in content.split('\n'):
            if "出版社" in line:
                info = line.split('(')
                publisher = info[0][5:].split(";")[0]
                pubdate = info[-1][:-1]
                break
        
        try:
            star = driver.find_element_by_xpath("//span[@data-hook='rating-out-of-text']").text.split('，')[0]
        except NoSuchElementException:
            star = "0"
        
        name = clear_name(name)
        isbn = find_isbn(driver, name)

        isbn, douban, people = get_douban(douban_driver, isbn, name, publisher, pubdate)
        
        books.append((asin, name, author, publisher, pubdate, isbn, star, douban, people))
    return books

def find_isbn(driver, name):
    isbn = ""
    if driver.find_elements_by_xpath("//div[@id='ebooksSitbLogo']"):
        driver.find_element_by_xpath("//div[@id='ebooksImageBlock']").click()
        
        body = ""
        try:
            WebDriverWait(driver,15).until(EC.visibility_of_element_located((By.ID, 'sitbReaderKindleSample')))
            driver.switch_to.frame("sitbReaderFrame")
            body = driver.find_element_by_xpath("//body").text
        except TimeoutException:
            print(name + " read timeout")
        except NoSuchFrameException:
            body = driver.find_element_by_xpath("//div[@id='sitbReaderKindleSample']").text
        
        if body:
            isbn = extract_isbn(body)

    return isbn

def clear_name(name):
    if "（" in name:
        name = name.split("（")[0]
    elif "【" in name:
        name = name.split("【")[0]
    elif "(" in name:
        name = name.split("(")[0]
    
    return name.strip()

def clear_isbn(isbn):
    if len(isbn) > 13 and "978" in isbn:
        i = isbn.find("978")
        isbn = isbn[i:i+13]
    
    if len(isbn) == 13 and isbn.startswith("978"):
        return isbn
    else:
        print(isbn + " is not correct.")
        return ""
    


def get_douban(douban_driver, isbn, name, publisher, pubdate):
    if isbn:
        result = search_isbn(douban_driver, isbn)
        if not result:
            result = search_name(douban_driver, name, publisher, pubdate)
    else:
        result = search_name(douban_driver, name, publisher, pubdate)
    
    if result:
        return result
    else:
        return isbn, "", ""

def search_isbn(douban_driver, isbn):

    sbox = douban_driver.find_element_by_xpath("//input[@id='inp-query']")
    sbox.clear()
    sbox.send_keys(isbn)
    sbox.submit()
    
    result = get_rate(douban_driver)
    if result:
        return isbn, *result
    else:
        print(isbn + " has no douban result.")
    
def search_name(douban_driver, name, publisher, pubdate):
    sbox = douban_driver.find_element_by_xpath("//input[@id='inp-query']")
    sbox.clear()
    sbox.send_keys(name)
    sbox.submit()
    items = douban_driver.find_elements_by_xpath("//div[@class='item-root']")
    for item in items:
        try:
            metas = item.find_element_by_xpath(".//div[@class='meta abstract']").text
            year = int(pubdate[:4])
            years = [year-1, year, year+1]
            if publisher.split("出")[0] in metas and any(str(year) in metas for year in years):
                douban, people = get_rate(item)
                item.find_element_by_xpath(".//div[@class='title']//a").click()
                infos = douban_driver.find_element_by_xpath("//div[@id='info']").text
                isbn = extract_isbn(infos)
                douban_driver.back()
                return isbn, douban, people
        except NoSuchElementException:
            continue

def get_rate(item):
    try:
        people = item.find_element_by_xpath(".//span[@class='pl']").text
        if people == ("(评价人数不足)" or "(目前无人评价)"):
            star = "0"
            ps = "0"
        else:
            ps = re.sub("\D", "", people)
            star = item.find_element_by_xpath(".//span[@class='rating_nums']").text
        return star, ps
    except NoSuchElementException:
        return

def extract_isbn(body):
    for line in body.split('\n'):
        if re.search("ISBN", line, re.IGNORECASE):
            isbn = re.sub("\D", "", line)
            isbn = clear_isbn(isbn)
            return isbn
    
    return ""


def main():
    url = "https://www.amazon.cn/s?rh=n%3A2332900071&fs=true&ref=lp_2332900071_sar"
    book_url = "http://www.amazon.cn/dp/"
    douban_url = "https://book.douban.com/"
    with webdriver.Chrome() as driver:
        isbns = get_isbns(driver, url)
        with webdriver.Chrome() as douban_driver:
            douban_driver.get(douban_url)
            books = get_books(driver, douban_driver, book_url, isbns)
    df = pd.DataFrame(books, columns=["asin", "name", "author", "publisher", "pubdate", "isbn", "star", "douban", "people"])
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    df.to_csv(f"data/time_unlimited_{timestamp}.csv")

if __name__ == "__main__":
    main()

