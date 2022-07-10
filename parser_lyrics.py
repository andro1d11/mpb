from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By


class lyrics_parser():
    ua = dict(DesiredCapabilities.CHROME)
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('window-size=1920x935')
    browser = webdriver.Chrome(options=options, executable_path="extra/other/chromedriver.exe")

    def get_tracks(self, track_name, browser=browser, options=options):
        url = 'https://genius.com/search?q=' + track_name
        browser.get(url)
        data = browser.find_elements(By.CLASS_NAME, 'mini_card')
        tracks = {}
        for i in data:
            try:
                tracks[f"{i.find_element(By.CLASS_NAME, 'mini_card-subtitle').text} - {i.find_element(By.CLASS_NAME, 'mini_card-title').text}"] = i.get_attribute('href')
            except:
                continue
        self.__open_x(browser)
        return tracks

    def get_lyrics(self, url, browser=browser):
        browser.get(url)
        data = browser.find_elements(By.CLASS_NAME, 'Lyrics__Container-sc-1ynbvzw-6')
        lyrics = ''
        for i in data:
            lyrics += i.text
        self.__open_x(browser)
        return lyrics
    
    def __open_x(self, browser=browser):
        browser.get('http://x.com/')

    def quit_webdriver(self, browser=browser):
        browser.quit()

if __name__ == '__main__':
    t = lyrics_parser()
    a = t.get_tracks('Терновый венец эволюции')
    b = t.get_lyrics("https://genius.com/Pyrokinesis-crown-of-evolution-throns-lyrics")