# PhotoFetchr

## Description
PhotoFetchr introduces an innovative solution for managing, organizing and retrieving your family photos effortlessly. The core of the application is a robust PostgreSQL database where each photo is stored as a bytea and intricately related with distinct metadata within separate tables, facilitating retrieval through user queries. Complementing this backend architecture is a user-friendly front end web application, powered by the Flask framework. This interface allows users to construct queries visually, which are then sent to the database. The database promptly responds with the requested photos, streamlining the user experience. Currently, this proof of concept hosts more than 5500 photos of varying quality, which still remains highly responsive and efficient, even on a Raspberry Pi 4B.

## Original Author
Frederik Tørnstrøm (github.com/Frederik3152)