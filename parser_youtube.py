from __future__ import unicode_literals
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
import requests
import pafy
import os


class music_parser():
    ua = dict(DesiredCapabilities.CHROME)
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('window-size=1920x935')
    browser = webdriver.Chrome(options=options, executable_path="extra/other/chromedriver.exe")
    
    def get_urls(self, track_name, browser=browser, options=options):
        ban_cymbols = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        url = 'https://www.youtube.com/results?search_query=' + track_name
        browser.get(url)
        tracks_container = browser.find_element(By.XPATH, '/html/body/ytd-app/div[1]/ytd-page-manager/ytd-search/div[1]/ytd-two-column-search-results-renderer/div/ytd-section-list-renderer/div[2]/ytd-item-section-renderer/div[3]')
        tracks = tracks_container.find_elements(By.TAG_NAME, 'ytd-video-renderer')
        data = {}
        for i in tracks:
            temp_key = i.find_element(By.ID, 'video-title').text
            for j in ban_cymbols:
                temp_key = temp_key.replace(j, '')
            data[temp_key] = (i.find_element(By.ID, 'video-title').get_attribute('href'), i.find_element(By.ID, 'img').get_attribute('src'))
        return data

    def download_track(self, url, img, path, track_name, browser=browser, options=options):
        if img != None:
            try:
                image = requests.get(img)
                out = open(f"extra/files/{track_name}.jpg", "wb")
                out.write(image.content)
                out.close()
            except:
                pass
        result = pafy.new(url)
        best_quality_audio = result.getbestaudio()
        best_quality_audio.download(path)
        for i in os.listdir(path):
            if i.split('.')[-1] in ['3gp', 'm4a', 'm4v', 'mp4', 'webm', 'ogg']:
                os.rename(f'{path}/' + i, f'{path}/' + str(track_name) + '.mp3')
    
    def quit_webdriver(self, browser=browser):
        browser.quit()

if __name__ == "__main__":
    pass