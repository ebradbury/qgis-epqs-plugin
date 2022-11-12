import json
import urllib

from qgis.PyQt.QtWidgets import (
    QMenu,
    QAction,
    QMessageBox
)

from qgis.core import (
    QgsApplication,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsProject
)

from qgis.gui import (
    QgsMapMouseEvent
)

EPGS_URL = 'https://nationalmap.gov/epqs/pqs.php?x={x}&y={y}&units={units}&output=json'
WGS84_CRS = QgsCoordinateReferenceSystem('EPSG:4326')

def classFactory(iface):
    return EPQSPlugin(iface)


class EPQSPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.clipboard = QgsApplication.clipboard()

    def unload(self):
        pass

    def initGui(self):
        # Stash for later
        self.canvas = self.iface.mapCanvas()

        # Connect to context menu event
        self.canvas.contextMenuAboutToShow.connect(self.populateContextMenu)

    # Called just before the context menu (right click menu) is created
    # Allows us to add our custom action
    def populateContextMenu(self, context_menu: QMenu, mouse_event: QgsMapMouseEvent):
        # Translate the map coordinate (could be any crs) to wgs84 for query params
        map_point = mouse_event.originalMapPoint()
        map_crs = self.canvas.mapSettings().destinationCrs()
        crs_transformer = QgsCoordinateTransform(map_crs, WGS84_CRS, QgsProject.instance())
        wgs84_point = crs_transformer.transform(map_point)

        # Add action to menu and connect handler
        sub_menu = context_menu.addMenu('Copy Elevation to Clipboard')

        elevation_in_feet_action = QAction('as Feet', self.iface.mainWindow())
        elevation_in_feet_action.triggered.connect(self.make_action_handler(wgs84_point, 'Feet'))

        elevation_in_meters_action = QAction('as Meters', self.iface.mainWindow())
        elevation_in_meters_action.triggered.connect(self.make_action_handler(wgs84_point, 'Meters'))

        sub_menu.addAction(elevation_in_feet_action)
        sub_menu.addAction(elevation_in_meters_action)

    # Returns a method that is the handler
    def make_action_handler(self, point, units):

        # Get elevation from USGS EPQS and copy to clipboard
        def action_handler():
            elevation = self.get_usgs_elevation(point.x(), point.y(), units)
            self.clipboard.setText(str(elevation))

        return action_handler

    # Send an HTTP request to USGS EPQS and return elevation.
    # An elevation of -1000 indicates that the coordinate was not found.
    # Returns None upon HTTP/JSON error
    def get_usgs_elevation(self, x, y, units):
        params = {'x': x, 'y': y, 'units': units}
        url = EPGS_URL.format(**params)

        # GET request
        try:
            with urllib.request.urlopen(url) as f:
                # Expecting json
                res = json.load(f)

                try:
                    # Grab elevation from json response
                    return res['USGS_Elevation_Point_Query_Service']['Elevation_Query']['Elevation']
                except KeyError:
                    return None
        except urllib.error.URLError as e:
            return None
