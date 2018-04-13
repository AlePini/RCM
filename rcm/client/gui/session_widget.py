# python import
import json
import uuid
import os.path
import collections

# pyqt5
from PyQt5.QtCore import QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QWidget, QLabel, QComboBox, \
    QGridLayout, QVBoxLayout, QLineEdit, QHBoxLayout, QPushButton, \
    QStyle, QProgressBar


# paramiko
from paramiko.ssh_exception import AuthenticationException

# local includes
from client.gui.display_dialog import QDisplayDialog
from client.gui.display_widget import QDisplayWidget
from client.utils.pyinstaller_utils import resource_path
from client.log.logger import logger
from client.log.config_parser import parser, config_file_name
from client.logic import rcm_client
from client.gui.thread import LoginThread


class QSessionWidget(QWidget):
    """
    Create a new session widget to be put inside a tab in the main window
    For each session we can have many displays
    """

    # define a signal when the user successful log in
    logged_in = pyqtSignal(str)

    sessions_changed = pyqtSignal(collections.deque)

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        self.user = ""
        self.host = ""
        self.session_name = ""
        self.displays = {}
        self.sessions_list = collections.deque(maxlen=5)
        self.platform_config = None
        self.rcm_client_connection = None
        self.is_logged = False
        self.login_thread = None

        # widgets
        self.session_combo = QComboBox(self)
        self.host_line = QLineEdit(self)
        self.user_line = QLineEdit(self)
        self.pssw_line = QLineEdit(self)

        # containers
        self.containerLoginWidget = QWidget()
        self.containerSessionWidget = QWidget()
        self.containerWaitingWidget = QWidget()

        # layouts
        self.session_ver_layout = QVBoxLayout()
        self.rows_ver_layout = QVBoxLayout()

        self.init_ui()

        self.uuid = uuid.uuid4().hex

    def init_ui(self):
        """
        Initialize the interface
        """

    # Login Layout
    # grid login layout
        grid_login_layout = QGridLayout()

        try:
            sessions_list = parser.get('LoginFields', 'hostList')
            self.sessions_list = collections.deque(json.loads(sessions_list), maxlen=5)
        except Exception:
            pass

        session_label = QLabel(self)
        session_label.setText('Sessions:')
        self.session_combo.clear()
        self.session_combo.addItems(self.sessions_list)

        self.session_combo.activated.connect(self.on_session_change)
        if self.sessions_list:
            self.session_combo.activated.emit(0)

        grid_login_layout.addWidget(session_label, 0, 0)
        grid_login_layout.addWidget(self.session_combo, 0, 1)

        host_label = QLabel(self)
        host_label.setText('Host:')

        grid_login_layout.addWidget(host_label, 1, 0)
        grid_login_layout.addWidget(self.host_line, 1, 1)

        user_label = QLabel(self)
        user_label.setText('User:')

        grid_login_layout.addWidget(user_label, 2, 0)
        pssw_label = QLabel(self)
        grid_login_layout.addWidget(self.user_line, 2, 1)

        pssw_label.setText('Password:')

        self.pssw_line.setEchoMode(QLineEdit.Password)
        grid_login_layout.addWidget(pssw_label, 3, 0)
        grid_login_layout.addWidget(self.pssw_line, 3, 1)

    # hor login layout
        pybutton = QPushButton('Login', self)
        pybutton.clicked.connect(self.login)
        pybutton.setShortcut("Return")

        login_hor_layout = QHBoxLayout()
        login_hor_layout.addStretch(1)
        login_hor_layout.addWidget(pybutton)
        login_hor_layout.addStretch(1)

    # container login widget
        # it disappears when the user logged in
        login_layout = QVBoxLayout()
        login_layout.addLayout(grid_login_layout)
        login_layout.addLayout(login_hor_layout)

        self.containerLoginWidget.setLayout(login_layout)

    # Create the main layout
        new_tab_main_layout = QVBoxLayout()
        new_tab_main_layout.addWidget(self.containerLoginWidget)

    # container waiting widget
        self.waiting_layout = QVBoxLayout()

        self.prog_dlg = QProgressBar(self)
        self.prog_dlg.setMinimum(0)
        self.prog_dlg.setMaximum(0)

        self.waiting_layout.addWidget(self.prog_dlg)
        self.containerWaitingWidget.setLayout(self.waiting_layout)

        new_tab_main_layout.addWidget(self.containerWaitingWidget)
        self.containerWaitingWidget.hide()

    # container session widget
        plusbutton_layout = QGridLayout()
        self.rows_ver_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_ver_layout.setSpacing(0)

        self.session_ver_layout.addLayout(plusbutton_layout)
        self.session_ver_layout.addLayout(self.rows_ver_layout)
        self.session_ver_layout.addStretch(1)

        font = QFont()
        font.setBold(True)

        name = QLabel()
        name.setText("Name")
        name.setFont(font)
        plusbutton_layout.addWidget(name, 0, 0)

        status = QLabel()
        status.setText("Status")
        status.setFont(font)
        plusbutton_layout.addWidget(status, 0, 1)

        time = QLabel()
        time.setText("Time")
        time.setFont(font)
        plusbutton_layout.addWidget(time, 0, 2)

        resources = QLabel()
        resources.setText("Resources")
        resources.setFont(font)
        plusbutton_layout.addWidget(resources, 0, 3)

        x = QLabel()
        x.setText("")
        plusbutton_layout.addWidget(x, 0, 4)
        plusbutton_layout.addWidget(x, 0, 5)

        new_display_ico = QIcon()
        new_display_ico.addFile(resource_path('gui/icons/plus.png'), QSize(16, 16))

        new_display_btn = QPushButton()
        new_display_btn.setIcon(new_display_ico)
        new_display_btn.setToolTip('Create a new display session')
        new_display_btn.clicked.connect(self.add_new_display)

        reload_btn = QPushButton()
        reload_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        reload_btn.setToolTip('Reload the page')
        reload_btn.clicked.connect(self.reload)

        new_display_layout = QHBoxLayout()
        new_display_layout.addSpacing(70)
        new_display_layout.addWidget(reload_btn)
        new_display_layout.addWidget(new_display_btn)

        plusbutton_layout.addLayout(new_display_layout, 0, 6)

        self.containerSessionWidget.setLayout(self.session_ver_layout)
        new_tab_main_layout.addWidget(self.containerSessionWidget)
        self.containerSessionWidget.hide()

        self.setLayout(new_tab_main_layout)

    def on_session_change(self):
        """
        Update the user and host fields when the user selects a different session in the combo
        :return:
        """
        try:
            user, host = self.session_combo.currentText().split('@')
            self.user_line.setText(user)
            self.host_line.setText(host)
        except ValueError:
            pass

    def login(self):
        self.user = str(self.user_line.text())
        self.host = str(self.host_line.text())
        password = str(self.pssw_line.text())
        self.session_name = self.user + "@" + self.host

        logger.info("Logging into " + self.session_name)

        self.rcm_client_connection = rcm_client.rcm_client_connection()
        self.rcm_client_connection.debug = False

        self.login_thread = LoginThread(self, self.host, self.user, password)
        self.login_thread.finished.connect(self.on_logged)
        self.login_thread.start()

        # Show the waiting widget
        self.containerLoginWidget.hide()
        self.containerSessionWidget.hide()
        self.containerWaitingWidget.show()

    def on_logged(self):
        if self.is_logged:
            # Show the session widget
            self.containerLoginWidget.hide()
            self.containerWaitingWidget.hide()
            self.containerSessionWidget.show()

            logger.info("Logged in " + self.session_name)

            # update sessions list
            if self.session_name in list(self.sessions_list):
                self.sessions_list.remove(self.session_name)
            self.sessions_list.appendleft(self.session_name)
            self.sessions_changed.emit(self.sessions_list)

            # update config file
            self.update_config_file(self.session_name)

            # Emit the logged_in signal.
            self.logged_in.emit(self.session_name)
        else:
            logger.error("Failed to login: invalid credentials")

    def add_new_display(self):
        # cannot have more than 5 sessions
        if len(self.displays) >= 5:
            logger.warning("You have already 5 displays")
            return

        display_win = QDisplayDialog(list(self.displays.keys()),
                                     self.platform_config)
        display_win.setModal(True)

        if display_win.exec() != 1:
            return

        display_name = display_win.display_name
        display_widget = QDisplayWidget(self, display_name)
        self.rows_ver_layout.addWidget(display_widget)
        self.displays[display_name] = display_widget
        logger.info("Added new display")

    def update_config_file(self, session_name):
        """
        Update the config file with the new session name
        :param session_name: name of the last session inserted by the user
        :return:
        """
        if not parser.has_section('LoginFields'):
            parser.add_section('LoginFields')

        parser.set('LoginFields', 'hostList', json.dumps(list(self.sessions_list)))

        try:
            config_file_dir = os.path.dirname(config_file_name)
            if not os.path.exists(config_file_dir):
                os.makedirs(config_file_dir)

            with open(config_file_name, 'w') as config_file:
                parser.write(config_file)
        except:
            logger.error("failed to dump the session list in the configuration file")

    def remove_display(self, id):
        """
        Remove the display widget from the tab
        :param id: display id name
        :return:
        """
        # first we hide the display
        logger.debug("Hiding display " + str(id))
        self.displays[id].hide()

        # then we remove it from the layout and from the dictionary
        self.rows_ver_layout.removeWidget(self.displays[id])
        self.displays[id].setParent(None)
        del self.displays[id]

        logger.info("Killed display " + str(id))

    def reload(self):
        logger.debug("Reloading...")