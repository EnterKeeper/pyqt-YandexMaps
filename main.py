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
        return None
        # sys.exit(0)

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
    def __init__(self, geocode):
        super().__init__()
        uic.loadUi('ui/main.ui', self)
        self.setWindowTitle('Yandex.Maps')

        self.coordinates = [0, 0]
        self.scale = [0.5, 0.5]
        self.map_label = ""

        self.move_to_object(geocode)
        self.update_image()

        self.layer_comboBox.currentIndexChanged.connect(self.update_image)
        self.search_pushButton.clicked.connect(self.search)
        self.reset_pushButton.clicked.connect(self.reset_search_results)

    def keyPressEvent(self, event):
        scale_keys = {
            Qt.Key_PageUp: -1,
            Qt.Key_PageDown: 1
        }
        coord_keys = {
            Qt.Key_Up: (0, 1),
            Qt.Key_Down: (0, -1),
            Qt.Key_Right: (1, 0),
            Qt.Key_Left: (-1, 0)
        }
        if event.key() in scale_keys:
            self.change_scale(scale_keys[event.key()])
        if event.key() in coord_keys:
            self.move_coordinates(coord_keys[event.key()])

    def move_to_object(self, geocode):
        toponym = get_toponym(geocode)
        if not toponym:
            return False
        self.coordinates = list(str_to_tuple(toponym["Point"]["pos"]))
        self.scale = list(get_toponym_size(toponym))
        return True

    def change_scale(self, power=1):
        def check_scale(scale):
            for x in scale:
                if not 0.001 <= x <= 50:
                    return False
            return True

        coefficient = 2 ** power
        new_scale = list(map(lambda x: x * coefficient, self.scale))
        if not check_scale(new_scale):
            return
        self.scale = new_scale
        self.update_image()

    def move_coordinates(self, direction):
        def check_coordinates(coords):
            limits = [170, 70]
            for i in range(len(coords)):
                if abs(coords[i]) > limits[i]:
                    return False
            return True

        coefficient = 0.2
        new_coordinates = [self.coordinates[i] + self.scale[i] * coefficient * direction[i]
                           for i in range(len(self.coordinates))]
        if not check_coordinates(new_coordinates):
            return False
        self.coordinates = new_coordinates
        self.update_image()

    def search(self):
        text = self.search_lineEdit.text()
        if not text:
            return
        result = self.move_to_object(text)
        if result:
            self.map_label = tuple_to_str(self.coordinates) + ",pmgns"
            self.update_image()

    def reset_search_results(self):
        self.map_label = ""
        self.update_image()

    def update_image(self):
        layers = ["map", "sat", "sat,skl"]

        layer = layers[self.layer_comboBox.currentIndex()]
        img_content = get_map(
            ll=tuple_to_str(self.coordinates),
            spn=tuple_to_str(self.scale),
            pt="~".join([self.map_label]),
            l=layer
        )

        image = QImage()
        image.loadFromData(img_content)

        pixmap = QPixmap(image)
        self.image.setPixmap(pixmap)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def main():
    app = QApplication(sys.argv)
    widget = MainWidget(START_GEOCODE)
    widget.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())


START_GEOCODE = "г. Белгород"
if __name__ == '__main__':
    main()
