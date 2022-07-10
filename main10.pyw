# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui, QtMultimedia
from PyQt5.QtCore import QThread, QObject
from PyQt5.QtWidgets import QFileDialog
from parser_youtube import music_parser
from parser_lyrics import lyrics_parser
from pypresence import Presence
from datetime import datetime, timedelta
from copy import deepcopy
import win32com.client as com
import threading
import random
import socket
import pyglet
import time
import json
import os


class get_tracks_to_lyrics_thread(QThread):
    def __init__(self, mainWindow, parent=None):
        QObject.__init__(self, parent=parent)
        self.mainWindow = mainWindow
        self.stop_search = 0
        self.mainWindow.tracks_area.clear()
        with open('extra/json/config.json', 'r') as f:
            self.config = json.load(f)

    def run(self):
        try:
            if self.mainWindow.action == 'lyrics':
                self.mainWindow.tracks_area.clear()
                self.mainWindow.tracks_area.addItem('Wait...')
            self.mainWindow.tracks_to_lyrics = parser_lyrics.get_tracks(self.mainWindow.track_to_lyrics_temp)
            if self.mainWindow.action == 'lyrics':
                self.mainWindow.tracks_area.clear()
            self.stop_search += 1
            if self.mainWindow.sidebar.indexFromItem(self.mainWindow.sidebar.currentItem()).row() == 2:
                # If the lyrics are not received 10 times
                if self.stop_search >= 10:
                    if self.mainWindow.action != 'playlist':
                        if self.mainWindow.action == 'lyrics':
                            self.mainWindow.tracks_area.addItem('Lyrics for track not found! :(')
                            self.mainWindow.find_track_bttn.show()
                    self.stop_search = 0
                # Else rerun
                else:

                    if len(list(self.mainWindow.tracks_to_lyrics)) == 0:
                        self.run()
                    # If lyrics found
                    else:
                        if self.mainWindow.action == 'lyrics':
                            for i in list(self.mainWindow.tracks_to_lyrics.keys()):
                                self.mainWindow.tracks_area.addItem(i + '\n')
                            self.mainWindow.action = 'lyrics'
                            self.mainWindow.find_track_bttn.show()
                        self.stop_search = 0
            else:
                self.stop_search = 0
        except Exception as exc:
            self.mainWindow.logs_listwidget.addItem(str(exc))

class get_lyrics_thread(QThread):
    def __init__(self, mainWindow, parent=None):
        QObject.__init__(self, parent=parent)
        self.mainWindow = mainWindow
        with open('extra/json/config.json', 'r') as f:
            self.config = json.load(f)
        with open('extra/json/data.json', 'r', encoding='utf-8') as f:
            self.json_data = json.load(f)
        try:
            self.translated_elements = self.json_data["Translated elements"][self.config["language"]]
        except KeyError:
            self.translated_elements = self.json_data["Translated elements"]["English"]
    def run(self):
        lyrics_track = self.mainWindow.tracks_area.currentItem().text().replace('\n', '')
        try:
            lyrics = parser_lyrics.get_lyrics(self.mainWindow.tracks_to_lyrics[lyrics_track].replace('\n', ''))
            lyrics = lyrics.split('\n')
            if self.mainWindow.action == 'lyrics':
                self.mainWindow.tracks_area.clear()
                for i in lyrics:
                    self.mainWindow.tracks_area.addItem(i)
            # Adding lyrics to temp
            with open('extra/json/temp.json', 'r', encoding='utf-8') as f:
                temp_data = json.load(f)
            temp_data['lyrics_data']['lyrics_track'] = self.mainWindow.track_to_lyrics_temp
            temp_data['lyrics_data']['lyrics'] = lyrics
            lyrics = ''
            with open('extra/json/temp.json', 'w', encoding='utf-8') as f:
                json.dump(temp_data, f, ensure_ascii=False, indent=4)
            temp_data = ''
            del self.mainWindow.tracks_to_lyrics, lyrics
        except:
            pass

class download_track_thread(QThread):
    def __init__(self, mainWindow, parent=None):
        QObject.__init__(self, parent=parent)
        self.mainWindow = mainWindow
        with open('extra/json/config.json', 'r') as f:
            self.config = json.load(f)
        with open('extra/json/data.json', 'r', encoding='utf-8') as f:
            self.json_data = json.load(f)
        try:
            self.translated_elements = self.json_data["Translated elements"][self.config["language"]]
        except KeyError:
            self.translated_elements = self.json_data["Translated elements"]["English"]

    def download_asynchronously(self, url, img_url, path, song_name):
        dt = threading.Thread(target=lambda: parser_youtube.download_track(url, img_url, path, song_name))
        try:
            dt.start()
            while True:
                if not dt.is_alive():
                    for i in range(self.mainWindow.queue_listwidget.count()):
                        if self.mainWindow.queue_listwidget.item(i).text() == song_name:
                            self.mainWindow.queue_listwidget.takeItem(i)
                            self.mainWindow.add_track_to_json('Downloads', song_name, f'files/{song_name}.mp3')
                            break
                    break

        except Exception as exc:
            for i in range(self.mainWindow.queue_listwidget.count()):
                if self.mainWindow.queue_listwidget.item(i).text() == song_name:
                    self.mainWindow.queue_listwidget.takeItem(i)
    
    def run(self):
        for i in self.mainWindow.queue:
            song_name = i['song_name']
            url = i['url']
            img_url = i['img_url']
            song_name = song_name.replace('?', '')

            DaT = threading.Thread(target=lambda: self.download_asynchronously(url, img_url, 'files', song_name))
            DaT.start()

            # Add to statistic
            with open('extra/json/data.json', 'r', encoding='utf-8') as f:
                self.mainWindow.json_data = json.load(f)
            if song_name in self.mainWindow.json_data['Statistic']['amount_plays']:
                pass
            else:
                self.mainWindow.json_data['Statistic']['amount_plays'][song_name] = 0
            with open('extra/json/data.json', 'w', encoding='utf-8') as f:
                json.dump(self.mainWindow.json_data, f, indent=4, ensure_ascii=False)

            self.mainWindow.track_area_action_bttn.setText(self.translated_elements[10])
        self.mainWindow.is_downloading_now = False

class download_tracks_from_file_thread(QThread):
    def __init__(self, mainWindow, tracks, parent=None):
        QObject.__init__(self, parent=parent)
        self.mainWindow = mainWindow
        self.tracks = tracks
    def run(self):
        for track in self.tracks:
            founded_tracks = parser_youtube.get_urls(track)
            first_track = {list(founded_tracks.keys())[0]: list(founded_tracks.values())[0]}    

            song_name = list(first_track.keys())[0]
            url = first_track[song_name][0]
            img_url = first_track[song_name][1]

            self.mainWindow.queue_listwidget.addItem(song_name)
            self.mainWindow.queue.append({'song_name': song_name, 'url': url, 'img_url': img_url})
        self.mainWindow.download_track_thread.start()

class parse_tracks_urls_thread(QThread):
    def __init__(self, mainWindow, parent=None):
        QObject.__init__(self, parent=parent)
        self.mainWindow = mainWindow
        with open('extra/json/config.json', 'r') as f:
            self.config = json.load(f)
        with open('extra/json/data.json', 'r', encoding='utf-8') as f:
            self.json_data = json.load(f)
        try:
            self.translated_elements = self.json_data["Translated elements"][self.config["language"]]
        except KeyError:
            self.translated_elements = self.json_data["Translated elements"]["English"]
    def run(self):
        self.mainWindow.find_track_bttn.hide()
        self.mainWindow.tracks_area.clear()
        self.mainWindow.tracks_area.addItem('Wait...')
        track_name = self.mainWindow.find_track_input.text()
        self.mainWindow.urls = parser_youtube.get_urls(track_name)
        # Add to temp
        with open('extra/json/temp.json', 'r', encoding='utf-8') as f:
            temp_data = json.load(f)
        temp_data['search_result'] = self.mainWindow.urls
        temp_data['input_data'] = track_name
        with open('extra/json/temp.json', 'w', encoding='utf-8') as f:
            json.dump(temp_data, f, indent=4, ensure_ascii=False)

        # If urls found
        if self.mainWindow.urls != False:
            self.mainWindow.tracks_area.clear()
            for url in self.mainWindow.urls:
                self.mainWindow.tracks_area.addItem(url)
            if len(self.mainWindow.tracks_area) != 0:
                self.mainWindow.track_area_action_bttn.show()
            self.mainWindow.find_track_bttn.show()

class rpc():
    def __init__(self, window):
        try:
            self.CLIENT_ID = 984392136713703474
            self.connectRPC()
        except:
            self.is_connected = False
            window.logs_listwidget.addItem('Discord RPC error')

    def connectRPC(self):
        try:
            self.RPC = Presence(self.CLIENT_ID)
            self.RPC.connect()
            self.is_connected = True
            window.logs_listwidget.addItem('Connected to Discord RPC')
        except:
            self.is_connected = False

    def update(self, text:str='', state_text:str=''):
        try:
            if self.is_connected:
                self.RPC.update(
                large_image='music-notes',
                details=text,
                state=state_text)
            else:
                pass
        except:
            self.is_connected = False

class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        QtWidgets.QSystemTrayIcon.__init__(self, icon, parent)
        self.window = parent
        self.setToolTip(f'MusicPyBox')
        self.hidden_menu = QtWidgets.QMenu(parent)
        elems = ['Next track', 'Prev track', 'Play/pause', 'Settings', 'Exit']
        for i in elems:
            self.hidden_menu.addAction(i, self.menu_clicked)
        self.hidden_menu.setIcon(QtGui.QIcon('extra/imgs/music-notes.png'))
        self.hidden_menu.addSeparator()
        self.setContextMenu(self.hidden_menu)
        
    def menu_clicked(self):
        action = self.sender().text()
        match action:
            case 'Next track':
                self.window.next_track()
            case 'Prev track':
                self.window.prev_track()
            case 'Play/pause':
                self.window.pause_or_resume()
            case 'Settings':
                nt = threading.Thread(target=lambda: os.system("notepad.exe extra/json/config.json"))
                nt.start()
            case 'Exit':
                self.window.close()

    def close(self):
        self.hidden_menu.close()

class MyWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.song = ''
        self.Play_Pause = True
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.play_mode)
        self.timer.start(1000)
        
    def setupUi(self, Form):
        with open('extra/json/config.json', 'r') as f:
            self.config = json.load(f)
        with open('extra/json/data.json', 'r', encoding='utf-8') as f:
            self.json_data = json.load(f)

        try:
            self.translated_elements = self.json_data["Translated elements"][self.config["language"]]
        except KeyError:
            self.translated_elements = self.json_data["Translated elements"]["English"]
            self.logs_listwidget.addItem('KeyError')

        Form.setObjectName("Form")
        Form.setEnabled(True)
        Form.resize(1920, 1000)
        self.setWindowIcon(QtGui.QIcon('extra/imgs/music-notes.png'))
        
        self.theme = self.config['theme']
        stylesheets = {
            'Standart dark': "QWidget#Form{\n""    background-color: #1b1c1c;\n""}\n""\n""QPushButton{\n""    background-color: #b4c1d1;\n""    border-radius: 5px;\n""    font: bold 14px;\n""    height: 31px;\n""}\n""QPushButton:hover{\n""    background-color: white;\n""}\n""\n""QLineEdit{\n""    background-color: #b4c1d1;\n""    border-radius: 5px;\n""    font: bold 14px;\n""    height: 31px;\n""}\n""QLineEdit:hover{\n""    background-color: white;\n""}\n""\n""QListWidget{\n""    border-radius: 10px;\n""    background-color: #000000;\n""    color: white;\n""}""QLabel{\n""    color: white;""}\n""",
            'Standart light': "QWidget#Form{\n""    background-color: #373d3d;\n""}\n""\n""QPushButton{\n""    background-color: #b4c1d1;\n""    border-radius: 5px;\n""    font: bold 14px;\n""    height: 31px;\n""}\n""QPushButton:hover{\n""    background-color: white;\n""}\n""\n""QLineEdit{\n""    background-color: #b4c1d1;\n""    border-radius: 5px;\n""    font: bold 14px;\n""    height: 31px;\n""}\n""QLineEdit:hover{\n""    background-color: white;\n""}\n""\n""QListWidget{\n""    border-radius: 10px;\n""    background-color: #bfd6d6;\n""    color: black;\n""}""QLabel{\n""    color: white;""}\n""",
            'Monokai': "QWidget#Form{\n""    background-color: #302f25;\n""}\n""\n""QPushButton{\n""    background-color: #4d4a41;\n""    border-radius: 5px;\n""    font: bold 14px;\n    color: #c4c3b9;\n""    height: 31px;\n""}\n""QPushButton:hover{\n""    background-color: #9e9d96;\n""}\n""\n""QLineEdit{\n""    background-color: #b4c1d1;\n""    border-radius: 5px;\n""    font: bold 14px;\n""    height: 31px;\n""}\n""QLineEdit:hover{\n""    background-color: white;\n""}\n""\n""QListWidget{\n""    border-radius: 10px;\n""    background-color: #1f1e1a;\n""    color: #c4c3b9;\n""}""QLabel{\n""    color: #c4c3b9;""}""",
            'Monokai low': "QWidget#Form{\n""    background-color: #1d1e1f;\n""}\n""\n""QPushButton{\n""    background-color: #3c3d40;\n""    border-radius: 5px;\n""    font: bold 14px;\n    color: #c4c3b9;\n""    height: 31px;\n""}\n""QPushButton:hover{\n""    background-color: #9e9d96;\n""}\n""\n""QLineEdit{\n""    background-color: #3c3d40;\n""    border-radius: 5px;\n""    font: bold 14px;\n""    height: 31px;\n""}\n""QLineEdit:hover{\n""    background-color: white;\n""}\n""\n""QListWidget{\n""    border-radius: 10px;\n""    background-color: #28292b;\n""    color: #e0ded3;\n""}""QLabel{\n""    color: #c4c3b9;""}""",
            'Discord': "QWidget#Form{\n""    background-color: #1d1e1f;\n""}\n""\n""QPushButton{\n""    background-color: #505257;\n""    border-radius: 5px;\n""    font: bold 14px;\n    color: #c4c3b9;\n""    height: 31px;\n""}\n""QPushButton:hover{\n""    background-color: #404245;\n""}\n""\n""QLineEdit{\n""    background-color: #c7b8b7;\n""    border-radius: 5px;\n""    font: bold 14px;\n""    height: 31px;\n""}\n""QLineEdit:hover{\n""    background-color: white;\n""}\n""\n""QListWidget{\n""    border-radius: 10px;\n""    background-color: #323236;\n""    color: #e0ded3;\n""}""QLabel{\n""    color: #c4c3b9;""}""",
        }
        self.tracks_area_stylesheets = {
            'Standart dark': "QListWidget { font: 20px;} QListWidget::item { border: 5px solid #505451; border-radius: 5px; margin: 8px; background-color: #505451;}",
            'Standart light': "QListWidget { font: 20px;} QListWidget::item { border: 5px solid #b4c1d1; border-radius: 5px; margin: 8px; background-color: #b4c1d1;}",
            'Monokai': "QListWidget { font: 20px;} QListWidget::item { border: 5px solid #36352e; border-radius: 5px; margin: 8px; background-color: #36352e;}",
            'Monokai low': "QListWidget { font: 20px;} QListWidget::item { border: 5px solid #2c2e30; border-radius: 5px; margin: 8px; background-color: #2c2e30;}",
            'Discord': "QListWidget { font: 20px;} QListWidget::item { border: 5px solid #48484f; border-radius: 5px; margin: 8px; background-color: #48484f;}"
        }

        Form.setStyleSheet(stylesheets[self.theme])
        self.gridLayout_2 = QtWidgets.QGridLayout(Form)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.verticalLayout_9 = QtWidgets.QVBoxLayout()
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.sidebar = QtWidgets.QListWidget(Form)
        self.sidebar.setWordWrap(True)
        self.sidebar.setMaximumSize(QtCore.QSize(171, 16777215))
        self.sidebar.setSizeIncrement(QtCore.QSize(50, 50))
        font = QtGui.QFont()
        font.setFamily("Microsoft JhengHei")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.sidebar.setFont(font)
        self.sidebar.viewport().setProperty("cursor", QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.sidebar.setStyleSheet("")
        self.sidebar.setObjectName("sidebar")
        self.verticalLayout_4.addWidget(self.sidebar)
        self.playlists = QtWidgets.QListWidget(Form)
        self.playlists.setWordWrap(True)
        self.playlists.setMaximumSize(QtCore.QSize(171, 16777215))
        self.playlists.setSizeIncrement(QtCore.QSize(50, 50))
        font = QtGui.QFont()
        font.setFamily("Microsoft JhengHei")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.playlists.setFont(font)
        self.playlists.setStyleSheet("")
        self.playlists.setObjectName("playlists")
        self.verticalLayout_4.addWidget(self.playlists)
        self.delete_playlist_bttn = QtWidgets.QPushButton(Form)
        self.delete_playlist_bttn.setObjectName("delete_playlist_bttn")
        self.verticalLayout_4.addWidget(self.delete_playlist_bttn)
        self.verticalLayout_4.setStretch(0, 1)
        self.verticalLayout_4.setStretch(1, 3)
        self.horizontalLayout_4.addLayout(self.verticalLayout_4)
        self.verticalLayout_6 = QtWidgets.QVBoxLayout()
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.horizontalLayout_13 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_13.setObjectName("horizontalLayout_13")
        self.find_track_input = QtWidgets.QLineEdit(Form)
        self.find_track_input.setObjectName("find_track_input")
        self.horizontalLayout_13.addWidget(self.find_track_input)
        self.find_track_bttn = QtWidgets.QPushButton(Form)
        self.find_track_bttn.setObjectName("find_track_bttn")
        self.select_tracks_file_bttn = QtWidgets.QPushButton(Form)
        self.select_tracks_file_bttn.setObjectName("select_tracks_file_bttn")
        self.horizontalLayout_13.addWidget(self.find_track_bttn)
        self.horizontalLayout_13.addWidget(self.select_tracks_file_bttn)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_13.addItem(spacerItem)
        self.horizontalLayout_13.setStretch(0, 2)
        self.horizontalLayout_13.setStretch(1, 1)
        self.horizontalLayout_13.setStretch(2, 1)
        self.verticalLayout_6.addLayout(self.horizontalLayout_13)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout()
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.tracks_area = QtWidgets.QListWidget(Form)
        self.tracks_area.setWordWrap(True)
        self.tracks_area.setObjectName("tracks_area")
        self.tracks_area.setStyleSheet("font: 20px; ")
        self.tracks_area.setStyleSheet(self.tracks_area_stylesheets[self.theme])
        self.verticalLayout_7.addWidget(self.tracks_area)
        self.track_area_action_bttn = QtWidgets.QPushButton(Form)
        self.track_area_action_bttn.setEnabled(True)
        self.track_area_action_bttn.setObjectName("track_area_action_bttn")
        self.verticalLayout_7.addWidget(self.track_area_action_bttn)
        self.horizontalLayout.addLayout(self.verticalLayout_7)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.week_top_lbl = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.week_top_lbl.setFont(font)
        self.week_top_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.week_top_lbl.setObjectName("week_top_lbl")
        self.verticalLayout.addWidget(self.week_top_lbl)
        self.week_top_list = QtWidgets.QListWidget(Form)
        self.week_top_list.setObjectName("week_top_list")
        self.week_top_list.setStyleSheet("font: 20px;")
        self.verticalLayout.addWidget(self.week_top_list)
        self.verticalLayout_5 = QtWidgets.QVBoxLayout()
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.stat_lbl = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.stat_lbl.setFont(font)
        self.stat_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.stat_lbl.setObjectName("stat_lbl")
        self.verticalLayout_5.addWidget(self.stat_lbl)
        self.stat_list = QtWidgets.QListWidget(Form)
        self.stat_list.setObjectName("stat_list")
        self.stat_list.setStyleSheet("font: 20px;")
        self.verticalLayout_5.addWidget(self.stat_list)
        self.verticalLayout.addLayout(self.verticalLayout_5)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.verticalLayout_11 = QtWidgets.QVBoxLayout()
        self.horizontalLayout.addLayout(self.gridLayout)
        self.verticalLayout_6.addLayout(self.horizontalLayout)
        self.horizontalLayout_4.addLayout(self.verticalLayout_6)
        self.queue_listwidget = QtWidgets.QListWidget(Form)
        self.queue_listwidget.setWordWrap(True)
        self.queue_listwidget.setObjectName("queue_listwidget")
        self.queue_lbl = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.queue_lbl.setFont(font)
        self.queue_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.queue_lbl.setObjectName("queue_lbl")
        self.logs_lbl = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.logs_lbl.setFont(font)
        self.logs_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.logs_listwidget = QtWidgets.QListWidget(Form)
        self.logs_listwidget.setObjectName("queue_listwidget")
        self.logs_listwidget.setWordWrap(True)
        self.queue_layout = QtWidgets.QVBoxLayout()
        self.queue_layout.addWidget(self.queue_lbl)
        self.queue_layout.addWidget(self.queue_listwidget)
        self.queue_layout.addWidget(self.logs_lbl)
        self.queue_layout.addWidget(self.logs_listwidget)
        self.queue_layout.setStretch(1, 3)
        self.horizontalLayout_4.addLayout(self.queue_layout)
        self.horizontalLayout_4.setStretch(0, 3)
        self.horizontalLayout_4.setStretch(1, 28)
        self.horizontalLayout_4.setStretch(2, 3)
        self.verticalLayout_9.addLayout(self.horizontalLayout_4)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_9.addItem(spacerItem1)
        self.verticalLayout_8 = QtWidgets.QVBoxLayout()
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setSpacing(8)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setSpacing(90)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem2)
        self.prev_bttn = QtWidgets.QPushButton(Form)
        self.prev_bttn.setObjectName("prev_bttn")
        self.horizontalLayout_3.addWidget(self.prev_bttn)
        self.play_bttn = QtWidgets.QPushButton(Form)
        self.play_bttn.setObjectName("play_bttn")
        self.horizontalLayout_3.addWidget(self.play_bttn)
        self.next_bttn = QtWidgets.QPushButton(Form)
        self.next_bttn.setObjectName("next_bttn")
        self.horizontalLayout_3.addWidget(self.next_bttn)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem3)
        self.horizontalLayout_3.setStretch(0, 10)
        self.horizontalLayout_3.setStretch(1, 12)
        self.horizontalLayout_3.setStretch(2, 8)
        self.horizontalLayout_3.setStretch(3, 13)
        self.horizontalLayout_3.setStretch(4, 10)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSpacing(5)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.track_name_lbl = QtWidgets.QLabel(Form)
        self.track_name_lbl.setWordWrap(True)
        self.track_name_lbl.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.track_name_lbl.setStyleSheet("color: white")
        self.track_name_lbl.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.track_name_lbl.setObjectName("track_name_lbl")
        self.horizontalLayout_2.addWidget(self.track_name_lbl)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem4)
        self.current_track_time = QtWidgets.QLabel(Form)
        self.current_track_time.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.current_track_time.setStyleSheet("color: white")
        self.current_track_time.setObjectName("current_track_time")
        self.horizontalLayout_2.addWidget(self.current_track_time)
        self.track_slider = QtWidgets.QSlider(Form)
        self.track_slider.setOrientation(QtCore.Qt.Horizontal)
        self.track_slider.setObjectName("track_slider")
        self.horizontalLayout_2.addWidget(self.track_slider)
        self.all_track_time = QtWidgets.QLabel(Form)
        self.all_track_time.setStyleSheet("color: white")
        self.all_track_time.setObjectName("all_track_time")
        self.horizontalLayout_2.addWidget(self.all_track_time)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem5)
        self.verticalLayout_10 = QtWidgets.QVBoxLayout()
        self.verticalLayout_10.setObjectName("verticalLayout_10")
        self.volume_lbl = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        self.volume_lbl.setFont(font)
        self.volume_lbl.setStyleSheet("color: white;")
        self.volume_lbl.setObjectName("volume_lbl")
        self.verticalLayout_10.addWidget(self.volume_lbl)
        self.volume_slider = QtWidgets.QSlider(Form)
        self.volume_slider.setSingleStep(self.config["volume_step"])
        self.volume_slider.setOrientation(QtCore.Qt.Horizontal)
        self.volume_slider.setObjectName("volume_slider")
        self.verticalLayout_10.addWidget(self.volume_slider)
        self.horizontalLayout_2.addLayout(self.verticalLayout_10)
        self.horizontalLayout_2.setStretch(0, 4)
        self.horizontalLayout_2.setStretch(1, 1)
        self.horizontalLayout_2.setStretch(2, 2)
        self.horizontalLayout_2.setStretch(3, 30)
        self.horizontalLayout_2.setStretch(5, 5)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.verticalLayout_2.setStretch(0, 3)
        self.verticalLayout_2.setStretch(1, 3)
        self.verticalLayout_8.addLayout(self.verticalLayout_2)
        self.verticalLayout_9.addLayout(self.verticalLayout_8)
        self.verticalLayout_9.setStretch(0, 28)
        self.verticalLayout_9.setStretch(1, 1)
        self.verticalLayout_9.setStretch(2, 4)
        self.gridLayout_2.addLayout(self.verticalLayout_9, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Music PyBox"))
        self.current_track_time.setText(_translate("Form", "0:00"))
        self.all_track_time.setText(_translate("Form", "0:00"))
        __sortingEnabled = self.sidebar.isSortingEnabled()
        self.sidebar.setSortingEnabled(False)
        left_sidebar_elements = self.translated_elements[0:5]
        for elem in left_sidebar_elements:
            self.sidebar.addItem(elem)
        self.tracks_area.setIconSize(QtCore.QSize(50, 50))
        self.stat_elements = [self.week_top_lbl, self.week_top_list, self.stat_lbl, self.stat_list]
        self.track_area_elements = [self.track_area_action_bttn, self.tracks_area, self.find_track_bttn, self.select_tracks_file_bttn, self.find_track_input]
        self.sidebar.setSortingEnabled(__sortingEnabled)
        self.find_track_bttn.setText(_translate("Form", self.translated_elements[10]))
        self.select_tracks_file_bttn.setText(self.translated_elements[17])
        self.track_area_action_bttn.setText(_translate("Form", self.translated_elements[11]))
        self.delete_playlist_bttn.setText(_translate("Form", self.translated_elements[5]))
        self.next_bttn.setText(_translate("Form", ">"))
        self.prev_bttn.setText(_translate("Form", "<"))
        self.play_bttn.setText(_translate("Form", "Play"))
        self.volume_lbl.setText(_translate("Form", self.translated_elements[16]))
        self.queue_lbl.setText(self.translated_elements[15])
        self.logs_lbl.setText('Logs')
        self.week_top_lbl.setText(self.translated_elements[6])
        self.stat_lbl.setText(self.translated_elements[8])
        self.tracks_area.setSelectionMode(3)

        # Threads
        self.parse_tracks_thread = parse_tracks_urls_thread(mainWindow=self)
        self.download_track_thread = download_track_thread(mainWindow=self)
        self.get_tracks_to_lyrics_thread = get_tracks_to_lyrics_thread(mainWindow=self)
        self.get_lyrics_thread = get_lyrics_thread(mainWindow=self)

        # Init qmediaplayer
        self.player = QtMultimedia.QMediaPlayer()

        # Connectin gui elements
        self.play_bttn.clicked.connect(lambda: self.pause_or_resume())
        self.find_track_bttn.clicked.connect(lambda: self.find_tracks_to_lyrics())
        self.select_tracks_file_bttn.clicked.connect(lambda: self.open_tracks_file_Dialog())
        self.track_area_action_bttn.clicked.connect(lambda: self.select_action())
        self.playlists.clicked.connect(lambda: self.load_playlist())
        self.playlists.itemDoubleClicked.connect(lambda: self.add_track_to_playlist())
        self.delete_playlist_bttn.clicked.connect(lambda: self.delete_playlist())
        self.tracks_area.itemClicked.connect(lambda: self.set_temp_track())
        self.tracks_area.itemDoubleClicked.connect(lambda: self.select_track())
        self.sidebar.clicked.connect(lambda: self.left_sidebar_action())
        self.next_bttn.clicked.connect(lambda: self.next_track())
        self.prev_bttn.clicked.connect(lambda: self.prev_track())
        self.player.mediaStatusChanged.connect(lambda: self.media_status_changed())
        self.player.durationChanged.connect(lambda: self.player_duration_changed())
        self.tracks_area.itemSelectionChanged.connect(lambda: self.set_temp_tracks())
        self.player.stateChanged.connect(self.playerState)
        self.track_slider.sliderReleased.connect(self.track_slider_released)
        self.volume_slider.valueChanged.connect(self.volume_slider_released)

        self.hide_elements(self.stat_elements)
        self.hide_elements([self.tracks_area, self.find_track_input, self.find_track_bttn, self.select_tracks_file_bttn, self.track_area_action_bttn])

        # Vars
        with open('extra/json/temp.json', 'r', encoding='utf-8') as f:
            self.urls = json.load(f)['search_result']
        with open('extra/json/data.json', 'r', encoding='utf-8') as f:
            self.json_data = json.load(f)
        self.current_track = ''
        self.action = 'playlist'
        self.selected_playlist = ''
        self.tracks_to_lyrics = {}
        self.queue = []
        self.Play_Pause = True
        self.first_play = True
        self.is_downloading_now = False
        try:
            self.current_track = self.json_data['Player']['last_track'][0]
        except:
            pass
        try:
            self.current_track_name = self.json_data['Player']['last_track'][1]
        except:
            pass
        try:
            self.current_track_playlist = self.json_data['Player']['last_playlist']
        except:
            pass
        self.next_week = (datetime.now() + timedelta(7)).strftime('%d.%m.%y')
        if self.json_data['Date']['next_week_date'] == '0':
            with open('extra/json/data.json', 'w') as f:
                self.json_data['Date']['next_week_date'] = self.next_week
                f.write(self.next_week)
        else:
            self.old_next_week = datetime.strptime(self.json_data['Date']['next_week_date'], '%d.%m.%y')
            if self.old_next_week < datetime.now():
                with open('extra/json/data.json', 'w', encoding='utf-8') as f:
                    self.json_data['Statistic']['amount_plays'] = {}
                    self.json_data['Date']['next_week_date'] = self.next_week
                    json.dump(self.json_data, f, ensure_ascii=False, indent=4)
        try:
            self.translated_elements = self.json_data["Translated elements"][self.config["language"]]
        except KeyError:
            self.translated_elements = self.json_data["Translated elements"]["English"]
            self.logs_listwidget.addItem('KeyError')

        # Get local ip
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.host_name = s.getsockname()[0]
        s.close()
        self.server  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host_name, 7777))

        # Track file exist?
        if not os.path.exists(self.current_track):
            self.current_track = ''
            self.current_track_name = ''
            self.current_track_playlist = ''
        
        # Set some text
        self.track_name_lbl.setText(self.current_track_name)
        self.playlists_data = os.listdir('files')
        for track in self.playlists_data:
            self.tracks_area.addItem('files/' + track)
            self.json_data['Playlists']['Local'].append('files/' + track)
            if track.split('.mp3')[-1] == '':
                if track.replace('.mp3', '') not in self.json_data['Statistic']['amount_plays']:
                    self.json_data['Statistic']['amount_plays'][track.replace('.mp3', '')] = 0
        with open('extra/json/data.json', 'w', encoding='utf-8') as f:
            json.dump(self.data_without_local_playlist(), f, ensure_ascii=False, indent=4)
        self.json_playlists = list(self.json_data['Playlists'])
        for playlist in self.json_playlists:
            self.playlists.addItem(playlist)

        try:
            self.player.setVolume(self.json_data['Player']['volume'])
            self.volume_slider.setValue(self.json_data['Player']['volume'])
            self.track_time_data = self.return_human_time_from_track_pyglet(self.current_track)
            self.track_time = self.track_time_data[0]
            self.all_track_time.setText(self.track_time_data[1])

            # Load player data from data file
            self.track_slider.setMinimum(0)
            self.track_slider.setMaximum(int(self.track_time))
            self.track_slider.setValue(self.json_data['Player']['track_duration'])
            self.player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl(self.current_track)))
            self.player.setPosition(self.track_slider.value())
            self.current_track_time.setText(time.strftime("%M:%S", time.gmtime(self.json_data['Player']['track_duration'] / 1000)))
            self.track_slider_released()
            rpc_client.update(f'{self.current_track_playlist}|{self.current_track_name}', '00:00')

        except:
            self.logs_listwidget.addItem('Load data error')


    """PLAYER CONTROL"""
    def next_playlist(self):
        items = [self.playlists.item(x).text() for x in range(self.playlists.count())]
        for i in range(len(items)):
            if items[i] == self.current_track_playlist:
                try:
                    next_playlist = items[i + 1]
                except IndexError:
                    next_playlist = items[0]
                    self.logs_listwidget.addItem('IndexError')
        self.current_track_playlist = next_playlist
        if type(self.json_data['Playlists'][self.current_track_playlist]) == list:
            self.current_track_name = self.json_data['Playlists'][self.current_track_playlist][0]
            self.current_track = self.json_data['Playlists'][self.current_track_playlist][0]
            self.pause_or_resume_w_args()
        elif type(self.json_data['Playlists'][self.current_track_playlist]) == dict:
            self.current_track_name = list(self.json_data['Playlists'][self.current_track_playlist].keys())[0]
            self.current_track = self.json_data['Playlists'][self.current_track_playlist][self.current_track_name]
            self.pause_or_resume_w_args()
            
    def prev_playlist(self):
        items = [self.playlists.item(x).text() for x in range(self.playlists.count())]
        for i in range(len(items)):
            if items[i] == self.current_track_playlist:
                try:
                    next_playlist = items[i - 1]
                except IndexError:
                    next_playlist = items[-1]
                    self.logs_listwidget.addItem('IndexError')
        self.current_track_playlist = next_playlist
        if type(self.json_data['Playlists'][self.current_track_playlist]) == list:
            self.current_track_name = self.json_data['Playlists'][self.current_track_playlist][0]
            self.current_track = self.json_data['Playlists'][self.current_track_playlist][0]
            self.pause_or_resume_w_args()
        elif type(self.json_data['Playlists'][self.current_track_playlist]) == dict:
            self.current_track_name = list(self.json_data['Playlists'][self.current_track_playlist].keys())[0]
            self.current_track = self.json_data['Playlists'][self.current_track_playlist][self.current_track_name]
            self.pause_or_resume_w_args()

    def next_track(self):
        if self.current_track_playlist == 'Local':
            try:
                self.json_data['Playlists']['Local'] = []
                self.playlists_data = os.listdir('files')
                for track in self.playlists_data:
                    self.json_data['Playlists']['Local'].append('files/' + track)
                self.current_track = self.json_data['Playlists'][self.current_track_playlist][self.json_data['Playlists'][self.current_track_playlist].index(self.current_track_name) + 1]
                self.current_track_name = self.current_track
                self.pause_or_resume_w_args()
            # If last track in playlist - select first track
            except IndexError:
                self.logs_listwidget.addItem('IndexError')
                self.current_track = self.json_data['Playlists'][self.current_track_playlist][0]
                self.current_track_name = self.current_track
                self.pause_or_resume_w_args()
        else:
            try:
                self.playlist_tracks_values = list(self.json_data['Playlists'][self.current_track_playlist].values())
                self.current_track = self.playlist_tracks_values[self.playlist_tracks_values.index(self.current_track) + 1]
                for k, v in self.json_data['Playlists'][self.current_track_playlist].items():
                    if v == self.current_track:
                        self.current_track_name = k
                        break
                self.pause_or_resume_w_args()
            # If last track in playlist - select first track
            except IndexError:
                self.logs_listwidget.addItem('IndexError')
                self.playlist_tracks_values = list(self.json_data['Playlists'][self.current_track_playlist].values())
                self.current_track = self.playlist_tracks_values[0]
                for k, v in self.json_data['Playlists'][self.current_track_playlist].items():
                    if v == self.current_track:
                        self.current_track_name = k
                        break
                self.pause_or_resume_w_args()
            except KeyError as ke:
                self.logs_listwidget.addItem('KeyError')

    def prev_track(self):
        if self.current_track != '':
            if self.current_track_playlist == 'Local':
                try:
                    self.json_data['Playlists']['Local'] = []
                    self.playlists_data = os.listdir('files')
                    for track in self.playlists_data:
                        self.json_data['Playlists']['Local'].append('files/' + track)
                    self.current_track = self.json_data['Playlists'][self.current_track_playlist][self.json_data['Playlists'][self.current_track_playlist].index(self.current_track_name) -1]
                    self.current_track_name = self.current_track
                    self.pause_or_resume_w_args()
                # If first track in playlist - select last track
                except IndexError:
                    self.logs_listwidget.addItem('IndexError')
                    self.current_track = self.json_data['Playlists'][self.current_track_playlist][-1]
                    self.current_track_name = self.current_track
                    self.pause_or_resume_w_args()
            else:
                try:
                    self.playlist_tracks_values = list(self.json_data['Playlists'][self.current_track_playlist].values())
                    self.current_track = self.playlist_tracks_values[self.playlist_tracks_values.index(self.current_track) - 1]
                    for k, v in self.json_data['Playlists'][self.current_track_playlist].items():
                        if v == self.current_track:
                            self.current_track_name = k
                            break
                    self.pause_or_resume_w_args()
                # If first track in playlist - select last track
                except IndexError:
                    self.logs_listwidget.addItem('IndexError')
                    self.playlist_tracks_values = list(self.json_data['Playlists'][self.current_track_playlist].values())
                    self.current_track = self.playlist_tracks_values[-1]
                    for k, v in self.json_data['Playlists'][self.current_track_playlist].items():
                        if v == self.current_track:
                            self.current_track_name = k
                            break
                    self.pause_or_resume_w_args()
                except KeyError as ke:
                    self.logs_listwidget.addItem('KeyError')

    def play(self, song):
        self.play_bttn.setText('Pause')
        if self.player.isAudioAvailable() == False:
            self.player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl(song)))
            self.song = song
        if self.song == song:
            pass
        else:
            self.player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl(song)))
            self.song = song

        self.player.play()
        self.Play_Pause = False

    def pause(self):
        self.play_bttn.setText('Play')
        self.player.pause()
        self.Play_Pause = True

    def pause_or_resume(self):
        if self.current_track != '': # If track selected
            self.track_name_lbl.setText(self.current_track_name)
            if self.first_play:
                # Change statistic
                temp_track_name = self.current_track_name.split('/')
                if temp_track_name[0] == 'files':
                    if temp_track_name[1].split('.mp3')[-1] == '':
                        temp_track_name = temp_track_name[1]
                        temp_track_name = temp_track_name[:-4]
                    else:
                        temp_track_name = temp_track_name[1]
                else:
                    temp_track_name = self.current_track_name
                if temp_track_name in self.json_data['Statistic']['amount_plays']:
                    self.json_data['Statistic']['amount_plays'][temp_track_name] += 1
                    with open('extra/json/data.json', 'w', encoding='utf-8') as f:
                        json.dump(self.json_data, f, indent=4, ensure_ascii=False)
                else:
                    self.json_data['Statistic']['amount_plays'][temp_track_name] = 1
                    with open('extra/json/data.json', 'w', encoding='utf-8') as f:
                        json.dump(self.json_data, f, indent=4, ensure_ascii=False)

                self.first_play = False
                self.play(self.current_track)
            else:
                if self.Play_Pause == False:
                    self.pause()
                else:
                    self.play(self.current_track)

    def add_track_to_playlist(self):
        self.playlist_to_add = self.playlists.currentItem().text()
        if self.playlist_to_add != 'Local':
            if self.temp_playlist != 'Local':
                for temp_track in self.temp_tracks:
                    self.json_data['Playlists'][self.playlist_to_add][temp_track] = self.json_data['Playlists'][self.temp_playlist][temp_track]
            elif self.temp_playlist == 'Local':
                for temp_track in self.temp_tracks:
                    self.json_data['Playlists'][self.playlist_to_add][temp_track] = temp_track
        with open('extra/json/data.json', 'w', encoding='utf-8') as f:
            json.dump(self.data_without_local_playlist(), f, indent=4, ensure_ascii=False)
        self.load_playlist()
    
    def delete_track_form_playlist(self):
        self.prev_current_track = self.current_track
        self.deleted_elements = self.tracks_area.selectedItems()
        self.current_playlist = self.playlists.currentItem().text()
        try:
            self.deleted_elements_text = []
            for i in self.tracks_area.selectedItems():
                self.deleted_elements_text.append(i.text())
        except AttributeError:
            self.logs_listwidget.addItem('AttributeError')
            return 0

        #for k in self.deleted_elements:
        if self.current_playlist == 'Local':
            for i in self.find_track_in_playlists(self.deleted_elements_text):
                for j in self.deleted_elements_text:
                    self.json_data['Playlists'][i] = {key:val for key, val in self.json_data['Playlists'][i].items() if val != j}
            self.json_data['Playlists']['Local'] = []
            # Adding all tracks from /files to json data
            for i in os.listdir('files'):
                self.json_data['Playlists']['Local'].append('files/' + i)
            # Removing file
            try:
                for i in self.deleted_elements_text:
                    pass
                    os.remove(self.json_data['Playlists']['Local'][self.json_data['Playlists']['Local'].index(i)])
                    os.remove('extra/' + self.json_data['Playlists'][self.current_playlist][self.json_data['Playlists'][self.current_playlist].index(i)][:-4] + '.jpg')   #self.deleted_element_text
            except FileNotFoundError:
                self.logs_listwidget.addItem('FileNotFoundError')

        try:
            for r in range(len(self.deleted_elements_text)):
                k = self.deleted_elements[r]
                i = self.deleted_elements_text[r]
                if type(self.json_data['Playlists'][self.current_playlist]) == dict:
                    json_data_playlist_keys = list(self.json_data['Playlists'][self.current_playlist].keys())
                    json_data_playlist_values = list(self.json_data['Playlists'][self.current_playlist].values())
                    
                    if i == self.current_track_name:
                        for i in range(len(json_data_playlist_values)):
                            if json_data_playlist_values[i] == self.json_data['Playlists'][self.current_playlist][i]:
                                if i == len(json_data_playlist_values) - 1:
                                    find_next_track = json_data_playlist_keys[i - 1]
                                    self.current_track = self.json_data['Playlists'][self.current_playlist][find_next_track]
                                    self.current_track_name = find_next_track
                                    break
                                else:
                                    find_next_track = json_data_playlist_keys[i + 1]
                                    self.current_track = self.json_data['Playlists'][self.current_playlist][find_next_track]
                                    self.current_track_name = find_next_track
                                    break
                    del self.json_data['Playlists'][self.current_playlist][i]

                elif type(self.json_data['Playlists'][self.current_playlist]) == list:
                    if i == self.current_track_name:
                        self.current_track_name = self.json_data['Playlists'][self.current_playlist][self.json_data['Playlists'][self.current_playlist].index(i) + 1]
                        self.current_track = self.current_track_name
                    del self.json_data['Playlists'][self.current_playlist][self.json_data['Playlists'][self.current_playlist].index(i)]

                self.tracks_area.takeItem(self.tracks_area.row(k))
                with open('extra/json/data.json', 'w', encoding='utf-8') as f:
                    json.dump(self.data_without_local_playlist(), f, indent=4, ensure_ascii=False)
                self.track_name_lbl.setText(self.current_track_name)
        except (IndexError, KeyError):
            self.tracks_area.takeItem(self.tracks_area.row(k))
            with open('extra/json/data.json', 'w', encoding='utf-8') as f:
                json.dump(self.data_without_local_playlist(), f, indent=4, ensure_ascii=False)
            self.track_name_lbl.setText(self.current_track_name)
            self.logs_listwidget.addItem('IndexError, KeyError')
    
    def create_playlist(self):
        self.new_playlist_name = self.find_track_input.text()
        self.forbidden_names = ['', 'Local', 'Downloads']
        if self.new_playlist_name not in self.forbidden_names and len(self.new_playlist_name.replace(' ', '')):
            with open('extra/json/data.json', 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
            self.json_data['Playlists'][self.new_playlist_name] = {}
            with open('extra/json/data.json', 'w', encoding='utf-8') as f:
                json.dump(self.data_without_local_playlist(), f, indent=4, ensure_ascii=False)
            self.playlists.addItem(self.new_playlist_name)

    def delete_playlist(self):
        self.removed_playlist = self.playlists.currentItem()
        if self.removed_playlist.text() != 'Downloads' and self.removed_playlist.text() != 'Local':
            with open('extra/json/data.json', 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
            del self.json_data['Playlists'][self.removed_playlist.text()]
            self.playlists.takeItem(self.playlists.row(self.removed_playlist))
            with open('extra/json/data.json', 'w', encoding='utf-8') as f:
                json.dump(self.data_without_local_playlist(), f, indent=4, ensure_ascii=False)
            self.tracks_area.clear()

    def add_track_to_json(self, playlist_name, track_name, track_path):
        with open('extra/json/data.json', 'r', encoding='utf-8') as f:
            self.json_data = json.load(f)
        self.json_data['Playlists'][playlist_name][track_name] = track_path
        with open('extra/json/data.json', 'w', encoding='utf-8') as f:
            json.dump(self.data_without_local_playlist(), f, indent=4, ensure_ascii=False)

    def add_playlist_to_json(self, playlist_name):
        with open('extra/json/data.json', 'r', encoding='utf-8') as f:
            self.json_data = json.load(f)
        self.json_data['Playlists'][playlist_name] = {}
        with open('extra/json/data.json', 'w', encoding='utf-8') as f:
            json.dump(self.data_without_local_playlist(), f, indent=4, ensure_ascii=False)

    "SETTING/CHANGING/RETURN SOMETHING DATA"
    # Return M:S from track timestamp with qmediaplayer
    def return_human_time_from_track_pyqt(self):
        try:
            ts = self.player.duration()
            return ts, time.strftime('%M:%S', time.gmtime(timedelta(milliseconds=ts).seconds))
        except Exception as exc:
            self.logs_listwidget.addItem('Error')
            return 0, '0:00'

    # Return M:S from track timestamp with pyglet
    def return_human_time_from_track_pyglet(self, track_file):
        try:
            ts = pyglet.media.load(track_file).duration
            return ts * 1000, time.strftime('%M:%S', time.gmtime(ts))
        except Exception as exc:
            self.logs_listwidget.addItem('Error')
            return 0, '0:00'

    # Returns all playlists that contain the title of the track.
    def find_track_in_playlists(self, trcks):
        playlists = []
        self.temp_data = self.data_without_local_playlist()
        self.temp_data['Playlists'].pop('Local')
        for playlist in self.temp_data['Playlists'].keys():
            for track in self.temp_data['Playlists'][playlist].values():
                if track in trcks:
                    playlists.append(playlist)
        return playlists

    def data_without_local_playlist(self):
        self.temp_data = deepcopy(self.json_data)
        self.temp_data['Playlists']['Local'] = []
        return self.temp_data
   
    def return_clear_track_name(self, track_name):
        return track_name.split('files/')[1].split('.mp3')[0]

    # Additional arguments for pause_or_resume()
    def pause_or_resume_w_args(self):
        self.Play_Pause = True
        self.first_play = True

        self.set_track_data()
        self.pause_or_resume()

        self.track_time_data = None
        self.track_time = None
        rpc_client.update(f'{self.current_track_playlist}|{self.current_track_name}', '00:00')

    # self.temp_track need to add selected track to other playlist
    def set_temp_track(self):
        self.temp_tracks = [self.tracks_area.currentItem().text()]

    # self.temp_tracks need to add selected track to other playlist
    def set_temp_tracks(self):
        if self.tracks_area.selectedItems() != []:
            self.temp_tracks = []
            for i in self.tracks_area.selectedItems():
                self.temp_tracks.append(i.text())

    def redact_text(self, text, num):
        text = list(text)
        for i in range(len(text)):
            if i % num == 0:
                for j in range(i):
                    if j >= 10:
                        text[i - j] = f'{text[i - j]}-\n'
                        break
                    elif text[i - j] == ' ':
                        text[i - j] = '\n'
                        break
        text = ''.join(text)
        return text

    def set_track_data(self):
        self.track_time_data = self.return_human_time_from_track_pyqt()
        self.track_time = self.track_time_data[0]
        self.all_track_time.setText(self.track_time_data[1])
        self.track_slider.setMaximum(int(self.track_time))
        if not self.first_play:
            self.track_slider.setValue(0)

    def open_tracks_file_Dialog(self):
        self.tracks_file_name = QFileDialog.getOpenFileName(self, "Open tracks file", "", "Text Files (*.txt)")
        self.download_tracks_from_file(self.tracks_file_name)

    # If button under track area clicked
    def select_action(self):
        if self.action == 'download':
            self.parse_track()
        elif self.action == 'playlist':
            self.delete_track_form_playlist()  

    """GUI"""
    def left_sidebar_action(self):
        current_sidebar_index = self.sidebar.indexFromItem(self.sidebar.currentItem()).row()
        # Main
        if current_sidebar_index == 0:
            self.is_waiting_connect = False
            self.hide_elements(self.track_area_elements)
            self.show_elements(self.stat_elements)
            self.week_top_list.clear()
            self.stat_list.clear()

            # Popularity of tracks foк week
            popular_tracks_temp = {}
            unsorted_popular_tracks_temp = self.json_data['Statistic']['amount_plays']
            sorted_popular_tracks_temp_keys = sorted(unsorted_popular_tracks_temp, key=unsorted_popular_tracks_temp.get, reverse=True)
            for w in sorted_popular_tracks_temp_keys:
                popular_tracks_temp[w] = unsorted_popular_tracks_temp[w]
            for i in popular_tracks_temp:
                self.week_top_list.addItem(f'{i}:\t{popular_tracks_temp[i]}')

            fso = com.Dispatch("Scripting.FileSystemObject")
            folder = fso.GetFolder('files')
            mb=1024*1024.0
            files_folder_size = "{}".format(round(folder.Size/mb, 1))
            self.stat_list.addItem(f'Размер папки /files: \t{files_folder_size} мб')

        # Search
        elif current_sidebar_index == 1:
            self.is_waiting_connect = False
            self.hide_elements(self.stat_elements)
            with open('extra/json/temp.json', 'r', encoding='utf-8') as f:
                temp_data = json.load(f)
                self.urls = temp_data['search_result']
                self.find_track_input.setText(temp_data['input_data'])
            self.tracks_area.clear()
            if self.urls != False:
                for i in self.urls:
                    self.tracks_area.addItem(i)
            self.action = 'download'
            self.show_elements([self.tracks_area, self.find_track_input, self.find_track_bttn, self.select_tracks_file_bttn, self.track_area_action_bttn])
            self.track_area_action_bttn.setText(self.translated_elements[11])

        # Lyrics
        elif current_sidebar_index == 2:
            self.is_waiting_connect = False
            self.hide_elements(self.stat_elements)
            self.hide_elements([self.select_tracks_file_bttn])
            self.show_elements([self.find_track_input, self.find_track_bttn, self.tracks_area])
            self.find_track_input.setText(self.current_track_name)
            self.tracks_area.clear()
            self.track_to_lyrics_temp = self.current_track_name
            self.action = 'lyrics'
            if self.current_track != '':
                if self.current_track_playlist == 'local' or self.track_to_lyrics_temp.split('files/')[0] == '' and self.track_to_lyrics_temp.split('files/')[1].split('.mp3')[-1] == '':
                    self.find_track_input.setText(self.return_clear_track_name(self.current_track_name))
                    self.track_to_lyrics_temp = self.return_clear_track_name(self.track_to_lyrics_temp)
            with open('extra/json/temp.json', 'r', encoding='utf-8') as f:
                temp_data = json.load(f)
            if self.track_to_lyrics_temp == temp_data['lyrics_data']['lyrics_track']:
                for i in temp_data['lyrics_data']['lyrics']:
                    self.tracks_area.addItem(i)
            else:
                self.get_tracks_to_lyrics_thread.start()

        # New playlist
        elif current_sidebar_index == 3:
            self.is_waiting_connect = False
            if self.find_track_input.isHidden():
                self.hide_elements([self.track_area_action_bttn])
                self.show_elements([self.find_track_input, self.tracks_area])
                self.tracks_area.clear()
                self.track_area_action_bttn.setText(self.translated_elements[12])
            else:
                self.create_playlist()
        
        # Connect to device
        elif current_sidebar_index == 4:
            self.tracks_area.clear()
            if self.tracks_area.isHidden():
                self.tracks_area.show()
                self.hide_elements(self.stat_elements)
                self.hide_elements([self.find_track_input, self.find_track_bttn])
            self.secret_code = random.randint(1000, 9999)
            self.track_area_action_bttn.setText(self.translated_elements[13])
            self.tracks_area.addItem(self.translated_elements[14])
            self.tracks_area.addItem(f'IP:\t{self.host_name}')
            self.tracks_area.addItem(f'PORT:\t{7777}')
            self.tracks_area.addItem(f'CODE:\t{self.secret_code}')

            self.is_waiting_connect = True
            at = threading.Thread(target=self.accept_connection)
            at.start()

    def select_track(self):
        if self.action == 'playlist':
            if self.selected_playlist == 'Local':
                if self.current_track_name != self.tracks_area.currentItem().text() and self.current_track != self.tracks_area.currentItem().text():
                    self.track_slider.setValue(0)
                    self.current_track_name = self.tracks_area.currentItem().text()
                    self.current_track = self.tracks_area.currentItem().text()
                    self.current_track_playlist = self.playlists.currentItem().text()
                    self.pause_or_resume_w_args()
            else:
                with open('extra/json/data.json', 'r', encoding='utf-8') as f:
                    self.json_data = json.load(f)

                if self.current_track_name != self.tracks_area.currentItem().text() and self.current_track != self.json_data['Playlists'][self.selected_playlist][self.tracks_area.currentItem().text()]:
                    self.track_slider.setValue(0)
                    self.current_track_name = self.tracks_area.currentItem().text()
                    self.current_track = self.json_data['Playlists'][self.selected_playlist][self.tracks_area.currentItem().text()]
                    self.current_track_playlist = self.playlists.currentItem().text()
                    self.pause_or_resume_w_args()
        elif self.action == 'lyrics':
            self.get_lyrics_thread.start()

    def load_playlist(self):
        self.temp_playlist = self.selected_playlist
        self.selected_playlist = self.playlists.currentItem().text()
        self.action = 'playlist'
        self.track_area_action_bttn.setText(self.translated_elements[12])
        self.hide_elements(self.stat_elements)
        self.hide_elements([self.find_track_input, self.find_track_bttn])
        self.show_elements([self.track_area_action_bttn, self.tracks_area])
        self.tracks_area.clear()
        if self.selected_playlist == 'Local':
            self.playlists_data = os.listdir('files')
            with open('extra/json/data.json', 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)
            for track in self.playlists_data:
                if track.split('.mp3')[-1] == '':
                    if os.path.exists('extra/files/' + track[:-4] + '.jpg'):
                        icon = QtGui.QIcon('extra/files/' + track[:-4] + '.jpg')
                    else:
                        icon = QtGui.QIcon('extra/imgs/default_pic.jpg')
                    item = QtWidgets.QListWidgetItem(icon, 'files/' + track)
                    self.tracks_area.addItem(item)
                    self.json_data['Playlists']['Local'].append('files/' + track)
        else:
            with open('extra/json/data.json', 'r', encoding='utf-8') as f:
                self.playlists_data = json.load(f)
            for track in self.playlists_data['Playlists'][self.selected_playlist]:
                if track.split('files/')[0] == '':
                    if os.path.exists('extra/files/' + track.split('files/')[1][:-4] + '.jpg'):
                        icon = QtGui.QIcon('extra/files/' + track.split('files/')[1][:-4] + '.jpg')
                    else:
                        icon = QtGui.QIcon('extra/imgs/default_pic.jpg')
                else:
                    if os.path.exists('extra/files/' + track + '.jpg'):
                        icon = QtGui.QIcon('extra/files/' + track + '.jpg')
                    else:
                        icon = QtGui.QIcon('extra/imgs/default_pic.jpg')
                item = QtWidgets.QListWidgetItem(icon, track)
                self.tracks_area.addItem(item)
    
    def hide_elements(self, elems):
        for i in elems:
            i.hide()

    def show_elements(self, elems):
        for i in elems:
            i.show()
   
    """CONNECTIONS ELEMENTS"""
    # Function for permanent track slider movement
    def play_mode(self):
        if self.Play_Pause == False:
            str_time = time.strftime("%M:%S", time.gmtime(self.track_slider.value() / 1000))
            self.current_track_time.setText(str_time)
            self.track_slider.setValue(self.track_slider.value() + 1000)
            if rpc_client.is_connected:
                rpc_client.update(f'{self.current_track_playlist}|{self.current_track_name}', str_time)
            else:
                rpc_client.connectRPC()
                rpc_client.update(f'{self.current_track_playlist}|{self.current_track_name}', str_time)

    def media_status_changed(self):
        # If track is end
        if self.player.mediaStatus() == 7:
            self.track_slider.setValue(0)
            self.next_track()

    def player_duration_changed(self):
        self.set_track_data()

    def volume_slider_released(self):
        self.player.setVolume(self.volume_slider.value())

    def track_slider_released(self):
        self.player.setPosition(self.track_slider.value())

    def playerState(self, state):
        if state == 0:
            self.Play_Pause = False
            self.track_slider.setSliderPosition(1000)

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.is_waiting_connect = False
        self.hide()
        self.player.pause()
        self.server.close()
        tray_icon.close()
        parser_youtube.quit_webdriver()
        parser_lyrics.quit_webdriver()
        with open('extra/json/data.json', 'r', encoding='utf-8') as f:
            self.json_data = json.load(f)
        try:
            self.json_data['Player']['last_track'] = [self.current_track, self.current_track_name]
        except AttributeError:
            self.json_data['Player']['last_track'] = ['', '']
        try:
            self.json_data['Player']['last_playlist'] = self.current_track_playlist
        except AttributeError:
            self.json_data['Player']['last_playlist'] = ''
        try:
            self.json_data['Player']['track_duration'] = self.player.position()
        except AttributeError:
            self.json_data['Player']['track_duration'] = 1
        try:
            self.json_data['Player']['player_slider'] = self.track_slider.sliderPosition()
        except AttributeError:
            self.json_data['Player']['player_slider'] = 1
        try:
            self.json_data['Player']['volume'] = self.volume_slider.value()
        except AttributeError:
            self.json_data['Player']['volume'] = 100
        with open('extra/json/data.json', 'w', encoding='utf-8') as f:
            json.dump(self.data_without_local_playlist(), f, indent=4, ensure_ascii=False)
    
    """OTHER"""
    # Connect external device
    def accept_connection(self):
        self.server.listen(1)
        while self.is_waiting_connect:
            user_socket, address = self.server.accept()
            break
        try:
            self.logs_listwidget.addItem('Connected')
            while self.is_waiting_connect:
                try:
                    received_data = user_socket.recv(1024).decode().split('/')
                except OSError:
                    self.logs_listwidget.addItem('OSError')
                    user_socket, address = self.server.accept()
                    received_data = user_socket.recv(1024).decode().split('/')
                    continue
                prefix = received_data[0]
                try:
                    if prefix == 'sc':
                        received_code = received_data[1]
                        if received_code != str(self.secret_code):
                            user_socket.close()
                            self.logs_listwidget.addItem('Connection reset')
                    elif prefix == 'pr':
                        self.pause_or_resume()
                    elif prefix == 'nt':
                        self.next_track()
                    elif prefix == 'pt':
                        self.prev_track()
                    elif prefix == 'np':
                        self.next_playlist()
                    elif prefix == 'pp':
                        self.prev_playlist()
                    elif prefix == 'vr':
                        self.volume_slider.setValue(int(received_data[1]))
                    elif prefix == 'ce':
                        self.logs_listwidget.addItem('Connection reset')
                        user_socket.close()
                except:
                    pass

        except ConnectionResetError:
            self.logs_listwidget.addItem('ConnectionResetError')
            user_socket.close()
    
    def find_tracks_to_lyrics(self):
        if self.action == 'lyrics':
            self.track_to_lyrics_temp = self.find_track_input.text()
            if self.track_to_lyrics_temp != '' and self.track_to_lyrics_temp.replace(' ', '') != '':
                self.get_tracks_to_lyrics_thread.stop_search = 0
                self.get_tracks_to_lyrics_thread.start()
        else:
            self.action = 'download'
            self.track_area_action_bttn.setText(self.translated_elements[11])
            self.tracks_area.show()
            self.parse_tracks_thread.start()

    def parse_track(self):
        try:
            if self.is_downloading_now:
                self.song_name = self.tracks_area.currentItem().text()
                self.url = self.urls[self.song_name][0]
                self.img_url = self.urls[self.song_name][1]
                self.queue_listwidget.addItem(self.song_name)
                self.queue.append({'song_name': self.song_name, 'url': self.url, 'img_url': self.img_url})
            else:
                self.is_downloading_now = True
                self.song_name = self.tracks_area.currentItem().text()
                self.url = self.urls[self.song_name][0]
                self.img_url = self.urls[self.song_name][1]
                self.queue_listwidget.addItem(self.song_name)
                self.queue.append({'song_name': self.song_name, 'url': self.url, 'img_url': self.img_url})
                self.download_track_thread.start()
        except Exception as exc:
            self.logs_listwidget.addItem(exc)

    def download_tracks_from_file(self, fpath):
        with open(fpath[0], 'r', encoding='utf-8') as f:
            tracks = f.read().split('\n')
        tracks = list(filter(lambda x: x != "", tracks))
        self.download_tracks_from_file_thread = download_tracks_from_file_thread(mainWindow=self, tracks=tracks)
        self.download_tracks_from_file_thread.run()

if __name__ == '__main__':
    import sys
    parser_lyrics = lyrics_parser()
    parser_youtube = music_parser()
    app = QtWidgets.QApplication(sys.argv)
    window = MyWindow()
    window.setWindowTitle('MP3-player, PyQt5')
    window.setupUi(window)
    rpc_client = rpc(window)
    tray_icon = SystemTrayIcon(QtGui.QIcon('extra/imgs/music-notes.png'), window)
    tray_icon.show()
    window.show()
    sys.exit(app.exec_())