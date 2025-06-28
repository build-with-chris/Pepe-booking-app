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
http://localhost:5000/apidocs

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

> Alle Details & Response-Formate findest du in Swagger.

---

## Frontend

Das **Frontend** wird aktuell als moderne Single Page App mit **React** entwickelt.  
Hier entstehen Schritt für Schritt Wizard, Artist-Login und das Admin-Dashboard.

---

## Quickstart

1. **Backend lokal starten**  
   (z.B. mit Flask, Virtualenv oder Docker)

2. **Swagger aufrufen**  
   [http://localhost:5000/apidocs](http://localhost:5000/apidocs)

3. **API testen & Frontend entwickeln**

---

## Technologie-Stack

- **Python 3 / Flask**  
- **SQLAlchemy** (ORM)
- **Swagger / Flasgger** (API-Doku)
- **React** (Frontend, in Arbeit)

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