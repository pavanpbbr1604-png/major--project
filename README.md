# major--project
# Crowd Density Estimation using Multi-Perspective Image Analysis

## Overview

An AI-powered crowd analysis system that detects people, estimates crowd density, and classifies crowd levels using images captured from different perspectives. The system combines YOLOv8x-based person detection with density estimation, reliability analysis, and multi-perspective fusion to provide accurate crowd insights.

## Features

* Person Detection using YOLOv8x
* Crowd Density Estimation
* Multi-Perspective Crowd Analysis
* Reliability-Based Count Estimation
* Crowd Classification (Undercrowded, Moderate, Overcrowded)
* SQLite-Based Analysis History
* Interactive Dashboard for Visualization

## Tech Stack

**Frontend:** HTML, CSS, JavaScript

**Backend:** Python, Flask

**Computer Vision:** YOLOv8x, OpenCV

**Database:** SQLite

## Workflow

Image Upload → Preprocessing → Person Detection → Density Estimation → Reliability Analysis → Multi-Perspective Fusion → Crowd Classification → Results Dashboard

## Run the Project

```bash
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Applications

* Railway Stations
* Shopping Malls
* Airports
* Stadiums
* Public Events
* Smart City Monitoring

## Future Enhancements

* Real-Time CCTV Monitoring
* Live Webcam Analysis
* Cloud Deployment
* Smart Crowd Alert System
