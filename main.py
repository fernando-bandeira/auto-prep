from PyQt5.QtWidgets import QWidget, QMainWindow, QApplication, QGridLayout
from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QTableWidgetItem
from PyQt5.QtWidgets import QHeaderView, QMessageBox
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from time import strftime, gmtime
import pyperclip
import requests
import datetime
import sys


class Worker(QObject):
    finished = pyqtSignal()

    def run(self):
        today = datetime.date.today()
        last_monday = today - datetime.timedelta(days=today.weekday(), weeks=1)
        last_friday = last_monday + datetime.timedelta(days=4)

        last_monday = last_monday.strftime('%Y-%m-%d')
        last_friday = last_friday.strftime('%Y-%m-%d')

        api_key = ''  # API key goes here
        workspace_id = ''  # It's important you inform the ID of the workspace, otherwise it won't work

        response = requests.get(
            f'https://api.clockify.me/api/v1/workspaces/{workspace_id}/users',
            headers={'X-Api-Key': api_key}
        )
        users = [(m['id'], m['name']) for m in response.json()]

        users_data = []

        for user in users:
            request_payload = {
                'dateRangeStart': f'{last_monday}T00:00:00.000Z',
                'dateRangeEnd': f'{last_friday}T23:59:59.999Z',
                'users': {
                    'ids': [user[0]],
                    'contains': 'CONTAINS',
                    'status': 'ALL'
                },
                'clients': {
                    'ids': ['5ca4d7f41080ec1cfa219a12'],
                    'contains': 'DOES_NOT_CONTAIN',
                    'status': 'ALL'
                },
                'detailedFilter': {
                    'sortColumn': 'DATE',
                    'page': 1,
                    'pageSize': 200,
                    'auditFilter': None,
                    'quickbooksSelectType': 'ALL'
                }
            }
            url = (
                'https://reports.api.clockify.me/v1/'
                f'workspaces/{workspace_id}/reports/detailed'
            )
            response = requests.post(
                url,
                headers={'X-Api-Key': api_key},
                json=request_payload)
            data = response.json()['totals'][0]
            if data:
                user_data = {
                    'Membro': user[1],
                    'Horas': strftime('%H', gmtime(data['totalTime'])),
                    'Minutos': strftime('%M', gmtime(data['totalTime']))
                }
                users_data.append(user_data)
        app.update_table(users_data)
        app.finish()
        self.finished.emit()


class App(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('AutoPREP')
        self.setMinimumSize(430, 500)

        self.cw = QWidget()
        self.grid = QGridLayout(self.cw)

        self.txt = QLabel('Click to extract data from Clockify')

        self.scrape_btn = QPushButton('Extract')
        self.scrape_btn.clicked.connect(self.scrape)

        self.table = QTableWidget()
        self.table.setRowCount(1)
        self.table.setColumnCount(3)
        self.table.setItem(0, 0, QTableWidgetItem('Member'))
        self.table.setItem(0, 1, QTableWidgetItem('Hours'))
        self.table.setItem(0, 2, QTableWidgetItem('Minutes'))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.copy_btn = QPushButton('Copy data')
        self.copy_btn.clicked.connect(self.copy_data)
        self.copy_btn.setDisabled(True)

        self.grid.addWidget(self.txt, 0, 0, 1, 1)
        self.grid.addWidget(self.scrape_btn, 1, 0, 1, 1)
        self.grid.addWidget(self.table, 2, 0, 1, 1)
        self.grid.addWidget(self.copy_btn, 3, 0, 1, 1)

        self.setCentralWidget(self.cw)

    def scrape(self):
        self.scrape_btn.setDisabled(True)
        self.txt.setText('Obtaining data...')
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def update_table(self, data):
        self.table.setRowCount(len(data) + 1)
        for i, d in enumerate(data):
            self.table.setItem(i + 1, 0, QTableWidgetItem(d['Member']))
            self.table.setItem(i + 1, 1, QTableWidgetItem(d['Hours']))
            self.table.setItem(i + 1, 2, QTableWidgetItem(d['Minutes']))

    def finish(self):
        self.scrape_btn.setDisabled(False)
        self.copy_btn.setDisabled(False)
        self.txt.setText('Dados obtidos.')

    def copy_data(self):
        self.table.selectAll()
        table_data = [item.text() for item in self.table.selectedItems()]
        interval = range((len(table_data) + 3 - 1) // 3)
        rows = ['\t'.join(table_data[i * 3:(i + 1) * 3]) for i in interval]
        items = '\n'.join(rows)
        pyperclip.copy(items)
        QMessageBox.about(self, 'Success', 'Copied!')


if __name__ == '__main__':
    qt = QApplication(sys.argv)
    app = App()
    app.show()
    qt.exec_()
