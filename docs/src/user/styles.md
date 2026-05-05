---
title: Styling Your Maps
summary: Creating beautiful map styles with Maputnik
---

# Styling Your Maps

Cloud Native GIS uses the **Mapbox Style Specification** for styling layers. The built-in **Maputnik** editor provides a visual interface for creating and editing styles.

## Understanding Map Styles

A map style defines how layers are rendered, including:

- **Colors**: Fill, stroke, and text colors
- **Sizes**: Line widths, symbol sizes
- **Typography**: Font families, sizes, and placement
- **Filters**: Data-driven styling rules
- **Zoom levels**: Scale-dependent rendering

## Maputnik Style Editor

### Accessing Maputnik

1. Go to **Admin > Cloud Native GIS > Layers**
2. Click on a layer
3. Click the **Editor** link in the layer detail view

### Editor Interface

```
+------------------+------------------------+
|   Layer List     |                        |
|   (Sources)      |      Map Preview       |
+------------------+                        |
|   Style Layers   |                        |
|   (Rendering)    |                        |
+------------------+------------------------+
|              Property Editor              |
+-------------------------------------------+
```

### Creating a Style

1. **Select a layer** from the sources panel
2. **Add a style layer** for the data source
3. **Configure properties**:
   - Paint properties (visual appearance)
   - Layout properties (positioning)
   - Filter expressions (data selection)
4. **Preview** your changes in real-time
5. **Save** the style

## Style Properties

### Fill Layers (Polygons)

```json
{
  "fill-color": "#3388ff",
  "fill-opacity": 0.6,
  "fill-outline-color": "#000000"
}
```

### Line Layers

```json
{
  "line-color": "#ff0000",
  "line-width": 2,
  "line-opacity": 1,
  "line-dasharray": [2, 4]
}
```

### Symbol Layers (Points/Labels)

```json
{
  "icon-image": "marker",
  "icon-size": 1.5,
  "text-field": ["get", "name"],
  "text-size": 12,
  "text-color": "#333333"
}
```

## Data-Driven Styling

Use expressions to style features based on their attributes:

### Color by Category

```json
{
  "fill-color": [
    "match",
    ["get", "type"],
    "residential", "#ffcc00",
    "commercial", "#0066ff",
    "industrial", "#ff6600",
    "#cccccc"
  ]
}
```

### Size by Value

```json
{
  "circle-radius": [
    "interpolate",
    ["linear"],
    ["get", "population"],
    0, 5,
    100000, 20,
    1000000, 40
  ]
}
```

### Zoom-Dependent Styling

```json
{
  "line-width": [
    "interpolate",
    ["linear"],
    ["zoom"],
    10, 1,
    15, 4,
    20, 8
  ]
}
```

## Managing Styles

### Style Storage

Styles are stored in the database and linked to layers. Each layer can have:

- One default style
- Multiple named style variants

### Exporting Styles

1. Open the layer in Maputnik
2. Click **Export** in the menu
3. Download as JSON

### Importing Styles

1. Open the layer in Maputnik
2. Click **Import**
3. Upload your JSON style file

## Best Practices

1. **Start simple**: Begin with basic colors, then add complexity
2. **Use zoom levels**: Adjust detail based on zoom
3. **Consider accessibility**: Use color-blind friendly palettes
4. **Test on different devices**: Ensure styles work across screens
5. **Document your styles**: Add comments and descriptions

## Resources

- [Mapbox Style Specification](https://docs.mapbox.com/mapbox-gl-js/style-spec/)
- [Maputnik Documentation](https://github.com/maputnik/editor)
- [Color Brewer](https://colorbrewer2.org/) - Cartographic color schemes

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/CloudNativeGIS)
