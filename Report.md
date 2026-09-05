# Project Report: Pearls AQI Predictor
**Submitted by:** Usman Sarwar
**Role:** Computer Systems and AI Engineer

## Abstract
In this comprehensive project report, I will walk you through exactly what I did to build the Pearls AQI Predictor. This project is a complete, end to end Machine Learning Operations (MLOps) pipeline designed to forecast the Air Quality Index (AQI) for my city, Sadiqabad. I built this entirely from scratch, utilizing advanced machine learning techniques, a completely serverless infrastructure, and a modern web interface.

## 1. Introduction and Motivation

As a Computer Systems and AI Engineer at Sukkur IBA University, I have always been deeply passionate about combining my engineering skills with practical, real world problems. Air pollution is a silent crisis. In growing cities like Sadiqabad, citizens often have no idea what the air quality will be like tomorrow, let alone three days from now. 

I wanted to build a solution. However, I didn't just want to build a simple Python notebook that sits on my computer. I wanted to build a fully deployed, production ready system that runs automatically, updates itself, and serves predictions to the public through a beautiful dashboard. 

My goal was to implement a 100% serverless architecture. This means I did not want to pay for expensive 24/7 cloud servers. Instead, I wanted to orchestrate free tier services to do heavy lifting on a schedule.

## 2. Data Collection Strategy

The first challenge I faced was getting reliable data. Machine learning is only as good as the data you feed into it. I needed historical air pollution data and historical weather data for Sadiqabad.

I decided to use two powerful APIs:
1. **OpenWeather API:** This gave me the historical concentrations of specific pollutants like PM2.5, PM10, Carbon Monoxide, and Ozone.
2. **Open Meteo API:** Weather severely impacts air quality. For instance, high winds clear out pollution. I gathered historical temperature, relative humidity, and wind speed data.

I wrote a robust Python script (`fetch_api.py`) that communicates with these APIs. To make the pipeline resilient, I added error handling and retry loops. If the API drops the connection, my script automatically waits a few seconds and tries again. This ensures the data collection never crashes silently.

## 3. Feature Engineering and the Feature Store

Once I had the raw data, I realized it wasn't enough to just pass raw numbers to a machine learning model. I needed to engineer new features that give the model "context."

In my `compute_features.py` script, I extracted time based variables like the hour of the day and the day of the week. This is crucial because pollution patterns are cyclical (e.g., rush hour traffic creates more pollution). I also calculated rolling averages over 24 hours to smooth out sudden spikes, and I calculated the rate of change from the previous hour.

After computing these features, I had to store them. I integrated **Hopsworks**, an enterprise grade Feature Store. Hopsworks acts as the central brain of my data. Whenever my script runs, it pushes the newly engineered dataframe to Hopsworks. This guarantees that my training scripts and my live prediction scripts are always querying the exact same, standardized dataset.

## 4. Machine Learning Model Training

For the prediction engine, I evaluated several algorithms and ultimately chose **XGBoost**. XGBoost is an incredibly powerful gradient boosting algorithm that excels at finding non linear relationships in tabular data.

Instead of predicting tomorrow's AQI and then using that prediction to predict the next day (which causes errors to multiply), I trained three entirely separate models:
1. A model specifically trained to predict 24 hours ahead.
2. A model specifically trained to predict 48 hours ahead.
3. A model specifically trained to predict 72 hours ahead.

This direct multi step forecasting approach yielded incredibly high R squared values and low Mean Absolute Errors. I saved these trained models, alongside the StandardScaler used to normalize the data, directly to the Hopsworks Model Registry. 

## 5. Model Explainability

I believe that AI should not be a "black box." Instructors and users need to know *why* the model made a specific prediction. 

To solve this, I integrated **SHAP** (SHapley Additive exPlanations). When my pipeline generates a prediction, it also calculates the SHAP values for that specific prediction. This mathematical technique breaks down the prediction and shows exactly how much the Temperature, or the PM2.5 levels, pushed the AQI number up or down. I extract this data and send it to the frontend to be visualized as a beautiful Waterfall chart.

## 6. Serverless Automation with GitHub Actions

This is where the magic happens. I wrote YAML workflow files for GitHub Actions to completely automate the entire system.

Every single hour, on the hour, GitHub wakes up a virtual machine and runs my `hourly_update.py` script. 
* It fetches the last hour of weather and pollution data.
* It engineers the features.
* It uploads the new row to Hopsworks.

Immediately after, it runs my `generate_predictions.py` script.
* It downloads the latest row from Hopsworks.
* It downloads the trained models from the registry.
* It generates the 1, 2, and 3 day forecasts.
* It writes everything into a static `predictions.json` file.
* Finally, a bot commits this JSON file to the repository.

This means my dashboard is always live, always updating, and requires absolutely zero manual intervention from me.

## 7. Artificial Intelligence Insights

Raw numbers can be confusing for regular people. An AQI of 85 might not mean anything to someone who isn't a scientist. 

To bridge this gap, I integrated a Large Language Model (LLM). During the hourly pipeline run, my script takes the numerical forecasts and sends them securely to the HuggingFace API using the Zephyr 7B model. I prompt the LLM to act as an expert meteorologist and summarize the data into a plain English health advisory. This text is then saved into the JSON file and displayed on the dashboard.

## 8. Frontend UI and Skeuomorphism

I built the dashboard frontend without relying on heavy frameworks like React or Angular. I used pure HTML, CSS, and Vanilla JavaScript. 

For the design language, I chose **Skeuomorphism**. Instead of flat colors, Skeuomorphism uses intricate box shadows, highlights, and gradients to make the buttons and panels look like physical, 3D objects pressing into or popping out of the screen. I spent a lot of time crafting the CSS to make the interface feel premium, tactile, and highly responsive.

I also added a local AI Chatbot on the frontend. Using JavaScript keyword matching, the chatbot can converse with visitors about my biography and the technical details of the project without needing to contact an external API, ensuring 100% security for my API keys.

## 9. Challenges I Overcame

Building this was not without hurdles:
* **Connection Drops:** The Hopsworks free tier would sometimes drop connections while I was uploading data. I solved this by engineering robust retry loops with exponential backoff in my Python scripts.
* **Git Conflicts:** Because the GitHub Action bot commits code to the repository automatically, I occasionally ran into non fast forward Git conflicts when trying to push my local CSS changes. I learned how to carefully rebase my local branches to integrate the bot's changes smoothly.
* **LLM Loading Times:** HuggingFace free models occasionally "go to sleep." My pipeline would fail because the model took longer than 20 seconds to wake up. I solved this by switching to a faster model and implementing a 503 error catcher that waits patiently for the model to load before trying again.

## 10. Conclusion

This project represents the culmination of my skills as an AI Engineer. I successfully integrated data engineering, machine learning, MLOps, cloud automation, and frontend web development into a single, cohesive, serverless product. 

I am incredibly proud of the Pearls AQI Predictor, and I hope this report clearly demonstrates the depth of engineering and problem solving that went into creating it.

Thank you for your time and for reviewing my work.

Usman Sarwar
