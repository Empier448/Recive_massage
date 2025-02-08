import sys
import socket
import re
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QCheckBox, QHBoxLayout, QLCDNumber, QLineEdit, QSizePolicy
from PyQt5.QtCore import QTimer, QObject, pyqtSignal as Signal, Qt

# กำหนดค่าต่าง ๆ
nInputs, nDist, nOut, nStates = 3, 5, 5, 6
nExtras = 3
inputs = np.zeros([nInputs + nExtras, 1])
outputs = np.zeros([nOut + nExtras, 1])
states = np.zeros([nStates + nExtras, 1])
disturbances = np.zeros([nDist + nExtras, 1])

#host = "127.0.0.1"
host = "192.168.0.108"
port = 65432  
#url = ""   #/////////////////
reqTimeout = 0.3  # seconds
timerInterval = 5000  # milliseconds (0.5 วินาที)

def decodeInputData(data):
    try:
        # ใช้ regex เพื่อดึงค่าหมายเลขจากข้อความ
        values = re.findall(r'\d+\.?\d*', data)  # เปลี่ยน regex ให้รองรับจุดทศนิยม
        x = np.array([float(value) for value in values])
        return x.reshape(-1, 1)
    except Exception as e:
        print(f"Error decoding data: {e}")
        return np.zeros((0, 1))

class Communicate(QObject):
    inputValueChanged = Signal(float)

class InputWidget(QWidget):
    def __init__(self, linha1: str, linha2: str, inicial: float):
        self.c = Communicate()
        super().__init__()
        vBox = QVBoxLayout(self)
        lb1 = QLabel(linha1)
        lb1.setAlignment(Qt.AlignHCenter)
        vBox.addWidget(lb1)
        self.inpTxt = QLineEdit(str(inicial))
        self.inpTxt.returnPressed.connect(self.updateInput)
        self.inpTxt.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.inpTxt.setMinimumWidth(50)
        if linha2 != "":
            lb2 = QLabel(linha2)
            lb2.setAlignment(Qt.AlignHCenter)
            vBox.addWidget(lb2)
        vBox.addWidget(self.inpTxt)
        vBox.setAlignment(Qt.AlignLeft)

    def updateInput(self):
        x = float(self.inpTxt.text())
        self.c.inputValueChanged.emit(x)

class OutputWidget(QWidget):
    def __init__(self, line1: str, line2: str, valor: float):
        super().__init__()
        vBox = QVBoxLayout(self)
        lb1 = QLabel(line1)
        lb1.setAlignment(Qt.AlignCenter)
        self.out = QLCDNumber()
        self.out.setDigitCount(7)
        self.out.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.out.setMinimumSize(90, 60)
        self.out.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.out.display(valor)
        self.out.setStyleSheet("QLCDNumber { background-color: white; color: red; }")
        vBox.addWidget(lb1)
        if line2 != '':
            lb2 = QLabel(line2)
            lb2.setAlignment(Qt.AlignCenter)
            vBox.addWidget(lb2)
        vBox.addWidget(self.out)
        vBox.setAlignment(Qt.AlignTop | Qt.AlignLeft)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.onTimer)
        self.initUI()
        self.connected = False

    def initUI(self):
        self.lbConnected = QLabel("Disconnected")
        self.lbConnected.setAlignment(Qt.AlignCenter)
        self.btnConnect = QPushButton("Connect")
        self.btnConnect.clicked.connect(self.toggleConnection)

        self.outPotNucleo = OutputWidget('Potência Nucleo', 'kW', 0)
        self.outPresPR = OutputWidget('Pressão PR', 'bar', 0)
        self.outPotSG = OutputWidget('Potência SG', 'MW', 0)

        self.cb_p_PR = QCheckBox('Pressure in Pressurizer')
        self.cb_m_SG = QCheckBox('Liquid Flow Rate in Steam Generator')
        self.cb_W_SG = QCheckBox('Power in Steam Generator')

        self.cb_p_PR.stateChanged.connect(self.chart_p_PR)
        self.cb_m_SG.stateChanged.connect(self.chart_m_SG)
        self.cb_W_SG.stateChanged.connect(self.chart_W_SG)

        hbox = QHBoxLayout()
        hbox.addWidget(self.lbConnected)
        hbox.addWidget(self.btnConnect)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(hbox)
        mainLayout.addWidget(self.outPotNucleo)
        mainLayout.addWidget(self.outPresPR)
        mainLayout.addWidget(self.outPotSG)
        mainLayout.addWidget(self.cb_p_PR)
        mainLayout.addWidget(self.cb_m_SG)
        mainLayout.addWidget(self.cb_W_SG)
        self.setLayout(mainLayout)

    def toggleConnection(self):
        if self.connected:
            self.connected = False
            self.lbConnected.setText("Disconnected")
            self.btnConnect.setText("Connect")
            self.timer.stop()
            if hasattr(self, 'sock') and self.sock:
                self.sock.close()
        else:
            self.connected = True
            self.lbConnected.setText("Connected")
            self.btnConnect.setText("Disconnect")
            self.timer.start(timerInterval)
            self.connectToServer()
     
    def connectToServer(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(reqTimeout)
            self.sock.connect((host, port))
        except socket.error as e:
            print(f"Socket connection error: {e}")
            self.connected = False
            self.lbConnected.setText("Disconnected")
            self.btnConnect.setText("Connect")
            self.timer.stop()

    def onTimer(self):
        if self.connected and self.sock:
            try:
                data = self.sock.recv(1024).decode()
                if data:
                    print(f"Received data: {data}")  # Debugging line
                    values = decodeInputData(data)
                    print(f"Decoded values: {values}")  # Debugging line
                    if values.size >= 3:
                        self.outPotNucleo.out.display(values[0, 0])
                        self.outPresPR.out.display(values[1, 0])
                        self.outPotSG.out.display(values[2, 0])
                else:
                    print("No data received, possibly client disconnected.")
                    self.toggleConnection()  # Reconnect or disconnect
            except socket.timeout:
                print("Socket timeout occurred")
            except socket.error as e:
                print(f"Socket error: {e}")
                self.toggleConnection()  # Reconnect or disconnect
            except Exception as e:
                print(f"Unexpected error: {e}")

    def chart_p_PR(self, state):
        if state == Qt.Checked:
            print("Pressure in Pressurizer chart enabled")
        else:
            print("Pressure in Pressurizer chart disabled")

    def chart_m_SG(self, state):
        if state == Qt.Checked:
            print("Liquid Flow Rate in Steam Generator chart enabled")
        else:
            print("Liquid Flow Rate in Steam Generator chart disabled")

    def chart_W_SG(self, state):
        if state == Qt.Checked:
            print("Power in Steam Generator chart enabled")
        else:
            print("Power in Steam Generator chart disabled")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())
