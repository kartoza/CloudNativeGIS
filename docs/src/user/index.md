---
title: User Guide
summary: Cloud Native GIS User Guide
---

# User Guide

Welcome to the Cloud Native GIS User Guide. This section provides comprehensive documentation for end users working with the platform.

## Getting Started

New to Cloud Native GIS? Start here:

- [Getting Started](getting-started.md) - Your first steps with Cloud Native GIS
- [Working with Layers](layers.md) - Understanding and managing geospatial layers
- [Styling Your Maps](styles.md) - Using Maputnik to create beautiful map styles

## Key Concepts

### Layers

Cloud Native GIS supports both **vector** and **raster** layers, served as tiles for efficient map rendering.

- **Vector Layers**: Point, line, and polygon data stored in PostGIS and served as vector tiles
- **Raster Layers**: Image data served as Cloud Optimized GeoTIFFs (COG) or PMTiles

### Styles

Map styles are stored in the database using the **Mapbox Style Specification**. This allows for:

- Consistent styling across all map views
- Version control of style changes
- Easy sharing of styles between layers

### Maputnik Integration

**Maputnik** is the built-in style editor that allows you to:

- Visually design map styles
- Preview changes in real-time
- Export styles in standard Mapbox GL format

## Quick Links

| Topic | Description |
|-------|-------------|
| [Installation](../quick_installation.md) | Quick installation guide |
| [API Reference](../api/index.md) | REST API documentation |
| [Administration](../administrator/index.md) | System administration guide |

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/CloudNativeGIS)
