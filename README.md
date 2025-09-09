# PepeBooking Backend

**PepeBooking** ist eine innovative Plattform zur Vermittlung von Show-Acts, Artisten und Performances.  
Dieses Repository enthält das **Backend** der PepeBooking App.

---

## Projektüberblick

Das Backend dient als zentrale Schnittstelle für:

- **Buchungsanfragen** (mit Preisempfehlung & Artist-Auswahl)
- **Künstlerverwaltung** (Artist-Profile, Gagen, Verfügbarkeiten)
- **Admin-Funktionen** (Angebotsmanagement, Kontroll-Dashboard)
- **Preisberechnung** (inkl. intelligenter Gewichtung & Spannen)
- **API für das React-Frontend** (in Entwicklung)

---

## API Dokumentation

Alle REST-Endpunkte sind ausführlich über **Swagger** dokumentiert.  
Einfach erreichbar unter:  
http://localhost:5000/api-docs/


---


### Wichtige Endpunkte

| Methode | Pfad                                     | Funktion                         |
| ------- | ---------------------------------------- | -------------------------------- |
| GET     | `/artists`                              | Liste aller Artists              |
| POST    | `/artists`                              | Künstler anlegen                 |
| DELETE  | `/artists/<artist_id>`                  | Künstler löschen (self-service)  |
| GET     | `/requests`                             | Buchungsanfragen (mit Empfehlung)|
| POST    | `/requests`                             | Neue Anfrage inkl. Preisspanne   |
| PUT     | `/requests/<req_id>/offer`              | Artist-Angebot für Anfrage       |
| GET     | `/requests/all`                         | Admin-Übersicht aller Anfragen   |
| GET/POST| `/requests/<req_id>/admin_offers`       | Admin-Angebote verwalten         |
| GET/POST| `/availability`                         | Verfügbarkeiten verwalten        |
| GET     | `/offers`                               | Übersicht aller Angebote         |
| POST    | `/offers`                               | Neues Angebot erstellen          |
| GET     | `/offers/<offer_id>`                    | Details zu einem Angebot         |
| PUT     | `/offers/<offer_id>`                    | Angebot aktualisieren            |
| DELETE  | `/offers/<offer_id>`                    | Angebot löschen                  |
| GET     | `/bookings`                             | Übersicht aller Buchungen        |
| POST    | `/bookings`                             | Neue Buchung erstellen           |
| GET     | `/bookings/<booking_id>`                | Details zu einer Buchung         |
| PUT     | `/bookings/<booking_id>`                | Buchung aktualisieren            |
| DELETE  | `/bookings/<booking_id>`                | Buchung löschen                  |

> Alle Details & Response-Formate findest du in Swagger.

---

## Frontend

Das **Frontend** wird aktuell als moderne Single Page App mit **React** entwickelt.  
Hier entstehen Schritt für Schritt Wizard, Artist-Login und das Admin-Dashboard.
Die Anwendung ist bereits in Production unter [pepeshows.de](https://pepeshows.de)

---

## Quickstart

1. **Backend lokal starten**  
   (z.B. mit Flask, Virtualenv oder Docker)

2. **Swagger aufrufen**  
   [http://localhost:5000/api-docs/](http://localhost:5000/api-docs/)

3. **API testen & Frontend entwickeln**

---

## Swagger / OpenAPI Hinweise

- Die API-Dokumentation basiert auf **Flasgger** und **Swagger-UI v3**.
- Spezifikation wird automatisch unter [`/apispec_1.json`](http://localhost:5000/apispec_1.json) bereitgestellt.
- Die UI ist unter [`/api-docs/`](http://localhost:5000/api-docs/) erreichbar.
- Root-Level nutzt `openapi: "3.0.3"`.

---

## Technologie-Stack

- **Python 3 / Flask**  
- **SQLAlchemy** (ORM)
- **Swagger / Flasgger** (API-Doku)
- **React** (Frontend) Repo unter https://github.com/build-with-chris/pepe-frontend-app

---

## Hinweis für Arbeitgeber

Dieses Backend ist als skalierbares, modulares Fundament für eine moderne Buchungsplattform konzipiert.  
Besonderer Fokus liegt auf:

- **Klarer API-Struktur**
- **Automatisierter Dokumentation**
- **Intelligenter Preisfindung**
- **Datensicherheit & Erweiterbarkeit**

Gerne beantworte ich Rückfragen zum Code, Deployment oder Produktvision!

---