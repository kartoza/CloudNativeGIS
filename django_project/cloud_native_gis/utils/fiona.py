# coding=utf-8
"""Cloud Native GIS."""

import os
import zipfile
import fiona
from fiona.crs import from_epsg
from fiona.collection import Collection
from django.core.files.temp import NamedTemporaryFile
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)


# Enable KML driver support in Fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw'


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


def _open_collection(fp: str, type: str) -> Collection:
    """Open collection from file path."""
    if type == FileType.SHAPEFILE:
        file_path = f'zip://{fp}'
        result = fiona.open(file_path, encoding='utf-8')
    else:
        result = fiona.open(fp, encoding='utf-8')
    return result


def delete_tmp_shapefile(file_path: str):
    """Delete temporary shapefile."""
    if file_path.endswith('.zip'):
        cleaned_fp = file_path
        if '/vsizip/' in file_path:
            cleaned_fp = file_path.replace('/vsizip/', '')
        if os.path.exists(cleaned_fp):
            os.remove(cleaned_fp)


def _store_zip_memory_to_temp_file(file_obj: InMemoryUploadedFile):
    """Store in-memory shapefile to temporary file."""
    with NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
        for chunk in file_obj.chunks():
            temp_file.write(chunk)
        path = f'zip://{temp_file.name}'
    return path


def _read_layers_from_memory_file(fp: InMemoryUploadedFile):
    """Read layers from memory file of shapefile."""
    layers = []
    file_path = None

    try:
        with NamedTemporaryFile(
                mode='wb+', delete=False, suffix='.zip'
        ) as destination:
            file_path = destination.name
            for chunk in fp.chunks():
                destination.write(chunk)

        layers = fiona.listlayers(f'zip://{file_path}')
    except Exception:
        pass
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    return layers


def _list_layers_shapefile(fp: str):
    """Get layer list from shapefile."""
    layers = []
    try:
        if isinstance(fp, InMemoryUploadedFile):
            layers = _read_layers_from_memory_file(fp)
        elif isinstance(fp, TemporaryUploadedFile):
            layers = fiona.listlayers(
                f'zip://{fp.temporary_file_path()}'
            )
        else:
            layers = fiona.listlayers(f'zip://{fp}')
    except Exception:
        pass
    return layers


def validate_shapefile_zip(layer_file_path: any):
    """
    Validate if shapefile zip has correct necessary files.

    Note: fiona will throw exception only if dbf or shx is missing
    if there are 2 layers inside the zip, and 1 of them is invalid,
    then fiona will only return 1 layer.
    """
    layers = _list_layers_shapefile(layer_file_path)
    is_valid = len(layers) > 0
    error = []
    names = []
    with zipfile.ZipFile(layer_file_path, 'r') as zipFile:
        names = zipFile.namelist()
    shp_files = [n for n in names if n.endswith('.shp')]
    shx_files = [n for n in names if n.endswith('.shx')]
    dbf_files = [n for n in names if n.endswith('.dbf')]

    if is_valid:
        for filename in layers:
            if f'{filename}.shp' not in shp_files:
                error.append(f'{filename}.shp')
            if f'{filename}.shx' not in shx_files:
                error.append(f'{filename}.shx')
            if f'{filename}.dbf' not in dbf_files:
                error.append(f'{filename}.dbf')
    else:
        distinct_files = (
            [
                os.path.splitext(shp)[0] for shp in shp_files
            ] +
            [
                os.path.splitext(shx)[0] for shx in shx_files
            ] +
            [
                os.path.splitext(dbf)[0] for dbf in dbf_files
            ]
        )
        distinct_files = list(set(distinct_files))
        if len(distinct_files) == 0:
            error.append('No required .shp file')
        else:
            for filename in distinct_files:
                if f'{filename}.shp' not in shp_files:
                    error.append(f'{filename}.shp')
                if f'{filename}.shx' not in shx_files:
                    error.append(f'{filename}.shx')
                if f'{filename}.dbf' not in dbf_files:
                    error.append(f'{filename}.dbf')
    is_valid = is_valid and len(error) == 0
    return is_valid, error


def _get_crs_epsg(crs):
    """Get crs from crs dict."""
    return crs['init'] if 'init' in crs else None


def open_fiona_collection(file_obj, type: str) -> Collection:
    """Open file_obj using fiona.

    :param file_obj: file
    :type file_obj: file object
    :param type: file type from FileType
    :type type: str
    :return: fiona collection object
    :rtype: Collection
    """
    # if less than <2MB, it will be InMemoryUploadedFile
    if isinstance(file_obj, InMemoryUploadedFile):
        if type == FileType.SHAPEFILE:
            # fiona having issues with reading ZipMemoryFile
            # need to store to temp file
            tmp_file = _store_zip_memory_to_temp_file(file_obj)
            return fiona.open(tmp_file)
        else:
            return fiona.open(file_obj.file)
    else:
        # TemporaryUploadedFile or just string to file path
        if isinstance(file_obj, TemporaryUploadedFile):
            file_path = (
                f'zip://{file_obj.temporary_file_path()}' if
                type == FileType.SHAPEFILE else
                f'{file_obj.temporary_file_path()}'
            )
            return fiona.open(file_path)
        else:
            return _open_collection(file_obj, type)


def validate_collection_crs(collection: Collection):
    """Validate crs to be EPSG:4326."""
    epsg_mapping = from_epsg(4326)
    valid = _get_crs_epsg(collection.crs) == epsg_mapping['init']
    crs = _get_crs_epsg(collection.crs)
    return valid, crs


def list_layers(fp, type: str = None):
    """List layers from filepath."""
    layers = []
    if not type and isinstance(fp, str):
        type = FileType.guess_type(fp)

    try:
        if type == FileType.SHAPEFILE:
            layers = _list_layers_shapefile(fp)
        else:
            layers = fiona.listlayers(fp)
    except Exception as ex:
        print(f'Failed to list layers: {ex}')
    return layers
