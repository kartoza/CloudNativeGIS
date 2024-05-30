POINT = {
    "layers": [
        {
            "id": "<uuid>",
            "type": "circle",
            "paint": {
                "circle-color": "#ff7800",
                "circle-radius": 4,
                "circle-opacity": 1
            },
            "filter": ["==", "$type", "Point"],
            "source": "<uuid>",
            "source-layer": "default"
        }
    ]
}
LINE = {
    "layers": [
        {
            "id": "<uuid>",
            "type": "line",
            "source": "<uuid>",
            "source-layer": "default",
            "filter": ["==", "$type", "LineString"],
            "paint": {
                "line-color": "#ff7800",
                "line-width": 1
            },
        }
    ]
}

POLYGON = {
    "layers": [
        {
            "id": "<uuid>",
            "type": "fill",
            "source": "<uuid>",
            "source-layer": "default",
            "filter": ["==", "$type", "Polygon"],
            "paint": {
                "fill-color": "#ff7800",
                "fill-opacity": 0.8
            },
        }
    ]
}
