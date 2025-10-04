# PhotoFetchr

## Description
PhotoFetchr is an innovative solution for managing, organizing and retrieving your family photos effortlessly. The application features a robust PostgreSQL database that stores photo metadata and file paths, with actual photos organized in an efficient filesystem structure. This hybrid approach combines the powerful querying capabilities of PostgreSQL with the performance benefits of filesystem storage.

The user-friendly frontend web application, powered by the Flask framework, allows users to construct complex queries visually through an intuitive interface. Users can search by people, dates, countries, and filenames to quickly find specific photos from their collection.

## Architecture

### Database Layer (PostgreSQL)
- **Metadata Storage**: Photo information, dates, countries, file paths
- **People Management**: Person identification and photo relationships
- **Advanced Queries**: Complex filtering and search capabilities

### Storage Layer (Filesystem)
- **Organized Structure**: Photos organized by year/month for performance
- **Thumbnail Cache**: Automatically generated thumbnails for fast browsing  

### Web Interface (Flask)
- **Visual Query Builder**: Intuitive interface for complex searches
- **Responsive Design**: Works on desktop and mobile devices

## Storage Structure
```text
/photos/
├── originals/
│   ├── 2023/
│   │   ├── 01/   # January photos
│   │   └── 02/   # February photos
│   └── 2024/
│       ├── 01/
│       └── 02/
└── thumbnails/
    ├── 2023/
    │   ├── 01/
    │   └── 02/
    └── 2024/
        ├── 01/
        └── 02/
```

## Original Author
Frederik Tørnstrøm ([github.com/Frederik3152](https://github.com/Frederik3152))