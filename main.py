import sys
import requests

from PyQt5 import uic
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow


def get_toponym_size(toponym):
    lower_corner, upper_corner = [[float(x) for x in value.split()]
                                  for value in toponym["boundedBy"]["Envelope"].values()]

    return [abs(upper_corner[i] - lower_corner[i]) for i in (0, 1)]


def get_toponym(geocode, **kwargs):
    geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"

    geocoder_params = {
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        "geocode": geocode,
        "format": "json"
    }
    geocoder_params.update(kwargs)

    response = requests.get(geocoder_api_server, params=geocoder_params)

    if not response:
        print("Ошибка выполнения запроса:")
        print(response.url)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        sys.exit(0)

    json_response = response.json()

    results = json_response["response"]["GeoObjectCollection"]["featureMember"]
    if not results:
        print("Ничего не найдено")
        sys.exit(0)

    toponym = results[0]["GeoObject"]

    return toponym


def get_map(**params):
    map_api_server = "http://static-maps.yandex.ru/1.x/"
    response = requests.get(map_api_server, params=params)
    return response.content


def str_to_tuple(point_str, sep=" "):
    return tuple([float(x) for x in point_str.split(sep)])


def tuple_to_str(point_tuple, sep=","):
    return sep.join(map(str, point_tuple))


class MainWidget(QMainWindow):
    def __init__(self, coordinates, scale):
        super().__init__()
        uic.loadUi('ui/main.ui', self)
        self.setWindowTitle('Yandex.Maps')

        self.coordinates = list(coordinates)
        self.scale = list(scale)

        self.update_image()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_PageUp:
            self.change_scale(-1)
        elif event.key() == Qt.Key_PageDown:
            self.change_scale(1)

    def change_scale(self, power=1):
        def check_scale(scale):
            for x in scale:
                if not 0.001 <= x <= 50:
                    return False
            return True

        coefficient = 2 ** power
        new_scale = list(map(lambda x: x * coefficient, self.scale))
        print(self.scale, new_scale)
        if not check_scale(new_scale):
            return
        self.scale = new_scale
        self.update_image()

    def update_image(self):
        img_content = get_map(
            ll=tuple_to_str(self.coordinates),
            spn=tuple_to_str(self.scale),
            l="map"
        )

        image = QImage()
        image.loadFromData(img_content)

        pixmap = QPixmap(image)
        self.image.setPixmap(pixmap)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def main():
    toponym = get_toponym(START_GEOCODE)
    pos = str_to_tuple(toponym["Point"]["pos"])
    size = get_toponym_size(toponym)

    app = QApplication(sys.argv)
    widget = MainWidget(pos, size)
    widget.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())


START_GEOCODE = "г. Белгород"
if __name__ == '__main__':
    main()
