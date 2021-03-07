import sys
import requests
import math

from PyQt5 import uic
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow


def lonlat_distance(a, b):
    degree_to_meters_factor = 111 * 1000
    a_lon, a_lat = a
    b_lon, b_lat = b

    radians_lattitude = math.radians((a_lat + b_lat) / 2.)
    lat_lon_factor = math.cos(radians_lattitude)

    dx = abs(a_lon - b_lon) * degree_to_meters_factor * lat_lon_factor
    dy = abs(a_lat - b_lat) * degree_to_meters_factor

    distance = math.sqrt(dx * dx + dy * dy)

    return distance


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


def search_organization(address_ll, **params):
    search_api_server = "https://search-maps.yandex.ru/v1/"

    search_params = {
        "apikey": "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3",
        "text": address_ll,
        "lang": "ru_RU",
        "ll": address_ll,
        "type": "biz"
    }
    search_params.update(params)

    response = requests.get(search_api_server, params=search_params)

    if not response:
        print("Ошибка выполнения запроса:")
        print(response.url)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        sys.exit(0)

    json_response = response.json()

    results = json_response["features"]
    if not results:
        print("Ничего не найдено")
        return
        # sys.exit(0)

    return results[0]


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
        self.zoom = 15
        self.map_label = ""

        self.result_label.setText("")

        self.move_to_object(geocode)
        self.update_image()
        self.found_toponym = None
        self.found_org = None

        self.layer_comboBox.currentIndexChanged.connect(self.update_image)
        self.search_pushButton.clicked.connect(self.search)
        self.reset_pushButton.clicked.connect(self.reset_search_results)
        self.postalcode_checkBox.stateChanged.connect(self.update_result)

    def keyPressEvent(self, event):
        zoom_keys = {
            Qt.Key_PageUp: -1,
            Qt.Key_PageDown: 1
        }
        coord_keys = {
            Qt.Key_Up: (0, 1),
            Qt.Key_Down: (0, -1),
            Qt.Key_Right: (1, 0),
            Qt.Key_Left: (-1, 0)
        }
        if event.key() in zoom_keys:
            self.change_zoom(zoom_keys[event.key()])
        if event.key() in coord_keys:
            self.move_coordinates(coord_keys[event.key()])

    def get_coords(self, mouse_event):
        img_rect = self.image.frameGeometry()
        if not img_rect.x() <= mouse_event.x() <= img_rect.x() + img_rect.width() or \
                not img_rect.y() <= mouse_event.y() <= img_rect.y() + img_rect.height():
            return

        coefficient_x, coefficient_y = 0.0000428, 0.0000428

        center_x = (img_rect.x() * 2 + img_rect.width()) // 2
        center_y = (img_rect.y() * 2 + img_rect.height()) // 2
        rel_x = mouse_event.x() - center_x
        rel_y = center_y - mouse_event.y()

        add_x = rel_x * coefficient_x * (2 ** (15 - self.zoom))
        add_y = rel_y * coefficient_y * (2 ** (15 - self.zoom)) * math.cos(math.radians(self.coordinates[1]))

        return [self.coordinates[0] + add_x, self.coordinates[1] + add_y]

    def mousePressEvent(self, event):
        coords = self.get_coords(event)
        if not coords:
            return

        if event.button() not in (1, 2):
            return

        if event.button() == 1:
            self.map_label = tuple_to_str(coords) + ",pmgns"
            self.found_toponym = get_toponym(tuple_to_str(coords))
        elif event.button() == 2:
            org = search_organization(tuple_to_str(coords), spn=tuple_to_str(self.zoom))
            org_coords = org["geometry"]["coordinates"]
            self.found_toponym = None
            if lonlat_distance(coords, org_coords) > 50:
                return
            self.found_org = org
        self.update_result()
        self.update_image()

    def move_to_object(self, geocode):
        toponym = get_toponym(geocode)
        if not toponym:
            return False
        self.coordinates = list(str_to_tuple(toponym["Point"]["pos"]))
        self.found_toponym = toponym
        return True

    def change_zoom(self, power=1):
        def check_zoom(zoom):
            return 1 <= zoom <= 15

        zoom = self.zoom + power
        if not check_zoom(zoom):
            return
        self.zoom = zoom
        self.update_image()

    def move_coordinates(self, direction):
        def check_coordinates(coords):
            limits = [170, 70]
            for i in range(len(coords)):
                if abs(coords[i]) > limits[i]:
                    return False
            return True

        coefficient = 0.002
        new_coordinates = [self.coordinates[i] + ((2 ** (15 - self.zoom)) * coefficient * direction[i])
                           for i in range(len(self.coordinates))]
        if not check_coordinates(new_coordinates):
            return False
        self.coordinates = new_coordinates
        self.update_image()

    def update_result(self):
        if self.found_toponym:
            address = self.found_toponym["metaDataProperty"]["GeocoderMetaData"]["Address"]
            postal_code = ""
            if self.postalcode_checkBox.isChecked() and "postal_code" in address:
                postal_code = address["postal_code"] + ", "
            self.result_label.setText(postal_code + address["formatted"])
        elif self.found_org:
            address = self.found_org["properties"]["CompanyMetaData"]["address"]
            self.result_label.setText(address)

    def search(self):
        text = self.search_lineEdit.text()
        if not text:
            return
        result = self.move_to_object(text)
        if result:
            self.map_label = tuple_to_str(self.coordinates) + ",pmgns"
            self.update_image()
            self.update_result()

    def reset_search_results(self):
        self.map_label = ""
        self.result_label.setText("")
        self.update_image()

    def update_image(self):
        layers = ["map", "sat", "sat,skl"]

        layer = layers[self.layer_comboBox.currentIndex()]
        img_content = get_map(
            ll=tuple_to_str(self.coordinates),
            z=self.zoom,
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
