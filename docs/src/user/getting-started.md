---
title: Getting Started
summary: Your first steps with Cloud Native GIS
---

# Getting Started

This guide will help you get started with Cloud Native GIS, from your first login to creating your first map layer.

## Accessing the Platform

After installation, access Cloud Native GIS through your web browser:

- **Production**: `http://your-domain.com/`
- **Development**: `http://localhost:5000/`

## Django Admin Interface

Cloud Native GIS uses Django's admin interface for layer and style management. Access it at:

```
http://your-domain.com/admin/
```

### Logging In

1. Navigate to the admin URL
2. Enter your username and password
3. Click "Log in"

!!! note
    Contact your administrator if you don't have credentials.

## Creating Your First Layer

### Step 1: Prepare Your Data

Cloud Native GIS supports various geospatial formats:

- **Shapefiles** (`.shp` with accompanying files)
- **GeoJSON** (`.geojson`, `.json`)
- **GeoPackage** (`.gpkg`)
- **KML** (`.kml`)

### Step 2: Upload the Layer

1. Go to **Cloud Native GIS > Layers** in the admin
2. Click **Add Layer**
3. Fill in the layer details:
   - **Name**: A descriptive name for your layer
   - **Description**: Optional description
   - **File**: Upload your geospatial file
4. Click **Save**

### Step 3: Configure the Layer

After upload, the layer will be processed and you can:

- View the layer attributes
- Set the default style
- Configure tile serving options

## Viewing Your Layer

Once a layer is created, you can:

1. **Preview in Admin**: Click on the layer to see a map preview
2. **Access via API**: Use the REST API to fetch layer data
3. **Embed in Applications**: Use the tile URLs in your mapping application

## Next Steps

- [Working with Layers](layers.md) - Deep dive into layer management
- [Styling Your Maps](styles.md) - Learn to style your layers
- [API Reference](../api/index.md) - Integrate with your applications

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/CloudNativeGIS)
