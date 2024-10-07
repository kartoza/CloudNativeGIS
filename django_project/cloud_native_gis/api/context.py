# coding=utf-8
"""Cloud Native GIS."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cloud_native_gis.utils.geometry import (
    query_features
)
from cloud_native_gis.models.layer import Layer


class ContextAPIView(APIView):
    """
    Context API endpoint for collection queries.

    Only accessible to authenticated users.
    Validates the query, processes data, and returns results.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Handle GET requests."""
        try:
            key = request.GET.get('key', None)
            attributes = request.GET.get('attr', '')
            x = request.GET.get('x', None)
            y = request.GET.get('y', None)
            if None in [key, x, y]:
                raise KeyError('Required request argument ('
                               'registry, key, x, y) missing.')

            srid = request.GET.get('srid', 4326)

            x_list = x.split(',')
            y_list = y.split(',')

            if len(x_list) != len(y_list):
                raise ValueError(
                    'The number of x and y coordinates must be the same')

            try:
                coordinates = [
                    (float(x), float(y)) for x, y in zip(x_list, y_list)]
            except ValueError:
                raise ValueError(
                    'All x and y values must be valid floats.')

            try:
                tolerance = float(request.GET.get('tolerance', 10.0))
            except ValueError:
                raise ValueError('Tolerance should be a float')

            registry = request.GET.get('registry', '')
            if registry.lower() not in [
                'collection', 'service', 'group', 'native']:
                raise ValueError('Registry should be "collection", '
                                 '"service" or "group".')

            outformat = request.GET.get('outformat', 'geojson').lower()
            if outformat not in ['geojson', 'json']:
                raise ValueError('Output format should be either '
                                 'json or geojson')

            data = []

            if registry == 'native':
                try:
                    layer = Layer.objects.get(unique_id=key)
                    if attributes:
                        attributes = attributes.split(',')
                    else:
                        attributes = layer.attribute_names
                    data = query_features(
                        layer.query_table_name,
                        field_names=attributes,
                        coordinates=coordinates,
                        tolerance=tolerance,
                        srid=srid
                    )
                except Layer.DoesNotExist as e:
                    return Response(str(e), status=status.HTTP_404_NOT_FOUND)

            # Todo : for non native layer
            # point = parse_coord(x, y, srid)
            # data = Worker(
            #     registry, key, point, tolerance, outformat).retrieve_all()

            return Response(data, status=status.HTTP_200_OK)
        except KeyError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
