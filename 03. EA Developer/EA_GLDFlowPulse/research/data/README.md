# GLD primary-flow input

The frozen input is acquired from the official SPDR Gold Shares Historical
Archive endpoint:

`https://api.spdrgoldshares.com/api/v1/historical-archive?exchange=NYSE&lang=en&product=gld`

The binary workbook is retained on `D:` and hashed before preregistration. It
must not be edited in place. The probe may use rows dated through 2024-12-31;
rows dated 2025 or later stay unread by the probe.
