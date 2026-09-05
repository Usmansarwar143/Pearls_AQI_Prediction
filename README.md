# Pearls AQI Predictor: Sadiqabad Air Quality Intelligence

Welcome to the official repository for the Pearls AQI Predictor! This project is a state of the art, 100% serverless Machine Learning Operations (MLOps) pipeline that predicts the Air Quality Index (AQI) for Sadiqabad, Pakistan, up to 3 days in advance. 

## Table of Contents
* Introduction
* Live Demo
* Core Features
* System Architecture
* Technology Stack
* Detailed Directory Structure
* Data Sources and Collection
* Feature Engineering and Hopsworks
* Model Training and XGBoost
* Frontend and Skeuomorphic UI
* Artificial Intelligence and LLM Integration
* Local Installation and Setup
* Automated Pipeline Workflows
* Contact Information

## Introduction

Air pollution is a massive global challenge. In growing cities like Sadiqabad, having accurate predictions of air quality can help citizens plan their daily activities safely. I created the Pearls AQI Predictor to solve this problem by leveraging advanced Machine Learning algorithms, specifically XGBoost, alongside a completely serverless infrastructure. 

This repository contains everything from the data fetching scripts to the frontend user interface. The entire system is automated. It fetches new weather and pollution data every hour, engineers features, pushes them to a Hopsworks Feature Store, downloads the latest trained models, generates 1 day, 2 day, and 3 day forecasts, calculates SHAP explainability values, generates natural language health insights using a HuggingFace Large Language Model, and deploys it all to a beautiful GitHub Pages dashboard.

## Live Demo

You can view the live, real time dashboard here:
[Pearls AQI Predictor Live Dashboard](https://usmansarwar143.github.io/Pearls_AQI_Prediction/)

## Core Features

* **Fully Serverless**: No dedicated backend servers are required. Everything runs on GitHub Actions and Hopsworks.
* **XGBoost Forecasting**: Highly accurate regression models trained specifically on Sadiqabad historical data.
* **Real Time Automation**: A cron job runs every hour to keep the data fresh.
* **SHAP Explainability**: The dashboard visually explains exactly which features (like temperature, humidity, or wind speed) drove the AI to make its prediction.
* **LLM Health Insights**: Integration with HuggingFace Zephyr 7B provides plain English health advisories based on the numerical AQI predictions.
* **Offline Chatbot**: A custom JavaScript AI assistant provides immediate answers about the project and its creator.
* **Skeuomorphic Design**: A premium, 3D style user interface built from scratch using pure CSS and Vanilla JavaScript.

## System Architecture

The architecture is divided into three main pipelines:

1. **Feature Pipeline (Hourly)**:
   This pipeline contacts the OpenWeather and Open Meteo APIs. It downloads the latest pollution metrics (PM2.5, PM10, CO, NO, etc.) and weather conditions (Temperature, Humidity, Wind Speed). It then calculates rolling averages and pushes this data to the Hopsworks Feature Store.

2. **Training Pipeline (On Demand / Weekly)**:
   This pipeline pulls years of historical data from Hopsworks. It cleans the data, scales it using StandardScaler, and trains three separate XGBoost models (for 24h, 48h, and 72h horizons). The trained models are then saved to the Hopsworks Model Registry.

3. **Batch Inference Pipeline (Hourly)**:
   This script runs right after the Feature Pipeline. It pulls the latest single row of data from the Feature Store, downloads the models from the Model Registry, generates predictions, calculates SHAP values, queries the HuggingFace LLM, and writes everything to a static JSON file (`predictions.json`).

4. **Frontend Deployment**:
   GitHub Pages automatically hosts the `docs/` folder, which serves `index.html` and dynamically reads the newly generated `predictions.json`.

## Technology Stack

* **Language**: Python 3.10
* **Machine Learning**: Scikit Learn, XGBoost, SHAP
* **MLOps**: Hopsworks (Feature Store & Model Registry)
* **Automation**: GitHub Actions
* **Frontend**: HTML5, Vanilla CSS3 (Skeuomorphism), Vanilla JavaScript
* **AI/LLM**: HuggingFace Inference API (Zephyr 7B)
* **Data Sources**: OpenWeather API, Open Meteo API

## Detailed Directory Structure

```text
Pearls_AQI_Prediction/
│
├── .github/
│   └── workflows/
│       ├── hourly_feature_pipeline.yml
│       └── model_training_pipeline.yml
│
├── docs/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   ├── favicon.png
│   ├── logo.png
│   └── predictions.json
│
├── src/
│   ├── feature_pipeline/
│   │   ├── compute_features.py
│   │   ├── fetch_api.py
│   │   └── hourly_update.py
│   │
│   ├── training_pipeline/
│   │   ├── train_models.py
│   │   └── evaluate.py
│   │
│   └── web_app/
│       └── generate_predictions.py
│
├── .gitignore
├── requirements.txt
└── README.md
```

## Data Sources and Collection

The quality of any Machine Learning model depends entirely on its data. For this project, I utilized two primary APIs:

1. **OpenWeather Air Pollution API**:
   This provides historical and current concentrations of CO, NO, NO2, O3, SO2, PM2.5, PM10, and NH3. These are the raw ingredients of the Air Quality Index.

2. **Open Meteo API**:
   Weather plays a massive role in pollution dispersion. High winds blow pollution away, while temperature inversions trap it. I collected temperature, relative humidity, and wind speed at 10 meters.

## Feature Engineering and Hopsworks

Raw data is rarely enough. In the `compute_features.py` script, I engineer several critical time series features:
* **Time Variables**: Hour of the day, Day of the week, Month. These capture cyclical human behaviors (like rush hour traffic).
* **Rolling Averages**: 24 hour rolling AQI helps smooth out temporary spikes.
* **Change Rates**: The difference between the current hour and the previous hour.

Once computed, this Pandas DataFrame is pushed to Hopsworks. Hopsworks acts as a centralized database for Machine Learning features, ensuring that the training pipeline and the inference pipeline are always using the exact same data definitions.

## Model Training and XGBoost

I chose XGBoost (Extreme Gradient Boosting) as the core algorithmic engine for this predictor. XGBoost is highly robust against overfitting and handles tabular, non linear environmental data exceptionally well.

The training script pulls the full feature group from Hopsworks, splits it into training and testing sets, and trains three distinct models. I opted for direct multi step forecasting (training separate models for exactly 1 day, 2 days, and 3 days out) rather than recursive forecasting (predicting tomorrow, then feeding that prediction back in to predict the next day), because recursive forecasting tends to compound and multiply errors over time.

## Frontend and Skeuomorphic UI

The dashboard located in the `docs/` folder is designed to be visually striking. Moving away from the common flat design or glassmorphism, I implemented a rich Skeuomorphic design. 

Skeuomorphism uses shadows, highlights, and gradients to make digital elements look like physical, tangible objects. The CSS features multiple layers of box shadows to create deep insets and raised panels. The entire frontend relies on Vanilla JavaScript to parse `predictions.json` and dynamically render Chart.js graphs, SHAP waterfall charts, and metric panels without needing a heavy framework like React.

## Artificial Intelligence and LLM Integration

To make the dashboard accessible to non technical users, raw AQI numbers are not enough. I integrated the HuggingFace Inference API directly into the backend batch script. 

When `generate_predictions.py` runs, it sends the numerical forecasts to the `HuggingFaceH4/zephyr-7b-beta` Large Language Model. The LLM acts as an expert meteorologist and returns a customized, plain English health advisory. This advisory is saved into the JSON file and displayed prominently on the dashboard.

Additionally, a local, offline Chatbot is built directly into the frontend. It operates securely within the browser and answers questions about the project architecture and its creator.

## Local Installation and Setup

If you wish to fork this repository and run it locally, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Usmansarwar143/Pearls_AQI_Prediction.git
   cd Pearls_AQI_Prediction
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   You will need to create a `.env` file in the root directory containing:
   ```text
   HOPSWORKS_API_KEY=your_key_here
   HOPSWORKS_PROJECT_NAME=your_project_name
   OPENWEATHER_API_KEY=your_key_here
   HF_API_KEY=your_huggingface_key
   ```

5. **Run the pipeline manually:**
   ```bash
   python src/feature_pipeline/hourly_update.py
   python src/web_app/generate_predictions.py
   ```

## Automated Pipeline Workflows

This repository uses GitHub Actions for CI/CD automation.

* `hourly_feature_pipeline.yml`: Runs at minute 0 of every hour. It triggers data collection, uploads to Hopsworks, generates predictions, and pushes the new `predictions.json` to the main branch.
* `model_training_pipeline.yml`: Runs on demand. It triggers the heavy process of retraining the XGBoost models on newly accumulated data.

## Contact Information

**Created and Engineered by Usman Sarwar**

I am a Computer Systems Engineer and AI Engineer from Sukkur IBA University, with hands on experience in Artificial Intelligence, computer vision, robotics, automation, and software development. I am an ambitious tech enthusiast who combines engineering skills with leadership, research, and community involvement, continuously exploring emerging technologies and building practical solutions.

* **GitHub**: [Usmansarwar143](https://github.com/Usmansarwar143)
* **Location**: Sadiqabad, Pakistan

Thank you for visiting the Pearls AQI Predictor!
