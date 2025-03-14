# coding=utf-8
"""Cloud Native GIS."""


class FileType:
    """File types."""

    GEOJSON = 'geojson'
    SHAPEFILE = 'shapefile'
    GEOPACKAGE = 'geopackage'
    KML = 'kml'

    @staticmethod
    def guess_type(filename: str):
        """Guess file type based on filename."""
        if filename.endswith('.geojson') or filename.endswith('.json'):
            return FileType.GEOJSON
        elif filename.endswith('.zip') or filename.endswith('.shp'):
            return FileType.SHAPEFILE
        elif filename.endswith('.gpkg'):
            return FileType.GEOPACKAGE
        elif filename.endswith('.kml'):
            return FileType.KML

        return None

    @staticmethod
    def to_extension(type: str):
        """Convert FileType to file extension."""
        if type == FileType.GEOJSON:
            return '.geojson'
        elif type == FileType.SHAPEFILE:
            return '.zip'
        elif type == FileType.GEOPACKAGE:
            return '.gpkg'
        elif type == FileType.KML:
            return '.kml'
        return ''
